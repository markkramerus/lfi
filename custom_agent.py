import json
import os
import re
from dotenv import load_dotenv
from agent_squad.agents import AnthropicAgent, AnthropicAgentOptions
from tool_surrogate_prompt_builder import build_tool_surrogate_prompt
from agent_squad.types import ConversationMessage
from typing import List, Dict, Optional, Union, AsyncIterable

SCENARIO = None
AGENT_CONFIG = None
INPUT_TEXT = None
CHAT_HISTORY = None
ANTHROPIC_AGENT = None
TOOL_CALLS_THIS_TURN = []

load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

def strip_fences(text):
    return (match.group(1).strip() if (match := re.search(r'```(?:\w+)?\s*(.*?)\s*```', text, re.DOTALL)) else text)

class CustomAnthropicAgent(AnthropicAgent):
    """
    The custom Anthropic agent uses an tool surrogate to generate
    realistic tool outputs for surrogate tools.
    """
    async def process_request(
        self,
        input_text: str,
        user_id: str,
        session_id: str,
        chat_history: List[ConversationMessage],
        additional_params: Optional[Dict[str, str]] = None
    ) -> Union[ConversationMessage, AsyncIterable[any]]:
        """
        Overrides the base method to inject tool surrogate logic for surrogate tools.
        """
        global SCENARIO, AGENT_CONFIG, INPUT_TEXT, CHAT_HISTORY, USER_ID, SESSION_ID, TOOL_CALLS_THIS_TURN
        TOOL_CALLS_THIS_TURN = []
        SCENARIO = additional_params.get("scenario")
        AGENT_CONFIG = additional_params.get("agent_config")
        CHAT_HISTORY = chat_history
        INPUT_TEXT = input_text
        USER_ID = user_id
        SESSION_ID = session_id

        if not SCENARIO or not AGENT_CONFIG:
            print("--- DEBUG: Missing scenario or agent_config ---")
            return ConversationMessage(role="assistant", content=[{"type": "text", "text": "Error: Missing scenario or agent_config"}])

        #print(f"\n--- CustomAnthropicAgent.process_request ---")
        #print("Chat history received:")
        #for message in chat_history:
        #    print(f"  - Role: {message.role}, Content: {message.content}")
        #print(f"input_text: {input_text[0:200]}...(truncated)")

        result = await super().process_request(input_text, user_id, session_id, chat_history, additional_params)
        
        if TOOL_CALLS_THIS_TURN:
            tool_markers = "".join([f"[TOOL_CALL]{tool_name}[/TOOL_CALL]" for tool_name in TOOL_CALLS_THIS_TURN])
            if isinstance(result, ConversationMessage):
                original_text = result.content[0].get('text', '')
                result.content[0]['text'] = f"{tool_markers}{original_text}"
            else: # It's an async iterable (streaming)
                async def stream_wrapper():
                    yield tool_markers
                    async for chunk in result:
                        yield chunk
                return stream_wrapper()

        return result

async def tool_surrogate_func(*args, **kwargs):
    """A surrogate for tools that are defined in the scenario but not yet implemented."""
    tool_name = kwargs.get('tool_name')
    if tool_name is None:
        print(f"WARNING: Tool name (required) was not included in a tool execution request. Arguments passed by LLM: {kwargs}. SKIPPING.")
        return("Unable to execute unnamed tool. Make sure the 'tool_name' parameter is always provided when requesting tool execution.")
    print(f"--- Tool {tool_name} called with inputs: {kwargs} ---")
    global TOOL_CALLS_THIS_TURN
    TOOL_CALLS_THIS_TURN.append(tool_name)
    current_tool_config = None
    for tool_config in AGENT_CONFIG.get('tools', []):
        if tool_config.get('toolName') == tool_name:
            current_tool_config = tool_config
            break
    if not current_tool_config:
        print(f"--- DEBUG: Cannot find tool config for {tool_name} ---")
        return "Tool failed to execute."

    prompt = build_tool_surrogate_prompt(
        scenario=SCENARIO,
        agent_config=AGENT_CONFIG,
        tool_name = tool_name,
        tool_config = current_tool_config,
        args=kwargs,
        chat_history=CHAT_HISTORY,
    )
    #print(f"--- DEBUG: created surrogate prompt", type(prompt))
    # Call the LLM with the prompt using a very simple agent that has no tools, no customization
    SimpleAgent= AnthropicAgent(AnthropicAgentOptions(
        name='Anthropic Assistant',
        description='A simple AI assistant',
        api_key=ANTHROPIC_API_KEY,
        model_id = 'claude-3-7-sonnet-latest',
        streaming=False
    ))

    response = await SimpleAgent.process_request(prompt, USER_ID, SESSION_ID, [])
    # The response from the LLM is a ConversationMessage, e.g., (role="assistant", content=[{"type": "text", "text": "Error: Missing scenario or agent_config"}])
    trimmed_response = strip_fences(response.content[0].get('text', 'Error: No text included in the tool agent response.'))
    print(f"--- Response from surrogate tool (trimmed): {' '.join(trimmed_response[0:100].replace('\n',' ').split())}")
    
    # Check if the tool is meant to end the conversation
    if current_tool_config.get("endsConversation"):
        print(f"--- Tool {tool_name} is configured to end the conversation. ---")
        trimmed_response += "\nSTART WRAPPING UP THE CONVERSATION"
        
    return trimmed_response

# not used
def mcp_tool_func(*args, **kwargs):
    """A placeholder for MCP tool calls."""
    print(f"--- MCP tool called with args: {args}, kwargs: {kwargs} ---")
    # In a real implementation, this would trigger an MCP call
    return "MCP tool function not implemented."
