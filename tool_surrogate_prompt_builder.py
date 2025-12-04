import json

MAX_HISTORY = 10000

# Helper function for safe JSON serialization
def safe_stringify(data, indent=2):
    try:
        return json.dumps(data, indent=indent)
    except TypeError:
        return str(data)


def task(tool_name, tool_config, args):
    guidance = tool_config.get("synthesisGuidance", "no additional guidance provided")
    description = tool_config.get('description', 'no description provided')
    inputs =  json.dumps(tool_config.get('inputSchema'))
    return f"""
<TASK>
You are an omniscient Tool Surrogate / World Simulator for a scenario-driven, multi-agent conversation.
Your task is to simulate a tool call with realistic, in-character results.
Here is information about the tool you will be simulating:
Tool Name: {tool_name}.
Tool Description: {description}
Input Schema: {inputs}
Input Parameter Values: {args}
Synthesis Guidance: {guidance}
</TASK>
"""

def scenario_header(scenario):
    title = scenario.get('scenario', {}).get('title', '(untitled)')
    desc = scenario.get('scenario', {}).get('description', '')
    return f"""
<SCENARIO>
- id: {scenario.get('scenario', {}).get('id', '(missing-id)')}
- title: {title}
- description: {desc}
</SCENARO>
"""

def agent_profile(agent_config):
    principal = agent_config.get('principal', {})
    principal_str = f"{principal.get('name', '(principal not specified)')} — {principal.get('description', '')}"
    goals = agent_config.get('goals', [])
    goals_str = "\n".join([f"  - {g}" for g in goals]) if goals else "  (none)"
    return f"""
<CALLING_AGENT>
You are providing this information to:
- agentId: {agent_config.get('agentId', '(unknown)')}
- principal: {principal_str}
- situation: {agent_config.get('situation', '(not specified)')}
- systemPrompt: {agent_config.get('systemPrompt', '(not specified)')}
- goals:
{goals_str}
</CALLING_AGENT>
"""

def knowledge_base(agent_config):
    kb = json.dumps(agent_config.get("knowledgeBase", "none"))
    return f"""
<KNOWLEDGE_BASE>
Information available to you for this task:
{kb}
</KNOWLEDGE_BASE>
"""

def general_guidance():
    return """
<GENERAL_GUIDANCE>
- Action focus: Use the tool name and the provided arguments as the primary source of truth. Produce the best possible result that this tool would return for those arguments.
- Context use: Conversation history and agent thought may inform realism and details, but do not invent unrelated outputs. Stay aligned with the tool’s role and its inputs.
- Move forward: If inputs are insufficient to progress, include concise next-step suggestions in the document "summary" field (e.g., needed fields and one concrete next action).
- Scope discipline: Do not switch tools or simulate other systems. Only return what this tool would produce.
- Clarity and brevity: Prefer concise, well-structured content. Avoid narrative filler beyond the requested artifacts.
- Follow this additional guidance: {tool.get('synthesisGuidance', '(no additional guidance)')}
</GENERAL_GUIDANCE>
"""

def conversation_history(history):
    """
    Formats the conversation history into a readable string for the prompt.
    """
    history_str = ""
    if history:
        for message in history:
            role = message.role
            content = ""
            if message.content and isinstance(message.content, list) and 'text' in message.content[0]:
                content = message.content[0]['text']
            history_str += f"{role}: {content}\n"
    return f"""
<CONVERSATION_HISTORY>
{history_str.strip()}
</CONVERSATION_HISTORY>
"""


def build_tool_surrogate_prompt(scenario, agent_config, tool_name, tool_config, args, chat_history):
    """
    Assembles the complete tool surrogate prompt by calling all the component functions.
    """ 
    # print("1 ", task(tool_name, tool_config, args))
    # print("2 ", scenario_header(scenario))
    # print("3 ", conversation_history(chat_history))
    # print("4 ", agent_profile(agent_config))
    # print("5 ", knowledge_base(agent_config))
    # print("6 ", general_guidance())

    prompt_parts = [
        task(tool_name, tool_config, args),
        scenario_header(scenario),
        conversation_history(chat_history),
        agent_profile(agent_config),
        knowledge_base(agent_config),
        general_guidance(),
    ]
    
    return "".join(prompt_parts)
