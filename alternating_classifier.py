from agent_squad.classifiers import Classifier, ClassifierResult
from agent_squad.types import ConversationMessage
from typing import List

class AlternatingClassifier(Classifier):
    """
    A stateful classifier that alternates between two agents in a scenario-agnostic way.
    """
    def __init__(self, initiating_agent_id: str):
        super().__init__()
        self.initiating_agent_id = initiating_agent_id
        self.last_agent_id = None

    async def process_request(
        self,
        input_text: str,
        chat_history: List[ConversationMessage]
    ) -> ClassifierResult:
        """
        Selects the next agent based on the conversation history.
        """
        agent_list = list(self.agents.values())
        if len(agent_list) != 2:
            return ClassifierResult(selected_agent=agent_list[0] if agent_list else None, confidence=1.0)

        if not self.last_agent_id:
            # First turn. The initiator is sending the first message, so we select the other agent.
            for agent in agent_list:
                if agent.id != self.initiating_agent_id:
                    selected_agent = agent
                    break
        else:
            # Subsequent turns. Select the agent that is not the last one.
            for agent in agent_list:
                if agent.id != self.last_agent_id:
                    selected_agent = agent
                    break
        
        self.last_agent_id = selected_agent.id
        return ClassifierResult(selected_agent=selected_agent, confidence=1.0)
