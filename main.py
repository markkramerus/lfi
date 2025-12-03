

##############################
#        PARAMETERS          # 
MAX_TURNS = 18
CLEAR_CACHE = False          # WARNING: This clears the entire cache, not just this use case
CACHE_RESULT = True
USE_GOOGLE_CLOUD_TTS = True  # Text-to-speech: if both are false, no TTS is generated
USE_GTTS = False
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

    if scenario_data.get("metadata"):
        update_scenario_info({
            "title": scenario_data["metadata"].get("title", "Chat Scenario"),
            "description": scenario_data["metadata"].get("description", "")
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

if __name__ == "__main__":
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
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
