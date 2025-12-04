

##############################
#        PARAMETERS          # 
MAX_TURNS = 18
CLEAR_CACHE = False          # WARNING: This clears the entire cache, not just this use case
CACHE_RESULT = True
USE_GOOGLE_CLOUD_TTS = True  # Text-to-speech: if both are false, no TTS is generated
USE_GTTS = False
SERVER_PORT = 5002           # Port for the scenario runner server
##############################


# IMPORTANT: Import patch first to fix top_p issue with Claude Haiku 4.5
import anthropic_top_p_patch

import asyncio
import os
import sys
import uuid
import json
import logging
import webbrowser
import re
import time
import signal
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from app import start_flask_app, update_chat_history, update_scenario_info, is_execution_paused
from agent_squad.orchestrator import AgentSquad, AgentSquadConfig
from agent_squad.types import ConversationMessage, ParticipantRole
from agent_squad.classifiers import ClassifierResult
from agent_chooser import AgentChooser
from agent_factory import create_agents_from_scenario

import llm_cache
if CLEAR_CACHE: # wipe existing cache values
    cache = llm_cache.get_cache()
    cache.clear()
if CACHE_RESULT:
# Enable automatic caching for all LLM calls
    llm_cache.enable_auto_caching()

# Suppress httpx info logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.WARNING)

# Load environment variables
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Initialize the appropriate TTS service
if USE_GOOGLE_CLOUD_TTS:
    from google_cloud_tts_service import GoogleCloudTTSService
    tts_service = GoogleCloudTTSService()
elif USE_GTTS:
    from tts_service import TTSService
    tts_service = TTSService()
else:
    tts_service = None

def create_agents_from_json_data(scenario_data):
    """
    Creates agents from in-memory JSON data instead of a file.
    This is used when the scenario is submitted via the API.
    """
    from custom_agent import CustomAnthropicAgent
    from agent_squad.agents import AnthropicAgentOptions
    from agent_squad.utils import AgentTool, AgentTools
    import local_tools as local_tools
    from custom_agent import mcp_tool_func, tool_surrogate_func
    from main_prompt_builder import build_main_prompt
    import inspect
    
    LOCALLY_IMPLEMENTED_TOOLS = {name: func for name, func in inspect.getmembers(local_tools, inspect.isfunction)}
    
    agents = []
    for agent_config in scenario_data.get('agents', []):
        # Create tools for the agent
        agent_tools = []
        for tool_config in agent_config.get('tools', []):
            tool_name = tool_config.get('toolName')
            if tool_name is None:
                print("WARNING: Tool name ('toolName' property) was not included in a tool configuration. Skipping this tool.")
                continue
            tool_function = LOCALLY_IMPLEMENTED_TOOLS.get(tool_name)
            mcp_server = tool_config.get('mcpServer')
            if tool_function:
                # Locally implemented tool
                pass
            elif mcp_server:
                # MCP tool
                tool_function = mcp_tool_func
            else:
                # Surrogate for an unimplemented tool
                tool_function = tool_surrogate_func

            # make sure the tool name is passed to the tool surrogate function
            properties = tool_config.get('inputSchema', {}).get('properties', {})
            properties['tool_name'] = {'type': 'string', 'enum': [tool_name]}
            required = tool_config.get('inputSchema', {}).get('required', [])
            required = required.append('tool_name') if required else ['tool_name']
            
            agent_tool = AgentTool(
                name=tool_name,
                description=tool_config.get('description'),
                properties=properties,
                required=required,
                func=tool_function
            )
            agent_tools.append(agent_tool)
        tools = AgentTools(agent_tools)

        # Create the agent with the enhanced options
        system_prompt = build_main_prompt(scenario_data, agent_config)
        agent = CustomAnthropicAgent(AnthropicAgentOptions(
            name=agent_config.get('agentId'),
            description=agent_config.get('situation'),
            api_key=ANTHROPIC_API_KEY,
            model_id='claude-haiku-4-5-20251001',
            streaming=False,
            custom_system_prompt={"template": system_prompt},
            tool_config={'tool': tools, 'toolMaxRecursions': 10}
        ))
        agent.agent_config = agent_config
        agents.append(agent)

    return scenario_data, agents


async def run_scenario_from_data(scenario_data):
    """Run a scenario from in-memory JSON data."""
    start_flask_app()
    time.sleep(1)  # Give flask time to start
    webbrowser.open("http://127.0.0.1:5001")
    
    user_id = "user_123"
    session_id = str(uuid.uuid4())

    _, agents = create_agents_from_json_data(scenario_data)
    if not agents:
        print("No agents were created. Exiting.")
        return False

    if scenario_data.get("scenario"):
        update_scenario_info({
            "title": scenario_data["scenario"].get("title", ""),
            "description": scenario_data["scenario"].get("description", "")
        })

    # Set up the orchestrator
    sending_agent = next((agent for agent in agents if 'messageToUseWhenInitiatingConversation' in agent.agent_config), None)
    if not sending_agent:
        print("Could not find an initiating agent in the scenario. You must specify an initiating message.")
        return False
    else:
        sending_agent_id = sending_agent.id
    responding_agent = next((agent for agent in agents if agent.id != sending_agent.id), None)
    responding_agent_id = responding_agent.id if responding_agent else "Unknown"
    
    classifier = AgentChooser(initiating_agent_id=responding_agent.id)
    orchestrator = AgentSquad(
        classifier=classifier,
        options=AgentSquadConfig(
            LOG_CLASSIFIER_OUTPUT=False
        )
    )
    orchestrator.scenario_data = scenario_data
    for agent in agents:
        orchestrator.add_agent(agent)

    # Main conversational loop
    max_turns = MAX_TURNS
    turn_count = 0
    conversation_ended = False
    next_request = None
    ui_history = []
    
    while not conversation_ended and turn_count < max_turns:
        turn_count += 1
        print(f"\n======= Turn {turn_count} =======")
        # swap agent roles
        temp = responding_agent
        temp_id = responding_agent_id
        responding_agent = sending_agent
        responding_agent_id = sending_agent_id
        sending_agent = temp
        sending_agent_id = temp_id

        print(f"--- Sending agent: {sending_agent.id}, Responding agent: {responding_agent.id} ---")

        classifier_result = ClassifierResult(selected_agent=responding_agent, confidence=1.0)
        if turn_count == 1:
            response_text = responding_agent.agent_config['messageToUseWhenInitiatingConversation']
        else:
            response = await orchestrator.agent_process_request(
                next_request,
                user_id,
                session_id,
                classifier_result,
                additional_params={
                    "scenario": orchestrator.scenario_data,
                    "agent_config": responding_agent.agent_config
                }
            )
            response_text = response.output.content[0]['text']
        
        tool_calls = re.findall(r'\[TOOL_CALL\](.*?)\[/TOOL_CALL\]', response_text)
        clean_content = re.sub(r'\[TOOL_CALL\].*?\[/TOOL_CALL\]', '', response_text).strip()
        full_response = f"TURN {turn_count}: Agent {responding_agent.id} said: {clean_content}"
        print("--- FULL RESPONSE ADDED TO HISTORY: ", full_response[0:200])
        
        await orchestrator.storage.save_chat_message(
            user_id,
            session_id,
            responding_agent.id,
            ConversationMessage(
                role=ParticipantRole.ASSISTANT.value,
                content=[{'text': full_response}]
            )
        )

        for tool_name in tool_calls:
            ui_history.append({
                'sending_agent_id': sending_agent_id,
                'responding_agent_id': responding_agent_id,
                'type': 'tool',
                'content': f"Running tool: {tool_name}",
            })
        
        if clean_content:
            msg_data = {
                'sending_agent_id': sending_agent_id,
                'responding_agent_id': responding_agent_id,
                'type': 'message',
                'content': clean_content,
            }

            if tts_service is not None:
                tts_content = clean_content.replace('#', '').replace('*', '').replace('-','')
                speaker_num = len([m for m in ui_history if m.get('type') == 'message'])
                speaker_id = f"speaker{(speaker_num % 2) + 1}"
                print(f"Generating audio for message {speaker_num + 1}: speaker={speaker_id}")
                audio_url = tts_service.get_audio_url(tts_content, speaker_id)
                if audio_url:
                    msg_data['audio_url'] = audio_url
                    print(f"  -> Audio generated: {audio_url}")
                else:
                    print(f"  -> Audio generation failed")
            
            ui_history.append(msg_data)
        
        print(f"--- UI_HISTORY length = {len(ui_history)}")
        update_chat_history(ui_history)
        next_request = response_text

        if 'toolUse' in response_text:
            print(f"WARNING: A TOOL USE REQUEST HAS SURFACED IN THE CONVERSATION: {response_text}")

        if "END OF CONVERSATION" in response_text:
            conversation_ended = True
            print("\n--- Conversation has ended ---")
        else:
            print("\n--- END OF TURN ---")
        
        while is_execution_paused() and not conversation_ended:
            print("⏸ Execution paused... (waiting for play)")
            time.sleep(0.5)
    
    if not conversation_ended:
        print("\n--- Maximum turns reached, ending conversation ---")

    time.sleep(3)
    return True


async def main(args):
    """Main function to demonstrate secure, agent-contained tool use."""
    start_flask_app()
    time.sleep(1)  # Give flask time to start
    webbrowser.open("http://127.0.0.1:5001")
    
    user_id = "user_123"
    session_id = str(uuid.uuid4())

    if len(args) != 2:
        print("You must pass in the name of the scenario as the command line argument")
        return
    else:
        scenario_path = os.path.join('scenarios', args[1])
        if not scenario_path.endswith('.json'):
            scenario_path_json = f'{scenario_path}.json'
        else:
            scenario_path_json = scenario_path
            scenario_path = scenario_path.replace(".json", "")
    scenario_path_text = f'{scenario_path}_result.txt'
    scenario_data, agents = create_agents_from_scenario(scenario_path_json)
    if not agents:
        print("No agents were created. Exiting.")
        return

    if scenario_data.get("scenario"):
        update_scenario_info({
            "title": scenario_data["scenario"].get("title", ""),
            "description": scenario_data["scenario"].get("description", "")
        })

    # 2. Set up the orchestrator
    sending_agent = next((agent for agent in agents if 'messageToUseWhenInitiatingConversation' in agent.agent_config), None)
    if not sending_agent:
        print("Could not find an initiating agent in the scenario. You must specify an initiating message.")
        return
    else:
        sending_agent_id = sending_agent.id
    responding_agent = next((agent for agent in agents if agent.id != sending_agent.id), None)
    responding_agent_id = responding_agent.id if responding_agent else "Unknown"
    
    classifier = AgentChooser(initiating_agent_id=responding_agent.id)
    orchestrator = AgentSquad(
        classifier=classifier,
        options=AgentSquadConfig(
            LOG_CLASSIFIER_OUTPUT=False
        )
    )
    orchestrator.scenario_data = scenario_data
    for agent in agents:
        orchestrator.add_agent(agent)

    # 3. Main conversational loop
    max_turns = MAX_TURNS
    turn_count = 0
    conversation_ended = False
    next_request = None
    ui_history = []
    
    while not conversation_ended and turn_count < max_turns:
        turn_count += 1
        print(f"\n======= Turn {turn_count} =======")
        # swap agent roles
        temp = responding_agent
        temp_id = responding_agent_id
        responding_agent = sending_agent
        responding_agent_id = sending_agent_id
        sending_agent = temp
        sending_agent_id = temp_id
        # end swap roles

        print(f"--- Sending agent: {sending_agent.id}, Responding agent: {responding_agent.id} ---")

        # The "next_request" variable holds the conversational message. The remainder is in the history
        classifier_result = ClassifierResult(selected_agent=responding_agent, confidence=1.0)
        if turn_count == 1:
            response_text = responding_agent.agent_config['messageToUseWhenInitiatingConversation']
        else:
            response = await orchestrator.agent_process_request(
                next_request,
                user_id,
                session_id,
                classifier_result,
                additional_params={
                    "scenario": orchestrator.scenario_data,
                    "agent_config": responding_agent.agent_config
                }
            )
            response_text = response.output.content[0]['text']
        #print(f"\n--- Raw response: {response_text} ---")
        tool_calls = re.findall(r'\[TOOL_CALL\](.*?)\[/TOOL_CALL\]', response_text)
        # remove tool calls since they are private
        clean_content = re.sub(r'\[TOOL_CALL\].*?\[/TOOL_CALL\]', '', response_text).strip()
        full_response = f"TURN {turn_count}: Agent {responding_agent.id} said: {clean_content}"
        print("--- FULL RESPONSE ADDED TO HISTORY: ", full_response[0:200])
        # Save message to history
        await orchestrator.storage.save_chat_message(
            user_id,
            session_id,
            responding_agent.id,
            ConversationMessage(
                role=ParticipantRole.ASSISTANT.value,
                content=[{'text': full_response}]
            )
        )

        # Add tool call messages to the UI history
        for tool_name in tool_calls:
            ui_history.append({
                'sending_agent_id': sending_agent_id,
                'responding_agent_id': responding_agent_id,
                'type': 'tool',
                'content': f"Running tool: {tool_name}",
            })
        # Add the clean conversational message to the UI history
        if clean_content:
            msg_data = {
                'sending_agent_id': sending_agent_id,
                'responding_agent_id': responding_agent_id,
                'type': 'message',
                'content': clean_content,
            }

            if tts_service is not None:
                # Remove markdown formatting characters (# and *) for TTS
                tts_content = clean_content.replace('#', '').replace('*', '').replace('-','')
                speaker_num = len([m for m in ui_history if m.get('type') == 'message'])
                speaker_id = f"speaker{(speaker_num % 2) + 1}"
                print(f"Generating audio for message {speaker_num + 1}: speaker={speaker_id}")
                audio_url = tts_service.get_audio_url(tts_content, speaker_id)
                if audio_url:
                    msg_data['audio_url'] = audio_url
                    print(f"  -> Audio generated: {audio_url}")
                else:
                    print(f"  -> Audio generation failed")
            
            ui_history.append(msg_data)
        
        # # Count how many audio messages we're about to send
        # audio_messages = len([m for m in ui_history if m.get('type') == 'message' and m.get('audio_url')])
        
        print(f"--- UI_HISTORY length = {len(ui_history)}")
        update_chat_history(ui_history)

        # The next request for the other agent is the raw response text
        next_request = response_text

        if 'toolUse' in response_text:
            print(f"WARNING: A TOOL USE REQUEST HAS SURFACED IN THE CONVERSATION: {response_text}")

        #Check for the termination signal in the response text
        if "END OF CONVERSATION" in response_text:
            conversation_ended = True
            print("\n--- Conversation has ended ---")
        else:
            print("\n--- END OF TURN ---")
        
        # Check pause state before continuing to next turn
        while is_execution_paused() and not conversation_ended:
            print("⏸ Execution paused... (waiting for play)")
            time.sleep(0.5)
    
    if not conversation_ended:
        print("\n--- Maximum turns reached, ending conversation ---")

    # Give the UI a moment to fetch the final update
    time.sleep(3)

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\nShutting down gracefully...")
    print("Flask server will stop automatically.")
    sys.exit(0)


# ============================================
# Server Mode - Flask API for running scenarios
# ============================================

server_app = Flask(__name__)
CORS(server_app)  # Enable CORS for cross-origin requests from the editor

# Track if a scenario is currently running
scenario_running = False
scenario_lock = threading.Lock()

@server_app.route('/run-scenario', methods=['POST'])
def api_run_scenario():
    """API endpoint to run a scenario from JSON data."""
    global scenario_running
    
    with scenario_lock:
        if scenario_running:
            return jsonify({"error": "A scenario is already running"}), 409
        scenario_running = True
    
    try:
        scenario_data = request.get_json()
        if not scenario_data:
            with scenario_lock:
                scenario_running = False
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Validate required fields
        if 'agents' not in scenario_data or len(scenario_data.get('agents', [])) < 2:
            with scenario_lock:
                scenario_running = False
            return jsonify({"error": "Scenario must have at least 2 agents"}), 400
        
        # Check that at least one agent has the initiating message
        has_initiating_message = any(
            'messageToUseWhenInitiatingConversation' in agent 
            for agent in scenario_data.get('agents', [])
        )
        if not has_initiating_message:
            with scenario_lock:
                scenario_running = False
            return jsonify({"error": "At least one agent must have 'messageToUseWhenInitiatingConversation'"}), 400
        
        # Run the scenario in a background thread
        def run_in_background():
            global scenario_running
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(run_scenario_from_data(scenario_data))
            except Exception as e:
                print(f"Error running scenario: {e}")
            finally:
                with scenario_lock:
                    scenario_running = False
        
        thread = threading.Thread(target=run_in_background)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "started",
            "message": "Scenario is now running. Check the chat window at http://127.0.0.1:5001"
        })
        
    except Exception as e:
        with scenario_lock:
            scenario_running = False
        return jsonify({"error": str(e)}), 500


@server_app.route('/status', methods=['GET'])
def api_status():
    """Check if the server is running and if a scenario is active."""
    with scenario_lock:
        return jsonify({
            "status": "running",
            "scenario_active": scenario_running
        })


def run_server():
    """Run the scenario runner server."""
    print("="*60)
    print("SCENARIO RUNNER SERVER")
    print("="*60)
    print(f"Server running on http://127.0.0.1:{SERVER_PORT}")
    print("Waiting for scenarios from the editor...")
    print("Press Ctrl+C to stop the server.")
    print("="*60 + "\n")
    
    server_app.run(port=SERVER_PORT, use_reloader=False, threaded=True)


if __name__ == "__main__":
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Check for --server flag to run in server mode
    if len(sys.argv) >= 2 and sys.argv[1] == '--server':
        run_server()
    else:
        # Original CLI mode
        asyncio.run(main(sys.argv))
        
        # After async conversation completes, keep the server alive
        print("\n" + "="*60)
        print("CONVERSATION COMPLETE")
        print("="*60)
        print("The Flask server is still running to serve audio files.")
        print("You can continue playing audio in your browser.")
        print("Press Ctrl+C to stop the server when done.")
        print("="*60 + "\n")
        
        # Keep the main thread alive so the Flask server can continue serving files
        # The Flask thread is a daemon thread, so it will exit when this loop exits
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            # This will be caught by the signal handler
            pass
