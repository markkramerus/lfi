import json
import os
from dotenv import load_dotenv
from custom_agent import CustomAnthropicAgent
from agent_squad.agents import AnthropicAgentOptions
from agent_squad.utils import AgentTool, AgentTools
import tools as tool_functions
import inspect

# Load environment variables from .env file
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Dynamically build the tool function map from the tools.py module
TOOL_FUNCTION_MAP = {name: func for name, func in inspect.getmembers(tool_functions, inspect.isfunction)}

def placeholder_tool_func(*args, **kwargs):
    """A placeholder for tools that are defined in the scenario but not yet implemented."""
    print(f"--- Placeholder tool called with args: {args}, kwargs: {kwargs} ---")
    return "Tool function not implemented."

def create_agents_from_scenario(file_path: str):
    """
    Reads a scenario configuration file and creates a list of Anthropic agents.

    Args:
        file_path: The path to the scenario JSON file.

    Returns:
        A list of configured AnthropicAgent instances.
    """
    with open(file_path, 'r') as f:
        scenario_data = json.load(f)

    agents = []
    for agent_config in scenario_data.get('agents', []):
        # Create tools for the agent
        agent_tools = []
        for tool_config in agent_config.get('tools', []):
            input_schema = tool_config.get('inputSchema', {})
            tool_name = tool_config.get('toolName')
            # Look up the real function, or use the placeholder if not found
            tool_function = TOOL_FUNCTION_MAP.get(tool_name, placeholder_tool_func)
            agent_tool = AgentTool(
                name=tool_name,
                description=tool_config.get('description'),
                properties=input_schema.get('properties', {}),
                required=input_schema.get('required', []),
                func=tool_function
            )
            agent_tools.append(agent_tool)
        tools = AgentTools(agent_tools)

        # Create the agent with the enhanced options
        agent = CustomAnthropicAgent(AnthropicAgentOptions(
            name=agent_config.get('agentId'),
            description=agent_config.get('situation'),
            api_key=ANTHROPIC_API_KEY,
            model_id='claude-sonnet-4-20250514',  # Default model
            streaming=False,
            custom_system_prompt={"template": agent_config.get('systemPrompt')},
            #tool_config=AgentTools(tools=agent_tools) if agent_tools else None
            tool_config = {'tool': tools, 'toolMaxRecursions': 5}
        ))
        agent.agent_config = agent_config
        agents.append(agent)

    return agents
