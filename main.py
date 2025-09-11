import asyncio
import os
import sys
import uuid
import json
import logging
from dotenv import load_dotenv
from agent_squad.orchestrator import AgentSquad, AgentSquadConfig
from agent_squad.types import ConversationMessage, ParticipantRole
from agent_squad.classifiers import ClassifierResult
from agent_chooser import AgentChooser
from agent_factory import create_agents_from_scenario
from main_prompt_builder import build_main_prompt

# Suppress httpx info logs
logging.getLogger("httpx").setLevel(logging.WARNING)

# Load environment variables
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MAX_HISTORY = 10000

async def main(args):
    """Main function to demonstrate secure, agent-contained tool use."""
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

    # 2. Set up the orchestrator
    initiating_agent = next((agent for agent in agents if 'messageToUseWhenInitiatingConversation' in agent.agent_config), None)
    if not initiating_agent:
        print("Could not find an initiating agent in the scenario.")
        return
    
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

    if not conversation_ended:
        print("\n--- Maximum turns reached, ending conversation ---")

if __name__ == "__main__":
    asyncio.run(main(sys.argv))
