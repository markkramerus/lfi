import asyncio
import os
import sys
import uuid
import ast
from dotenv import load_dotenv
from agent_squad.orchestrator import AgentSquad, AgentSquadConfig
from agent_squad.types import ConversationMessage, ParticipantRole
from agent_chooser import AgentChooser
from agent_factory import create_agents_from_scenario
from main_prompt_builder import build_main_prompt

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
        initiating_agent.id,
        ConversationMessage(
            role=ParticipantRole.USER.value,
            content=[{'text': next_request}]
        )
    )

    call_tool = False
    max_turns = 10
    turn_count = 0
    conversation_ended = False

    while not conversation_ended and turn_count < max_turns:
        turn_count += 1
        print(f"\n======= Turn {turn_count} =======")
        current_agent = classifier.peek_next_agent()
        print(f"--- Agent receiving message: {current_agent.id} ---")
        
        # Fetch the real chat history from the orchestrator's storage
        chat_history = await orchestrator.storage.fetch_chat(user_id, session_id, current_agent.id)
        next_prompt = build_main_prompt(scenario_data, current_agent, chat_history)

        # print(f"\n--- Prompt text: ---")
        # print(next_prompt)

        classifier_result = await orchestrator.classify_request(next_prompt, user_id, session_id)
        response = await orchestrator.agent_process_request(
            next_prompt,
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
            next_request = response_text = full_response
        else:
            response_text = response.output.content[0]['text']
            print("response_text = ", response_text)
            next_request = response_text

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
