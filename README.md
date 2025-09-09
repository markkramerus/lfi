# Agent Conversation System

This project demonstrates how to build a multi-agent conversational system using the Agent Squad framework. It includes a dynamic agent factory that creates and configures agents from scenario files, and it showcases how to implement and use tools to give agents advanced capabilities.

## How Tool Use is Implemented

Tool use in the Agent Squad framework is a multi-step process that allows a Large Language Model (LLM) to decide *which* tool to use and with *what* inputs, while the framework handles the actual execution.

Tools are defined using the `AgentTool` class, which specifies the tool's name, description, input schema, and the function to be executed.

```python
# From agent_factory.py
agent_tool = AgentTool(
    name="search_ehr_clinical_notes",
    description="Search EHR for patient's clinical notes...",
    properties={ "dateRange": { "type": "string" }, ... },
    required=["searchTerms"],
    func=placeholder_tool_func  # The actual Python function to run
)
```

-   **`name` & `description`:** This is what the LLM sees. It uses the `description` to determine which tool is best suited for a given task.
-   **`properties` & `required`:** This is the input schema that the LLM uses to understand what parameters to provide.
-   **`func`:** This is the actual Python function that gets executed when the tool is called.


## Implementing MCP Server Tools

If a tool is implemented on an MCP server, the registration process is slightly different. Instead of providing a local Python function, you provide the details of the MCP server.

### 1. Scenario File Configuration

The scenario file would be updated to include MCP-specific information:

```json
{
  "toolName": "lookup_medical_policy",
  "description": "Retrieve specific medical policy criteria...",
  "toolType": "mcp",
  "mcpServer": "healthfirst-policy-server.mcp",
  "mcpToolName": "get_policy_by_name",
  "inputSchema": { ... }
}
```

### 2. Agent Factory Logic

The agent factory would then be updated to recognize the `toolType` and create an MCP-specific tool object:

```python
# Conceptual example
if tool_config.get('toolType') == 'mcp':
    agent_tool = MCPTool(
        name=tool_config.get('toolName'),
        description=tool_config.get('description'),
        mcp_server=tool_config.get('mcpServer'),
        mcp_tool_name=tool_config.get('mcpToolName'),
        input_schema=tool_config.get('inputSchema')
    )
```

### 3. MCP Execution Flow

The execution flow is similar, but instead of calling a local function, the framework makes a network request to the specified MCP server to execute the tool. The server's response is then passed back to the LLM, just as with a local tool.
