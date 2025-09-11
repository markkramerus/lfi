import asyncio
import os
import sys
import uuid
import json
import logging
import webbrowser
import re
import time
from dotenv import load_dotenv
from app import start_flask_app, update_chat_history, update_scenario_info
from agent_squad.orchestrator import AgentSquad, AgentSquadConfig
from agent_squad.types import ConversationMessage, ParticipantRole
from agent_squad.classifiers import ClassifierResult
from agent_chooser import AgentChooser
from agent_factory import create_agents_from_scenario
from main_prompt_builder import build_main_prompt

# Suppress httpx info logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.WARNING)

# Load environment variables
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MAX_HISTORY = 10000

async def main(args):
    """Main function to demonstrate secure, agent-contained tool use."""
    start_flask_app()
    time.sleep(1)  # Give flask time to start
    webbrowser.open("http://127.0.0.1:5001")
    
    user_id = "user_123"
    session_id = str(uuid.uuid4())

    #print("--- Starting Secure Tool Use Demonstration ---")
    if len(args) != 2:
        print("You must pass in the name of the scenario as the command line argument")
        return
    else:
        scenario_path = os.path.join('scenarios', args[1])
        if not scenario_path.endswith('.json'):
            scenario_path = f'{scenario_path}.json'
    scenario_data, agents = create_agents_from_scenario(scenario_path)
    if not agents:
        print("No agents were created. Exiting.")
        return

    if scenario_data.get("metadata"):
        update_scenario_info({
            "title": scenario_data["metadata"].get("title", "Chat Scenario"),
            "description": scenario_data["metadata"].get("description", "")
        })

    # 2. Set up the orchestrator
    initiating_agent = next((agent for agent in agents if 'messageToUseWhenInitiatingConversation' in agent.agent_config), None)
    if not initiating_agent:
        print("Could not find an initiating agent in the scenario.")
        return
    
    other_agent = next((agent for agent in agents if agent.id != initiating_agent.id), None)
    initiating_agent_id = initiating_agent.id
    other_agent_id = other_agent.id if other_agent else "Unknown"
    
    classifier = AgentChooser(initiating_agent_id=initiating_agent.id)
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
    
    next_request = initiating_agent.agent_config['messageToUseWhenInitiatingConversation']

    # Manually save the initiating message to the chat history
    await orchestrator.storage.save_chat_message(
        user_id,
        session_id,
        "session",
        ConversationMessage(
            role=ParticipantRole.USER.value,
            content=[{'text': f"{initiating_agent.id}: {next_request}"}]
        )
    )
    
    max_turns = 10
    turn_count = 0
    conversation_ended = False

    while not conversation_ended and turn_count < max_turns:
        turn_count += 1
        print(f"\n======= Turn {turn_count} =======")
        current_agent = classifier.peek_next_agent()
        print(f"--- Agent receiving message: {current_agent.id} ---")

        print("***************CHAT HISTORY FROM CONSISTENT POV OF INITIATING AGENT:")
        # Fetch the real chat history from the orchestrator's storage
        chat_history = await orchestrator.storage.fetch_chat(user_id, session_id, initiating_agent.id)
        
        # Update UI
        ui_history = []
        for message in chat_history:
            agent_id = initiating_agent_id if message.role == ParticipantRole.ASSISTANT.value else other_agent_id
            raw_content = ""
            if message.content and isinstance(message.content, list) and len(message.content) > 0 and message.content[0].get('text'):
                raw_content = message.content[0]['text']
            
            # Strip the agent ID prefix if it exists
            if raw_content.startswith(f"{initiating_agent_id}: "):
                raw_content = raw_content.replace(f"{initiating_agent_id}: ", "", 1)

            # Extract tool calls and the clean message content
            tool_calls = re.findall(r'\[TOOL_CALL\](.*?)\[/TOOL_CALL\]', raw_content)
            clean_content = re.sub(r'\[TOOL_CALL\].*?\[/TOOL_CALL\]', '', raw_content).strip()

            # Add tool call messages to the history
            for tool_name in tool_calls:
                ui_history.append({
                    'role': message.role,
                    'agent_id': agent_id,
                    'type': 'tool',
                    'content': f"Running tool: {tool_name}"
                })
            
            # Add the clean conversational message to the history
            if clean_content:
                ui_history.append({
                    'role': message.role,
                    'agent_id': agent_id,
                    'type': 'message',
                    'content': clean_content
                })
        update_chat_history(ui_history)

        index = 1


        for message in chat_history:
            print(f"  {index}. Role: {message.role}, Content: {(json.dumps(message.content).replace('\n',' '))[0:100]}")
            index = index + 1
        print("***************END CHAT HISTORY")



        # The system prompt is now set in the agent factory.
        # The "next_request" variable holds the conversational message.
        classifier_result = ClassifierResult(selected_agent=current_agent, confidence=1.0)
        response = await orchestrator.agent_process_request(
            next_request,
            user_id,
            session_id,
            classifier_result,
            additional_params={
                "scenario": orchestrator.scenario_data,
                "agent_config": current_agent.agent_config
            }
        )
        
        print(f"\n--- Response from {response.metadata.agent_name} ---")

        if response.streaming:
            full_response = ""
            async for chunk in response:
                full_response += chunk
            response_text = full_response
        else:
            response_text = response.output.content[0]['text']
        
        print("response_text = ", response_text)

        # The orchestrator automatically saves the turn to the speaker's history.
        # We need to manually save it to the listener's history with roles flipped.
        agent_listening = next((agent for agent in agents if agent.id != current_agent.id), None)
        if agent_listening:
            # The user message for the speaker is the current `next_request`
            user_message = ConversationMessage(role=ParticipantRole.USER.value, content=[{'text': next_request}])
            # The assistant message from the speaker is the response
            assistant_message = response.output

            # Save to the listener's history with roles flipped
            await orchestrator.storage.save_chat_message(
                user_id, session_id, agent_listening.id,
                ConversationMessage(role=ParticipantRole.ASSISTANT.value, content=user_message.content)
            )
            await orchestrator.storage.save_chat_message(
                user_id, session_id, agent_listening.id,
                ConversationMessage(role=ParticipantRole.USER.value, content=assistant_message.content)
            )

        # The next request for the other agent is the raw response text
        next_request = response_text
        
        # Advance to the next agent
        classifier.advance_turn()

        if 'toolUse' in response_text:
            print(f"WARNING: A TOOL USE REQUEST HAS SURFACED IN THE CONVERSATION: {response_text}")

        #Check for the termination signal in the response text
        if "END OF CONVERSATION" in response_text:
            conversation_ended = True
            print("\n--- Conversation has ended ---")

    # Perform one final UI update to ensure the last message is displayed
    chat_history = await orchestrator.storage.fetch_chat(user_id, session_id, initiating_agent.id)
    ui_history = []
    for message in chat_history:
        agent_id = initiating_agent_id if message.role == ParticipantRole.ASSISTANT.value else other_agent_id
        raw_content = ""
        if message.content and isinstance(message.content, list) and len(message.content) > 0 and message.content[0].get('text'):
            raw_content = message.content[0]['text']

        if raw_content.startswith(f"{initiating_agent_id}: "):
            raw_content = raw_content.replace(f"{initiating_agent_id}: ", "", 1)

        tool_calls = re.findall(r'\[TOOL_CALL\](.*?)\[/TOOL_CALL\]', raw_content)
        clean_content = re.sub(r'\[TOOL_CALL\].*?\[/TOOL_CALL\]', '', raw_content).strip()

        for tool_name in tool_calls:
            ui_history.append({
                'role': message.role,
                'agent_id': agent_id,
                'type': 'tool',
                'content': f"Running tool: {tool_name}"
            })
        
        if clean_content:
            ui_history.append({
                'role': message.role,
                'agent_id': agent_id,
                'type': 'message',
                'content': clean_content
            })
    update_chat_history(ui_history)
    
    if not conversation_ended:
        print("\n--- Maximum turns reached, ending conversation ---")

    # Give the UI a moment to fetch the final update before the script exits
    time.sleep(3)

if __name__ == "__main__":
    asyncio.run(main(sys.argv))
