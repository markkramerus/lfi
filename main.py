import asyncio
import os
import sys
import uuid
from dotenv import load_dotenv
from agent_squad.orchestrator import AgentSquad, AgentSquadConfig
from alternating_classifier import AlternatingClassifier
from agent_factory import create_agents_from_scenario

# Load environment variables
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

async def main(args):
    """Main function to demonstrate secure, agent-contained tool use."""
    print("--- Starting Secure Tool Use Demonstration ---")
    if len(args) != 2:
        print("You must pass in the name of the scenario as the command line argument")
        return
    else:
    # 1. Create agents from the scenario      
        scenario_path = os.path.join('scenarios', args[1])
        if not scenario_path.endswith('.json'):
            scenario_path = f'{scenario_path}.json'
    agents = create_agents_from_scenario(scenario_path)
    if not agents:
        print("No agents were created. Exiting.")
        return

    # 2. Set up the orchestrator
    initiating_agent = next((agent for agent in agents if 'messageToUseWhenInitiatingConversation' in agent.agent_config), None)
    if not initiating_agent:
        print("Could not find an initiating agent in the scenario.")
        return
    
    classifier = AlternatingClassifier(initiating_agent_id=initiating_agent.id)
    orchestrator = AgentSquad(
        classifier=classifier,
        options=AgentSquadConfig(
            LOG_CLASSIFIER_OUTPUT=True
        )
    )
    for agent in agents:
        orchestrator.add_agent(agent)

    # 3. Simulate a conversation that requires tool use
    user_id = "user_123"
    session_id = str(uuid.uuid4())
    
    next_request = initiating_agent.agent_config['messageToUseWhenInitiatingConversation']
    
    max_turns = 10
    turn_count = 0
    conversation_ended = False

    while not conversation_ended and turn_count < max_turns:
        turn_count += 1
        print(f"\n--- Turn {turn_count}: Sending request ---")
        
        response = await orchestrator.route_request(next_request, user_id, session_id)

        print(f"\n--- Response from {response.metadata.agent_name} ---")
        if response.streaming:
            full_response = ""
            async for chunk in response:
                full_response += chunk
                print(chunk, end="", flush=True)
            print()
            next_request = full_response
        else:
            response_text = response.output.content[0]['text']
            print(response_text)
            next_request = response_text

        # Check for the termination signal in the response text
        if "{\"conversation_status\": \"completed\"}" in next_request:
            conversation_ended = True
            # Remove the signal from the response text
            next_request = next_request.replace("{\"conversation_status\": \"completed\"}", "").strip()
            print("\n--- Conversation has ended ---")

    if not conversation_ended:
        print("\n--- Maximum turns reached, ending conversation ---")

    print("\n--- Demonstration Complete ---")

if __name__ == "__main__":
    asyncio.run(main(sys.argv))
