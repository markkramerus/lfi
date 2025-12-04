import json

def schema_to_string(schema):
    return json.dumps(schema, indent=2)


def build_main_prompt(scenario, agent_config):

    parts = []
    parts.append('<ROLE>')
    parts.append(f'You are agent named {agent_config["agentName"]}')   # name is required, ID is less important
    principal = agent_config.get("principal")
    if principal is not None:
        parts.append(f'You represent {principal.get("name", " an unspecified organization or individual")}.')
        if principal.get('description'):
            parts.append(f'They are a {principal.get("type", "entity")} described as: {principal.get("description")}')
    parts.append('</ROLE>')
    if agent_config.get('systemPrompt'):
        parts.append('<GENERAL INSTRUCTIONS>')
        parts.append(agent_config['systemPrompt'])
        if agent_config.get('goals'):
            parts.append('Your goals are as follows:\n' + '\n'.join(f"- {g}" for g in agent_config['goals']))
        parts.append('/GENERAL INSTRUCTIONS>')

    parts.append('<CURRENT SCENARIO>')
    if scenario.get('title'):
        parts.append(f"Situation title: {scenario.get('title') or scenario.get('id')}")
    parts.append(agent_config['situation'])
    if scenario.get('description'):
        parts.append(f"Situation description: {scenario['description']}")
    if scenario.get('background'):
        parts.append(f"Situation background: {scenario['background']}")
    parts.append('</CURRENT SCENARIO>')

    other_agents = [a for a in scenario.get('agents', []) if a['agentId'] != agent_config['agentId']]
    if len(other_agents) == 1:
        other_agent = other_agents[0]
        parts.append("<COUNTERPARTY>")
        parts.append(f"In this scenario, you will be conversiting with an agent named {other_agent['agentName']}")
        other_principal = other_agent.get("principal")
        if other_principal:
            parts.append(f"That agent represents {other_principal.get('name', ' an unspecified organization or individual')}.")
            if other_principal.get('description'):
                parts.append(f'They are a {other_principal.get("type", "entity")} described as: {other_principal.get("description")}')
        parts.append("</COUNTERPARTY>")
    parts.append('<CONVERSATION RULES>')
    parts.append('You will be having a back and forth conversation with the counterparty agent. You will stick to your role in the conversation. You will use the provided conversational history to avoid repeating items already discussed. You will use the available tools to get required data when that data is not already available in the conversational history. You will be polite and efficient, keeping your responses short and to the point. After the initial turns, if you cannot see the conversational history, you will reply with "I AM SORRY - I CANNOT ACCESS THE CONVERSATIONAL HISTORY AT THIS TIME - END OF CONVERSATION."')
    parts.append('</CONVERSATION RULES>')
    parts.append('<ENDING THE CONVERSATION>')
    parts.append('If your goal has been achieved and acknowledged by the other party, end the conversation by appending "END OF CONVERSATION" to your message. A tool may also signal you to start bringing the conversation to a close by including "START WRAPPING UP THE CONVERSATION" in its output. Before ending the conversation, ask if there is anything else the other party needs, or if there are any more questions. Signal "END OF CONVERSATION" only when both parties have no more questions or activities. Be polite, and do not cut off abruptly, but at the same time, do not drag the conversation out for no reason.')
    parts.append('</ENDING THE CONVERSATION>')
    return '\n'.join(parts)
