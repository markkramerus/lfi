import json



def schema_to_string(schema):
    return json.dumps(schema, indent=2)

# def build_tools_catalog(scenario, current_agent):
#     lines = ["""
# <AVAILABLE TOOLS>
# If you want to call a tool, you will return this JSON structure: {"tool_name": string, "args": dict}
# Here are the available tools:
# """]
#     have_tool = False
#     for tool_config in  current_agent.agent_config.get('tools', []):
#         have_tool = True
#         lines.append(f"Tool: {tool_config['toolName']}(args: dict)")
#         lines.append(f"// {tool_config.get('description', '')}".strip())
#         schema_str = schema_to_string(tool_config.get('inputSchema'))
#         lines.append(f"Input Schema for {tool_config['toolName']}:\n{schema_str}")
#         lines.append('')
#     lines.append('</AVAILABLE TOOLS>')
#     if have_tool:
#         return '\n'.join(lines)
#     else:
#         return ''

def finalization_reminder():
    return """
<FINALIZATION>
Your response will be the last message in the conversation.
Compose ONE final message to the remote agent summarizing the outcome and key reasons.
IMPORTANT: Include the exact phrase "END OF CONVERSATION" at the conclusion of your response.
</FINALIZATION>
"""


def build_main_prompt(scenario, current_agent, chat_history, available_files_xml=None, finalization_reminder=None):
    other_agents = [a for a in scenario.get('agents', []) if a['agentId'] != current_agent.id]
    agent_config = current_agent.agent_config # entire agent description dictionary from scenario file

    history_str = ""
    if chat_history:
        for message in chat_history:
            role = message.role
            content = ""
            if message.content and isinstance(message.content, list) and 'text' in message.content[0]:
                content = message.content[0]['text']
            history_str += f"{role}: {content}\n"
    else:
        history_str = "<!-- no conversation history -->"

    parts = ['<SCENARIO>']
    md = scenario.get('metadata', {})
    if md.get('title') or md.get('id'):
        parts.append(f"Title: {md.get('title') or md.get('id')}")
    if md.get('description'):
        parts.append(f"Description: {md['description']}")
    if md.get('background'):
        parts.append(f"Background: {md['background']}")
    parts.append('</SCENARIO>\n<YOUR_ROLE>')
    parts.append(f'You are agent "{current_agent.id}" for {agent_config.get('principal', {}).get('name', 'Unknown')}.')
    if agent_config.get('principal', {}).get('description'):
        parts.append(f"Principal Info: {agent_config['principal']['description']}")
    if agent_config.get('principal', {}).get('type'):
        parts.append(f"Principal Type: {agent_config['principal']['type']}")
    if agent_config.get('systemPrompt'):
        parts.append(f"System: {agent_config['systemPrompt']}")
    if agent_config.get('situation'):
        parts.append(f"Situation: {agent_config['situation']}")
    if agent_config.get('goals'):
        parts.append('Goals:\n' + '\n'.join(f"- {g}" for g in agent_config['goals']))
    parts.append('</YOUR_ROLE>')

    if len(other_agents) == 1:
        other_agent = other_agents[0]
        info=["<OTHER PARTY'S ROLE>"]
        info = [f"{other_agent['agentId']} for {other_agent.get('principal', {}).get('name', 'Unknown')}"]
        if other_agent.get('principal', {}).get('description'):
            info.append(f"desc: {other_agent['principal']['description']}")
        if other_agent.get('principal', {}).get('type'):
            info.append(f"type: {other_agent['principal']['type']}")
        info.append("</OTHER PARTY'S ROLE>")
        parts.append('\n'.join(info))

    parts.extend(['<CONVERSATION_HISTORY>', history_str, '</CONVERSATION_HISTORY>'])

# Do not provide the tools in the prompt - the framework will invoke them.
    # tools_catalog = build_tools_catalog(scenario, current_agent)
    # #print("tools_catalog ", tools_catalog)
    # parts.append(tools_catalog)

    parts.append("""
<TOOLING_GUIDANCE>
- First review the conversation history to check for any required information. If found, do not repeat the tool call. 
- Call only the necessary tools directly related to the original prompt.
- After obtaining the necessary information, answer the original prompt with a message directed at the other party.
- Keep all exchanges in this conversation thread; do not refer to portals/emails/fax.",
</TOOLING_GUIDANCE>
    """)

    if finalization_reminder and finalization_reminder.strip():
        parts.extend(['', finalization_reminder.strip(), ''])

    parts.append("""
<RESPONSE>
You have two response options: request to run a tool to get more information, or compose a response to the other party. In both cases, respond with exactly ONE JSON object:
- If you have the information needed to advance the conversation, your response should be a message for other party, in plain text, using a professional tone, and without extraneous commentary. Use the schema: {"action": "send_message", "message": str}
- If sending the final response, ending the conversation, conclude your message with the exact phrase "END OF CONVERSATION".
- If you need to run a tool to get the information needed to compose a response, respond using the schema: {"action": "toolUse", "tool_name": str, "args": object}
</RESPONSE>
""")
    return '\n'.join(parts)
