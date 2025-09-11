import json
import os
from dotenv import load_dotenv
from custom_agent import CustomAnthropicAgent
from agent_squad.agents import AnthropicAgentOptions
from agent_squad.utils import AgentTool, AgentTools
import local_tools as local_tools
from custom_agent import mcp_tool_func, tool_surrogate_func
import inspect

# Load environment variables from .env file
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Get a list of tools implemented in the tools.py file
LOCALLY_IMPLEMENTED_TOOLS = {name: func for name, func in inspect.getmembers(local_tools, inspect.isfunction)}



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
            tool_name = tool_config.get('toolName')
            tool_function = LOCALLY_IMPLEMENTED_TOOLS.get(tool_name)
            mcp_server = tool_config.get('mcpServer')
            if tool_function:
                # Locally implemented tool
                pass
            elif mcp_server:
                # MCP tool
                tool_function = mcp_tool_func
            else:
                # Surrogate for an unimplemented tool
                tool_function = tool_surrogate_func

            # make sure the tool name is passed to the tool surrogate function
            properties=tool_config.get('inputSchema', {}).get('properties', {})
            properties['tool_name'] = {'type': 'string', 'enum': [tool_name]}
            required=tool_config.get('inputSchema', {}).get('required', [])
            required = required.append('tool_name')
            
            agent_tool = AgentTool(
                name=tool_name,
                description=tool_config.get('description'),
                properties=properties,
                required=required,
                func=tool_function
            )
            agent_tools.append(agent_tool)
        tools = AgentTools(agent_tools)

        # Create the agent with the enhanced options
        agent = CustomAnthropicAgent(AnthropicAgentOptions(
            name=agent_config.get('agentId'),
            description=agent_config.get('situation'),
            api_key=ANTHROPIC_API_KEY,
            #model_id='claude-sonnet-4-20250514',  # Default model
            model_id = 'claude-3-7-sonnet-latest',
            streaming=False,
            custom_system_prompt={"template": agent_config.get('systemPrompt')},
            tool_config = {'tool': tools, 'toolMaxRecursions': 5}
        ))
        # Save the entire configuration dictionary
        agent.agent_config = agent_config
        agents.append(agent)

    return scenario_data, agents
