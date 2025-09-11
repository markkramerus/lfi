from agent_squad.classifiers import Classifier, ClassifierResult
from agent_squad.types import ConversationMessage
from typing import List

class AgentChooser(Classifier):
    """
    A stateful classifier that alternates between two agents in a scenario-agnostic way.
    """
    def __init__(self, initiating_agent_id: str):
        super().__init__()
        self.last_agent_id = initiating_agent_id
        print(f"\n--- DEBUG: AgentChooser.__init__ ---")
        print(f"initiating_agent_id: {self.last_agent_id}")

    def peek_next_agent(self):
        """
        Determines the next agent to speak, without advancing the state.
        """
        agent_list = list(self.agents.values())
        if len(agent_list) != 2:
            return agent_list[0] if agent_list else None

        # Select the agent that is not the last one.
        for agent in agent_list:
            if agent.id != self.last_agent_id:
                return agent
        return agent_list[0] # Fallback

    def get_next_agent(self):
        """
        Determines the next agent to speak.
        """
        #print("\n--- DEBUG: AgentChooser.get_next_agent ---")
        agent_list = list(self.agents.values())
        #print(f"agent_list: {agent_list}")
        if len(agent_list) != 2:
            print("--- DEBUG: Not a two-agent scenario ---")
            return agent_list[0] if agent_list else None

        # Select the agent that is not the last one.
        for agent in agent_list:
            if agent.id != self.last_agent_id:
                selected_agent = agent
                break
        
        self.last_agent_id = selected_agent.id
        print(f"--- Agent receiving message: {selected_agent.id} ---")
        return selected_agent

    async def process_request(
        self,
        input_text: str,
        chat_history: List[ConversationMessage]
    ) -> ClassifierResult:
        """
        Selects the next agent based on the conversation history.
        """
        selected_agent = self.get_next_agent()
        #print(f"\n--- DEBUG: At 2: Selected agent: {selected_agent.id}")
        return ClassifierResult(selected_agent=selected_agent, confidence=1.0)
