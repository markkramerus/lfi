# Architectural Diagrams of Agentic Systems

This document contains Mermaid diagrams illustrating the different agentic architectures we've discussed.

## 1. The Banterop Architecture ("God View" Orchestrator)

This diagram shows the current architecture of the Banterop application, where the central `PairsService` has a "god view" of the entire conversation and all tool calls.

```mermaid
sequenceDiagram
    participant ClientA as Client as Party A
    box Orchestrator
        participant PairsService as PairsService
        participant OpenRouter as LLM (via OpenRouter)
        participant ClientSpecificTool as Client-Specific Tools
    end
    participant ClientB as Client as Party B

    ClientA->>PairsService: Initiate or Continue Conversation
    PairsService->>OpenRouter: Prompt + history + tool descriptions
    OpenRouter->>PairsService: LLM response (may include tool request)
    PairsService-->>ClientSpecificTool:  Execute LLM's tool request
    ClientSpecificTool-->>PairsService: Receive tool output
    PairsService-->>OpenRouter: Return tool output to LLM
    OpenRouter-->>PairsService: LLM output
    PairsService->>PairsService: Add LLM response to history
    PairsService->>ClientB: Prompt + history + tool descriptions
```


## 2. Secure, Client-Side Architecture

This diagram illustrates the secure, client-side architecture where each party is responsible for its own private data and tool calls. The central service acts only as a message broker.

```mermaid
sequenceDiagram
    box Party A's Private Environment
        participant ClientA as Party A's Client
        participant PrivateToolsA as Private MCP Server (Party A)
        participant PrivateLLM as Self-Hosted LLM (Party A)
    end
    participant PairsService as Message Broker
    participant CommercialLLM as Commercial LLM API (e.g., OpenRouter)
    box Party B's Private Environment
        participant ClientB as Party B's Client
    end

    note right of ClientA: Client A can use a private, self-hosted LLM for maximum security,<br/>or a commercial API for convenience.

    PairsService->>ClientA: 1. Notify: Your turn (with Party B's message)
    
    alt Using Self-Hosted LLM
        ClientA->>PrivateLLM: 2. Construct prompt and send to private LLM
        PrivateLLM->>ClientA: 3. LLM response (may include tool_call)
    else Using Commercial LLM
        ClientA->>CommercialLLM: 2. Construct prompt and send to commercial LLM
        CommercialLLM-->>ClientA: 3. LLM response (may include tool_call)
    end

    alt LLM requests a private tool
        ClientA->>PrivateToolsA: 4. Execute private tool
        PrivateToolsA-->>ClientA: 5. Tool result
        
        alt Using Self-Hosted LLM
            ClientA->>PrivateLLM: 6. Send tool result to LLM
            PrivateLLM-->>ClientA: 7. Final LLM response
        else Using Commercial LLM
            ClientA->>CommercialLLM: 6. Send tool result to LLM
            CommercialLLM-->>ClientA: 7. Final LLM response
        end
    end

    ClientA->>PairsService: 8. Send final, non-confidential message
    PairsService->>ClientB: 9. Forward message to Party B
```

## 3. Hybrid Architecture (Client-Side Private Tools, Centralized Public Tools)

This diagram shows a hybrid model. The central `PairsService` manages the main conversation and public tools, but each client is responsible for executing its own private tools. This is a practical compromise that balances security and convenience.

```mermaid
sequenceDiagram
    box Party A's Private Environment
        participant ClientA as Party A's Client
        participant PrivateToolsA as Private MCP Server (Party A)
    end
    participant PairsService as PairsService (Interlocutor)
    participant OpenRouter as OpenRouter API
    participant ClientSpecificTools as Public MCP Server
    box Party B's Private Environment
        participant ClientB as Party B's Client
    end

    PairsService->>ClientA: 1. Notify: Your turn (with Party B's message)
    ClientA->>OpenRouter: 2. Construct prompt with history + private & public tools
    OpenRouter-->>ClientA: 3. LLM response (may include tool_call)
    alt LLM requests a private tool
        ClientA->>PrivateToolsA: 4. Execute private tool
        PrivateToolsA-->>ClientA: 5. Tool result
        ClientA->>OpenRouter: 6. Send tool result to LLM
        OpenRouter-->>ClientA: 7. LLM generates response based on private data
    end
    alt LLM requests a public tool
        ClientA->>PairsService: 4. Request public tool execution
        PairsService->>ClientSpecificTools: 5. Execute public tool
        ClientSpecificTools-->>PairsService: 6. Tool result
        PairsService-->>ClientA: 7. Forward tool result
        ClientA->>OpenRouter: 8. Send tool result to LLM
        OpenRouter-->>ClientA: 9. LLM generates response based on public data
    end
    ClientA->>PairsService: 10. Send final, non-confidential message
    PairsService->>ClientB: 11. Forward message to Party B
```
