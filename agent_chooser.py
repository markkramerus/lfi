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

    def advance_turn(self):
        """
        Advances the turn to the next agent.
        """
        next_agent = self.peek_next_agent()
        if next_agent:
            self.last_agent_id = next_agent.id
        return next_agent

    async def process_request(
        self,
        input_text: str,
        chat_history: List[ConversationMessage]
    ) -> ClassifierResult:
        """
        This method is required by the abstract base class, but our implementation
        bypasses it. It will not be called.
        """
        # This logic will not be executed.
        return ClassifierResult(selected_agent=self.peek_next_agent(), confidence=1.0)
