from agent_squad.agents import AnthropicAgent
from prompt_builder import finalization_reminder

class CustomAnthropicAgent(AnthropicAgent):
    """
    A custom Anthropic agent that injects a finalization reminder
    into the prompt when a terminal tool has been used.
    """
    async def _process_tool_result(self, tool_name, tool_result, original_messages):
        """
        Overrides the base method to add a finalization reminder to the prompt.
        """
        messages = original_messages.copy()
        
        # Find the tool definition to check if it's a terminal tool
        tool = self.tool_config.tool.get_tool(tool_name)
        if tool and tool.ends_conversation:
            # This is a terminal tool, so inject the finalization reminder.
            # The reminder is added to the last user message.
            # I am making an assumption here that the last message is the one
            # that contains the tool result.
            last_message = messages[-1]
            if last_message['role'] == 'user':
                # It's common for the tool result to be part of a user message
                # in the conversation history.
                if isinstance(last_message['content'], list):
                    # Find the tool result content block and append the reminder
                    for content_block in last_message['content']:
                        if content_block.get('type') == 'tool_result':
                            content_block['content'] += finalization_reminder()
                            break
                else:
                    # If it's just a string, append the reminder
                    last_message['content'] += finalization_reminder()

        return await super()._process_tool_result(tool_name, tool_result, messages)
