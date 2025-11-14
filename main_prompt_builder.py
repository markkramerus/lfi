import json

def schema_to_string(schema):
    return json.dumps(schema, indent=2)


def build_main_prompt(scenario, agent_config):
    other_agents = [a for a in scenario.get('agents', []) if a['agentId'] != agent_config['agentId']]

    # parts = ['<SCENARIO>']
    # md = scenario.get('metadata', {})
    # if md.get('title') or md.get('id'):
    #     parts.append(f"Title: {md.get('title') or md.get('id')}")
    # if md.get('description'):
    #     parts.append(f"Description: {md['description']}")
    # if md.get('background'):
    #     parts.append(f"Background: {md['background']}")
    # parts.append('</SCENARIO>\n<YOUR_ROLE>')
    parts = []
    #parts.append(f'You are agent "{agent_config["agentId"]}" for {agent_config.get("principal", {}).get("name", "Unknown")}.')
    parts.append(f'You are agent "{agent_config["agentId"]}"')
    # if agent_config.get('principal', {}).get('description'):
    #     parts.append(f"Principal Info: {agent_config['principal']['description']}")
    # if agent_config.get('principal', {}).get('type'):
    #     parts.append(f"Principal Type: {agent_config['principal']['type']}")
    if agent_config.get('systemPrompt'):
        parts.append(f"Instructions: {agent_config['systemPrompt']}")
    if agent_config.get('goals'):
        parts.append('Goals:\n' + '\n'.join(f"- {g}" for g in agent_config['goals']))
    if agent_config.get('situation'):
        parts.append(f"Current task: {agent_config['situation']}")

    # if len(other_agents) == 1:
    #     other_agent = other_agents[0]
    #     info=["<OTHER PARTY'S ROLE>"]
    #     info = [f"{other_agent['agentId']} for {other_agent.get('principal', {}).get('name', 'Unknown')}"]
    #     if other_agent.get('principal', {}).get('description'):
    #         info.append(f"desc: {other_agent['principal']['description']}")
    #     if other_agent.get('principal', {}).get('type'):
    #         info.append(f"type: {other_agent['principal']['type']}")
    #     info.append("</OTHER PARTY'S ROLE>")
    #     parts.append('\n'.join(info))

    parts.append(f'''
Ending the conversation:
If your goal has been achieved and acknowledged by the other party, end the conversation by appending "END OF CONVERSATION" to your message. 
A tool may also signal you to start bringing the conversation to a close by including "START WRAPPING UP THE CONVERSATION" in its output.
Before ending the conversation, ask if there is anything else the other party needs, or if there are any more questions. Signal "END OF CONVERSATION" only when both parties have no more questions or activities.
Be polite, and do not cut off abruptly, but at the same time, do not drag the conversation out for no reason.
''')

    return '\n'.join(parts)
