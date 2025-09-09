import json

# Helper function for safe JSON serialization
def safe_stringify(data, indent=2):
    try:
        return json.dumps(data, indent=indent)
    except TypeError:
        return str(data)

# Helper function for truncating text
def truncate_text(text, max_length, suffix='...'):
    if not text or len(text) <= max_length:
        return text
    if max_length <= len(suffix):
        return text[:max_length]
    return text[:max_length - len(suffix)] + suffix

def finalization_reminder():
    return """
<FINALIZATION_REMINDER>
You have invoked a terminal tool that ends the conversation.
Compose ONE final message to the remote agent:
- Summarize the outcome and key reasons.
- Append the following JSON object to the very end of your message: {"conversation_status": "completed"}
</FINALIZATION_REMINDER>
"""

def system_role():
    return """
<SYSTEM_ROLE>
You are an omniscient Oracle / World Simulator for a scenario-driven, multi-agent conversation.
Your role: execute a tool call with realistic, in-character results.
</SYSTEM_ROLE>
"""

def format_scenario_header(scenario):
    title = scenario.get('metadata', {}).get('title', '(untitled)')
    desc = scenario.get('metadata', {}).get('description', '')
    tags = scenario.get('metadata', {}).get('tags', [])
    tags_str = f" [tags: {', '.join(tags)}]" if tags else ''
    return f"""
SCENARIO:
- id: {scenario.get('metadata', {}).get('id', '(missing-id)')}
- title: {title}{tags_str}
- description: {desc}
"""

def format_agent_profile(agent):
    principal = agent.get('principal', {})
    principal_str = f"{principal.get('name', '(principal not specified)')} — {principal.get('description', '')}"
    goals = agent.get('goals', [])
    goals_str = "\\n".join([f"  - {g}" for g in goals]) if goals else "  (none)"
    return f"""
CALLING AGENT PROFILE:
- agentId: {agent.get('agentId', '(unknown)')}
- principal: {principal_str}
- situation: {agent.get('situation', '(not specified)')}
- systemPrompt: {agent.get('systemPrompt', '(not specified)')}
- goals:
{goals_str}
"""

def calling_agent_kb(agent):
    kb = agent.get('knowledgeBase', {})
    kb_str = safe_stringify(kb)
    kb_trunc = truncate_text(kb_str, 30000, '... [calling agent knowledge truncated]')
    return f"""
<CALLING_AGENT_KB>
{kb_trunc or '(none)'}
</CALLING_AGENT_KB>
"""

def format_scenario_knowledge(scenario):
    k = scenario.get('knowledge', {})
    if not k:
        return "SCENARIO KNOWLEDGE: (none)"
    facts = k.get('facts', [])
    facts_str = "\\n".join([f"  {i+1}. {f}" for i, f in enumerate(facts)]) if facts else "  (none)"
    documents = k.get('documents', [])
    documents_str = "\\n".join([f"  - [{d.get('id')}] {d.get('title')} ({d.get('type')})" for d in documents]) if documents else "  (none)"
    refs = k.get('references', [])
    refs_str = "\\n".join([f"  - {r.get('title')}: {r.get('url')}" for r in refs]) if refs else "  (none)"
    return f"""
SCENARIO KNOWLEDGE (shared ground-truth available to the Oracle):
Facts:
{facts_str}
Documents (IDs usable for synthesized refs):
{documents_str}
References:
{refs_str}
"""

def scenario_metadata(scenario):
    meta = {
        'id': scenario.get('metadata', {}).get('id'),
        'title': scenario.get('metadata', {}).get('title'),
        'description': scenario.get('metadata', {}).get('description'),
        'background': scenario.get('metadata', {}).get('background'),
        'challenges': scenario.get('metadata', {}).get('challenges'),
        'tags': scenario.get('metadata', {}).get('tags'),
    }
    return f"""
<SCENARIO_METADATA>
{safe_stringify(meta)}
</SCENARIO_METADATA>
"""

def agent_thought_leading_to_tool_call(leading_thought):
    if not leading_thought:
        return ""
    return f"""
<AGENT_THOUGHT_LEADING_TO_TOOL_CALL>
{leading_thought}
</AGENT_THOUGHT_LEADING_TO_TOOL_CALL>
"""

def tool_invocation(tool, args):
    return f"""
<TOOL_INVOCATION>
- name: {tool.get('toolName')}
- description: {tool.get('description', '(no description provided)')}
- inputSchema: {safe_stringify(tool.get('inputSchema', {'type': 'object'}))}
- arguments: {safe_stringify(args)}
</TOOL_INVOCATION>
"""

def synthesis_guidance():
    return """
<SYNTHESIS_GUIDANCE>
- Action focus: Use the tool name and the provided arguments as the primary source of truth. Produce the best possible result that this tool would return for those arguments.
- Context use: Conversation history and agent thought may inform realism and details, but do not invent unrelated outputs. Stay aligned with the tool’s role and its inputs.
- Move forward: If inputs are insufficient to progress, include concise next-step suggestions in the document "summary" field (e.g., needed fields and one concrete next action).
- Scope discipline: Do not switch tools or simulate other systems. Only return what this tool would produce.
- Clarity and brevity: Prefer concise, well-structured content. Avoid narrative filler beyond the requested artifacts.
</SYNTHESIS_GUIDANCE>
"""

def terminal_note(tool):
    if tool.get('endsConversation'):
        outcome = tool.get('conversationEndStatus', 'neutral')
        return f"""
<TERMINAL_NOTE>
This tool is TERMINAL (endsConversation=true). Your output should help conclude the conversation. outcome="{outcome}".
</TERMINAL_NOTE>
"""
    return """
<TERMINAL_NOTE>
This tool is NOT terminal. Produce output to advance the conversation.
</TERMINAL_NOTE>
"""

def constraints():
    return """
<CONSTRAINTS>
- The conversation thread is the sole channel of exchange.
- Do NOT suggest portals, emails, fax, or separate submission flows.
- Encourage sharing documents via conversation attachments (by docId) when appropriate.
- Reveal only what the specific tool would plausibly know, even though you are omniscient.
- Text-only artifacts only: do NOT produce binary formats (e.g., PDF, images, Office documents).
</CONSTRAINTS>
"""

def output_formats():
    return """
<OUTPUT_FORMATS>
Return exactly one JSON code block with keys:
- reasoning: string
- output: { documents: Document[] }

Document shape:
{
  "docId"?: string,
  "name": string,
  "contentType": string,  // Allowed: application/json, text/plain, text/markdown, text/csv, application/xml, text/xml
  "contentString"?: string,  // for text-like types (e.g., text/plain, text/markdown)
  "contentJson"?: any,       // for application/json and other structured content
  "summary"?: string,
}
Rules:
- Exactly one of contentString or contentJson must be present per document (never both).
- Use contentJson only when contentType is application/json. For all other allowed types, use contentString.
- Do NOT claim to produce binary formats (e.g., PDF, images, Word/Excel); this Oracle outputs text-only artifacts.
- If a binary-like artifact is implied, instead provide a faithful text/markdown or JSON representation.
Return multiple documents by including multiple entries in output.documents in the desired order.

Example with two artifacts:
```
{
  "reasoning": "Brief rationale.",
  "output": {
    "documents": [
      {
        "docId": "contract_123",
        "name": "contract.json",
        "contentType": "application/json",
        "contentJson": { /* content here */ }
      },
      {
        "docId": "interfaces_456",
        "name": "interfaces.txt",
        "contentType": "text/plain",
        "contentString": "<content here>"
      }
    ]
  }
}
```
</OUTPUT_FORMATS>
"""

def conversation_history(history):
    if not history:
        return ""
    history_trunc = truncate_text(history, 20000, '... [history truncated]')
    return f"""
<CONVERSATION_HISTORY>
{history_trunc}
</CONVERSATION_HISTORY>
"""

def output_contract():
    return """
<OUTPUT_CONTRACT>
- Return exactly one framing JSON code block.
- The framing JSON MUST have keys: "reasoning" (string) and "output" (with a "documents" array as specified above).
- No extra text outside the code block.
</OUTPUT_CONTRACT>
"""

def result_format(tool):
    directors_note = tool.get('synthesisGuidance', '')
    return f"""
<RESULT_FORMAT>
Produce your response to the "{tool.get('toolName')}" tool call with the args shown above.

<DIRECTORS_NOTE_GUIDING_RESULTS>
{directors_note}
</DIRECTORS_NOTE_GUIDING_RESULTS>

</RESULT_FORMAT>
"""

def build_oracle_prompt(scenario, my_agent_id, tool, args, conversation_history, leading_thought):
    """
    Assembles the complete oracle prompt by calling all the component functions.
    """
    me = next((agent for agent in scenario.get('agents', []) if agent.get('agentId') == my_agent_id), scenario.get('agents', [{}])[0])
    
    prompt_parts = [
        system_role(),
        format_scenario_header(scenario),
        format_agent_profile(me),
        calling_agent_kb(me),
        format_scenario_knowledge(scenario),
        scenario_metadata(scenario),
        agent_thought_leading_to_tool_call(leading_thought),
        tool_invocation(tool, args),
        synthesis_guidance(),
        terminal_note(tool),
        constraints(),
        output_formats(),
        conversation_history(conversation_history),
        output_contract(),
        result_format(tool),
        "Follow SYNTHESIS_GUIDANCE and DIRECTORS_NOTE_GUIDING_RESULTS, and OUTPUT_CONTRACT exactly."
    ]
    
    return "\\n\\n".join(prompt_parts)
