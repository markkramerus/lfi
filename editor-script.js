// Global state
let agents = [];
let scenarios = [];
let currentItemType = 'agent'; // 'agent' or 'scenario'
let currentAgentIndex = -1;
let currentScenarioIndex = -1;

// Track CodeMirror instances for cleanup
let codeMirrorInstances = {};

// CodeMirror helper functions
function destroyAllCodeMirrorInstances() {
    Object.keys(codeMirrorInstances).forEach(key => {
        if (codeMirrorInstances[key]) {
            codeMirrorInstances[key].toTextArea();
        }
    });
    codeMirrorInstances = {};
}

function createCodeMirrorEditor(elementId, initialValue, onChange, options = {}) {
    const textarea = document.getElementById(elementId);
    if (!textarea) return null;
    
    // Destroy existing instance if any
    if (codeMirrorInstances[elementId]) {
        codeMirrorInstances[elementId].toTextArea();
    }
    
    const defaultOptions = {
        mode: { name: "javascript", json: true },
        theme: "default",
        lineNumbers: true,
        matchBrackets: true,
        autoCloseBrackets: true,
        foldGutter: true,
        gutters: ["CodeMirror-linenumbers", "CodeMirror-foldgutter", "CodeMirror-lint-markers"],
        lint: true,
        tabSize: 2,
        indentWithTabs: false,
        lineWrapping: true
    };
    
    const cm = CodeMirror.fromTextArea(textarea, { ...defaultOptions, ...options });
    
    // Set initial value
    cm.setValue(initialValue);
    
    // Add change handler with debounce
    let changeTimeout;
    cm.on('change', () => {
        clearTimeout(changeTimeout);
        changeTimeout = setTimeout(() => {
            const value = cm.getValue();
            onChange(value, cm);
        }, 300);
    });
    
    // Store instance for later cleanup
    codeMirrorInstances[elementId] = cm;
    
    return cm;
}

// Initialize - load data from localStorage
function init() {
    loadAgentsFromStorage();
    loadScenariosFromStorage();
    renderAgentList();
    renderScenarioList();
}

// Storage functions
function loadAgentsFromStorage() {
    const stored = localStorage.getItem('agents');
    if (stored) {
        agents = JSON.parse(stored);
    }
}

function loadScenariosFromStorage() {
    const stored = localStorage.getItem('scenarios');
    if (stored) {
        scenarios = JSON.parse(stored);
    }
}

function saveAgentsToStorage() {
    localStorage.setItem('agents', JSON.stringify(agents));
}

function saveScenariosToStorage() {
    localStorage.setItem('scenarios', JSON.stringify(scenarios));
}

// Utility function
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Sidebar tab switching
function switchSidebarTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.sidebar-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`.sidebar-tab[data-tab="${tabName}"]`).classList.add('active');

    // Update panels
    document.querySelectorAll('.sidebar-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    document.getElementById(`${tabName}Panel`).classList.add('active');

    // Update current item type
    currentItemType = tabName;

    // Clear selection and show empty state
    if (tabName === 'agent' && currentAgentIndex >= 0) {
        renderEditorView();
        renderJSONView();
    } else if (tabName === 'scenario' && currentScenarioIndex >= 0) {
        renderEditorView();
        renderJSONView();
    } else {
        showEmptyState();
    }
}

function showEmptyState() {
    document.getElementById('editorView').innerHTML = '<div class="empty-state"><h2>No Item Selected</h2><p>Select an item from the sidebar or create a new one</p></div>';
    document.getElementById('jsonView').innerHTML = '<div class="empty-state"><h2>No Item Selected</h2><p>Select an item from the sidebar or create a new one</p></div>';
}

// Agent list rendering
function renderAgentList() {
    const listContainer = document.getElementById('agentList');
    if (!listContainer) return;
    
    listContainer.innerHTML = '';

    agents.forEach((agent, index) => {
        const item = document.createElement('div');
        item.className = 'item' + (currentItemType === 'agent' && index === currentAgentIndex ? ' active' : '');
        
        const textSpan = document.createElement('span');
        textSpan.className = 'item-text';
        textSpan.textContent = agent.agentName || 'Untitled Agent';
        textSpan.onclick = () => selectAgent(index);
        
        const menuBtn = document.createElement('button');
        menuBtn.className = 'item-menu-btn';
        menuBtn.textContent = '⋮';
        menuBtn.onclick = (e) => {
            e.stopPropagation();
            toggleItemMenu('agent', index, e);
        };
        
        const menu = document.createElement('div');
        menu.className = 'item-menu';
        menu.id = `agent-menu-${index}`;
        
        const deleteItem = document.createElement('div');
        deleteItem.className = 'item-menu-item danger';
        deleteItem.textContent = '🗑️ Delete Agent';
        deleteItem.onclick = (e) => {
            e.stopPropagation();
            closeAllMenus();
            deleteAgent(index);
        };
        
        menu.appendChild(deleteItem);
        item.appendChild(textSpan);
        item.appendChild(menuBtn);
        item.appendChild(menu);
        listContainer.appendChild(item);
    });
}

function selectAgent(index) {
    currentItemType = 'agent';
    currentAgentIndex = index;
    renderAgentList();
    renderScenarioList();
    renderEditorView();
    renderJSONView();
}

function deleteAgent(index) {
    const agent = agents[index];
    const agentName = agent.agentName || 'Untitled Agent';
    
    if (confirm(`Are you sure you want to delete "${agentName}"? This action cannot be undone.`)) {
        agents.splice(index, 1);
        
        if (currentAgentIndex === index) {
            currentAgentIndex = agents.length > 0 ? 0 : -1;
        } else if (currentAgentIndex > index) {
            currentAgentIndex--;
        }
        
        saveAgentsToStorage();
        renderAgentList();
        
        if (currentItemType === 'agent') {
            if (currentAgentIndex >= 0) {
                renderEditorView();
                renderJSONView();
            } else {
                showEmptyState();
            }
        }
    }
}

// Scenario list rendering
function renderScenarioList() {
    const listContainer = document.getElementById('scenarioList');
    if (!listContainer) return;
    
    listContainer.innerHTML = '';

    scenarios.forEach((scenario, index) => {
        const item = document.createElement('div');
        item.className = 'item' + (currentItemType === 'scenario' && index === currentScenarioIndex ? ' active' : '');
        
        const textSpan = document.createElement('span');
        textSpan.className = 'item-text';
        textSpan.textContent = scenario.title || 'Untitled Scenario';
        textSpan.onclick = () => selectScenario(index);
        
        const menuBtn = document.createElement('button');
        menuBtn.className = 'item-menu-btn';
        menuBtn.textContent = '⋮';
        menuBtn.onclick = (e) => {
            e.stopPropagation();
            toggleItemMenu('scenario', index, e);
        };
        
        const menu = document.createElement('div');
        menu.className = 'item-menu';
        menu.id = `scenario-menu-${index}`;
        
        const deleteItem = document.createElement('div');
        deleteItem.className = 'item-menu-item danger';
        deleteItem.textContent = '🗑️ Delete Scenario';
        deleteItem.onclick = (e) => {
            e.stopPropagation();
            closeAllMenus();
            deleteScenario(index);
        };
        
        menu.appendChild(deleteItem);
        item.appendChild(textSpan);
        item.appendChild(menuBtn);
        item.appendChild(menu);
        listContainer.appendChild(item);
    });
}

function selectScenario(index) {
    currentItemType = 'scenario';
    currentScenarioIndex = index;
    renderAgentList();
    renderScenarioList();
    renderEditorView();
    renderJSONView();
}

function deleteScenario(index) {
    const scenario = scenarios[index];
    const scenarioTitle = scenario.title || 'Untitled Scenario';
    
    if (confirm(`Are you sure you want to delete "${scenarioTitle}"? This action cannot be undone.`)) {
        scenarios.splice(index, 1);
        
        if (currentScenarioIndex === index) {
            currentScenarioIndex = scenarios.length > 0 ? 0 : -1;
        } else if (currentScenarioIndex > index) {
            currentScenarioIndex--;
        }
        
        saveScenariosToStorage();
        renderScenarioList();
        
        if (currentItemType === 'scenario') {
            if (currentScenarioIndex >= 0) {
                renderEditorView();
                renderJSONView();
            } else {
                showEmptyState();
            }
        }
    }
}

// Menu functions
function toggleItemMenu(type, index, event) {
    event.stopPropagation();
    const menu = document.getElementById(`${type}-menu-${index}`);
    const isCurrentlyShown = menu.classList.contains('show');
    
    closeAllMenus();
    
    if (!isCurrentlyShown) {
        menu.classList.add('show');
    }
}

function closeAllMenus() {
    document.querySelectorAll('.item-menu').forEach(menu => {
        menu.classList.remove('show');
    });
    closeAllToolMenus();
}

// Tool menu functions
function toggleToolMenu(index, event) {
    event.stopPropagation();
    const menu = document.getElementById(`tool-menu-${index}`);
    const isCurrentlyShown = menu.classList.contains('show');
    
    closeAllToolMenus();
    
    if (!isCurrentlyShown) {
        menu.classList.add('show');
    }
}

function closeAllToolMenus() {
    document.querySelectorAll('.tool-menu').forEach(menu => {
        menu.classList.remove('show');
    });
}

// Initialize on load
document.addEventListener('DOMContentLoaded', init);

// Close menus when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.item-menu') && !e.target.closest('.item-menu-btn')) {
        closeAllMenus();
    }
    if (!e.target.closest('.tool-menu') && !e.target.closest('.tool-menu-btn')) {
        closeAllToolMenus();
    }
});

// Main content tab switching
function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`.tab[data-tab="${tabName}"]`).classList.add('active');

    document.getElementById('editorView').classList.remove('active');
    document.getElementById('jsonView').classList.remove('active');

    if (tabName === 'editor') {
        document.getElementById('editorView').classList.add('active');
    } else {
        document.getElementById('jsonView').classList.add('active');
    }
}

// Main render dispatchers
function renderEditorView() {
    if (currentItemType === 'agent') {
        renderAgentEditorView();
    } else if (currentItemType === 'scenario') {
        renderScenarioEditorView();
    } else {
        showEmptyState();
    }
    updateRunScenarioButtonVisibility();
}

function renderJSONView() {
    if (currentItemType === 'agent') {
        renderAgentJSONView();
    } else if (currentItemType === 'scenario') {
        renderScenarioJSONView();
    } else {
        showEmptyState();
    }
}

// Agent Editor View
function renderAgentEditorView() {
    const view = document.getElementById('editorView');
    if (currentAgentIndex === -1) {
        view.innerHTML = '<div class="empty-state"><h2>No Agent Selected</h2><p>Select an agent from the sidebar or create a new one</p></div>';
        return;
    }

    const agent = agents[currentAgentIndex];
    
    view.innerHTML = `
        <input type="text" 
            class="item-name-title" 
            value="${escapeHtml(agent.agentName || '')}"
            placeholder="Agent Name"
            onchange="updateAgentField('agentName', this.value)">

        <div class="form-section">
            <div class="section-title">AGENT ID</div>
            <div class="form-group">
                <input type="text" 
                    class="form-input" 
                    value="${escapeHtml(agent.agentId || '')}"
                    placeholder="agent-id"
                    onchange="updateAgentField('agentId', this.value)">
            </div>
        </div>

        <div class="form-section">
            <div class="section-title">PRINCIPAL (Who the agent represents)</div>
            <div class="principal-fields">
                <div class="form-group">
                    <label class="form-label">Type</label>
                    <input type="text" 
                        class="form-input" 
                        value="${escapeHtml(agent.principal?.type || '')}"
                        placeholder="e.g., organization, individual"
                        onchange="updatePrincipalField('type', this.value)">
                </div>
                <div class="form-group">
                    <label class="form-label">Name</label>
                    <input type="text" 
                        class="form-input" 
                        value="${escapeHtml(agent.principal?.name || '')}"
                        placeholder="e.g., HealthFirst Insurance"
                        onchange="updatePrincipalField('name', this.value)">
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">Description</label>
                <input type="text" 
                    class="form-input" 
                    value="${escapeHtml(agent.principal?.description || '')}"
                    placeholder="Brief description of the principal"
                    onchange="updatePrincipalField('description', this.value)">
            </div>
        </div>

        <div class="form-section">
            <div class="section-title">SITUATION</div>
            <div class="form-group">
                <textarea 
                    class="form-textarea" 
                    placeholder="Describe the situation this agent operates in..."
                    onchange="updateAgentField('situation', this.value)">${escapeHtml(agent.situation || '')}</textarea>
            </div>
        </div>

        <div class="form-section">
            <div class="section-title">SYSTEM PROMPT</div>
            <div class="form-group">
                <textarea 
                    class="form-textarea" 
                    style="min-height: 200px;"
                    placeholder="System prompt that defines the agent's behavior..."
                    onchange="updateAgentField('systemPrompt', this.value)">${escapeHtml(agent.systemPrompt || '')}</textarea>
            </div>
        </div>

        <div class="tools-section" id="toolsSection">
            <div class="tools-header">
                <div class="section-title" style="margin: 0;">TOOLS</div>
                <button class="add-tool-btn" onclick="addTool()">+ ADD TOOL</button>
            </div>
            <div class="tools-list" id="toolsList">
                ${renderToolsList(agent.tools || [])}
            </div>
        </div>

        <div class="form-section">
            <div class="section-title">KNOWLEDGE BASE (JSON)</div>
            <div class="form-group json-field-container">
                <textarea id="knowledgeBaseEditor">${escapeHtml(JSON.stringify(agent.knowledgeBase || {}, null, 2))}</textarea>
            </div>
        </div>
    `;
    
    // Initialize CodeMirror for Knowledge Base
    setTimeout(() => {
        initializeKnowledgeBaseEditor(agent);
    }, 10);
}

function initializeKnowledgeBaseEditor(agent) {
    const jsonString = JSON.stringify(agent.knowledgeBase || {}, null, 2);
    createCodeMirrorEditor('knowledgeBaseEditor', jsonString, (value, cm) => {
        if (currentAgentIndex === -1) return;
        try {
            agents[currentAgentIndex].knowledgeBase = JSON.parse(value);
            // Update JSON view without re-rendering editor
            if (currentItemType === 'agent') {
                renderAgentJSONView();
            }
        } catch (error) {
            // Invalid JSON - just ignore for now, lint will show the error
        }
    }, {
        lineNumbers: true,
        lint: true
    });
}

function updateAgentField(field, value) {
    if (currentAgentIndex === -1) return;
    agents[currentAgentIndex][field] = value;
    renderAgentList();
    renderAgentJSONView();
}

function updatePrincipalField(field, value) {
    if (currentAgentIndex === -1) return;
    if (!agents[currentAgentIndex].principal) {
        agents[currentAgentIndex].principal = {};
    }
    agents[currentAgentIndex].principal[field] = value;
    renderAgentJSONView();
}

function updateKnowledgeBase(value) {
    if (currentAgentIndex === -1) return;
    try {
        agents[currentAgentIndex].knowledgeBase = JSON.parse(value);
        renderAgentJSONView();
    } catch (error) {
        alert('Invalid JSON in Knowledge Base: ' + error.message);
    }
}

// Agent Tools Functions
function renderToolsList(tools) {
    if (!tools || tools.length === 0) {
        return '<p style="color: #999; text-align: center; padding: 20px;">No tools defined</p>';
    }

    return tools.map((tool, index) => `
        <div class="tool-item" id="tool-${index}">
            <div class="tool-header" onclick="toggleTool(${index})">
                <div class="tool-header-left">
                    <span class="tool-expand-icon">▶</span>
                    <span class="tool-name-display">🔧 ${escapeHtml(tool.toolName || 'Untitled Tool')}</span>
                </div>
                <button class="tool-menu-btn" onclick="event.stopPropagation(); toggleToolMenu(${index}, event)">⋮</button>
                <div class="tool-menu" id="tool-menu-${index}">
                    <div class="tool-menu-item danger" onclick="event.stopPropagation(); closeAllToolMenus(); deleteTool(${index})">🗑️ Delete Tool</div>
                </div>
            </div>
            <div class="tool-content">
                <div class="tool-field">
                    <label class="tool-field-label">Tool Name</label>
                    <input type="text" 
                        class="form-input" 
                        value="${escapeHtml(tool.toolName || '')}"
                        placeholder="tool_name"
                        onchange="updateToolField(${index}, 'toolName', this.value)">
                </div>
                <div class="tool-field">
                    <label class="tool-field-label">Description</label>
                    <textarea 
                        class="form-textarea" 
                        style="min-height: 80px;"
                        placeholder="Description of what this tool does..."
                        onchange="updateToolField(${index}, 'description', this.value)">${escapeHtml(tool.description || '')}</textarea>
                </div>
                <div class="tool-field json-field-container">
                    <label class="tool-field-label">Input Schema (JSON)</label>
                    <textarea 
                        id="toolInputSchema-${index}"
                        class="tool-input-schema-textarea">${escapeHtml(JSON.stringify(tool.inputSchema || {}, null, 2))}</textarea>
                </div>
                <div class="tool-field">
                    <label class="tool-field-label">Synthesis Guidance</label>
                    <textarea 
                        class="form-textarea" 
                        style="min-height: 100px;"
                        placeholder="Guidance for synthesizing responses..."
                        onchange="updateToolField(${index}, 'synthesisGuidance', this.value)">${escapeHtml(tool.synthesisGuidance || '')}</textarea>
                </div>
                <div class="tool-field">
                    <label class="tool-checkbox-group">
                        <input type="checkbox" 
                            class="tool-checkbox"
                            ${tool.endsConversation ? 'checked' : ''}
                            onchange="updateToolField(${index}, 'endsConversation', this.checked)">
                        <span class="tool-checkbox-label">Ends Conversation?</span>
                    </label>
                </div>
                ${tool.endsConversation ? `
                    <div class="tool-field">
                        <label class="tool-field-label">Conversation End Status</label>
                        <input type="text" 
                            class="form-input" 
                            value="${escapeHtml(tool.conversationEndStatus || '')}"
                            placeholder="e.g., success, failure"
                            onchange="updateToolField(${index}, 'conversationEndStatus', this.value)">
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
}

function toggleTool(index) {
    const toolElement = document.getElementById(`tool-${index}`);
    if (toolElement) {
        const wasExpanded = toolElement.classList.contains('expanded');
        toolElement.classList.toggle('expanded');
        
        // Initialize CodeMirror for Input Schema when tool is expanded
        if (!wasExpanded) {
            initializeToolInputSchemaEditor(index);
        }
    }
}

function initializeToolInputSchemaEditor(index) {
    const editorId = `toolInputSchema-${index}`;
    
    // Check if already initialized
    if (codeMirrorInstances[editorId]) {
        // Refresh the editor in case it needs to adjust to container size
        codeMirrorInstances[editorId].refresh();
        return;
    }
    
    const tool = agents[currentAgentIndex]?.tools?.[index];
    if (!tool) return;
    
    const jsonString = JSON.stringify(tool.inputSchema || {}, null, 2);
    
    setTimeout(() => {
        createCodeMirrorEditor(editorId, jsonString, (value, cm) => {
            if (currentAgentIndex === -1) return;
            try {
                agents[currentAgentIndex].tools[index].inputSchema = JSON.parse(value);
                // Update JSON view without re-rendering editor
                if (currentItemType === 'agent') {
                    renderAgentJSONView();
                }
            } catch (error) {
                // Invalid JSON - lint will show the error
            }
        }, {
            lineNumbers: true,
            lint: true
        });
    }, 50);
}

function addTool() {
    if (currentAgentIndex === -1) return;
    
    const newTool = {
        toolName: "new_tool",
        description: "",
        inputSchema: {
            type: "object",
            properties: {}
        },
        synthesisGuidance: ""
    };
    
    if (!agents[currentAgentIndex].tools) {
        agents[currentAgentIndex].tools = [];
    }
    agents[currentAgentIndex].tools.push(newTool);
    renderAgentEditorView();
    renderAgentJSONView();
    
    setTimeout(() => {
        const newIndex = agents[currentAgentIndex].tools.length - 1;
        toggleTool(newIndex);
    }, 10);
}

function deleteTool(index) {
    if (currentAgentIndex === -1) return;
    if (confirm('Are you sure you want to delete this tool?')) {
        agents[currentAgentIndex].tools.splice(index, 1);
        renderAgentEditorView();
        renderAgentJSONView();
    }
}

function updateToolField(index, field, value) {
    if (currentAgentIndex === -1) return;
    agents[currentAgentIndex].tools[index][field] = value;
    
    if (field === 'toolName' || field === 'endsConversation') {
        renderAgentEditorView();
    }
    renderAgentJSONView();
}

function updateToolInputSchema(index, value) {
    if (currentAgentIndex === -1) return;
    try {
        agents[currentAgentIndex].tools[index].inputSchema = JSON.parse(value);
        renderAgentJSONView();
    } catch (error) {
        alert('Invalid JSON in Input Schema: ' + error.message);
    }
}

// Scenario Editor View
function renderScenarioEditorView() {
    const view = document.getElementById('editorView');
    if (currentScenarioIndex === -1) {
        view.innerHTML = '<div class="empty-state"><h2>No Scenario Selected</h2><p>Select a scenario from the sidebar or create a new one</p></div>';
        return;
    }

    const scenario = scenarios[currentScenarioIndex];
    
    view.innerHTML = `
        <input type="text" 
            class="item-name-title" 
            value="${escapeHtml(scenario.title || '')}"
            placeholder="Scenario Title"
            onchange="updateScenarioField('title', this.value)">

        <div class="form-section">
            <div class="section-title">SCENARIO ID</div>
            <div class="form-group">
                <input type="text" 
                    class="form-input" 
                    value="${escapeHtml(scenario.id || '')}"
                    placeholder="scenario-id"
                    onchange="updateScenarioField('id', this.value)">
            </div>
        </div>

        <div class="form-section">
            <div class="section-title">DESCRIPTION</div>
            <div class="form-group">
                <textarea 
                    class="form-textarea" 
                    placeholder="Brief description of the scenario..."
                    onchange="updateScenarioField('description', this.value)">${escapeHtml(scenario.description || '')}</textarea>
            </div>
        </div>

        <div class="form-section">
            <div class="section-title">BACKGROUND</div>
            <div class="form-group">
                <textarea 
                    class="form-textarea" 
                    placeholder="Background information for the scenario..."
                    onchange="updateScenarioField('background', this.value)">${escapeHtml(scenario.background || '')}</textarea>
            </div>
        </div>

        <div class="form-section">
            <div class="section-title">AGENT REFERENCES</div>
            <div class="agent-refs-fields">
                <div class="form-group">
                    <label class="form-label">Initiating Agent ID</label>
                    <input type="text" 
                        class="form-input" 
                        value="${escapeHtml(scenario.agents?.initiating_agent_id || '')}"
                        placeholder="e.g., prior_auth_patient_agent"
                        onchange="updateAgentRefField('initiating_agent_id', this.value)">
                </div>
                <div class="form-group">
                    <label class="form-label">Responding Agent ID</label>
                    <input type="text" 
                        class="form-input" 
                        value="${escapeHtml(scenario.agents?.responding_agent_id || '')}"
                        placeholder="e.g., prior_auth_insurance_agent"
                        onchange="updateAgentRefField('responding_agent_id', this.value)">
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">Initiating Message</label>
                <textarea 
                    class="form-textarea" 
                    style="min-height: 100px;"
                    placeholder="Enter the initiating message..."
                    onchange="updateAgentRefField('messageToUseWhenInitiatingConversation', this.value)">${escapeHtml(scenario.agents?.messageToUseWhenInitiatingConversation || '')}</textarea>
            </div>
        </div>

        <div class="form-section" hidden>
            <div class="section-title">KNOWLEDGE BASE (JSON)</div>
            <div class="form-group">
                <textarea 
                    class="form-textarea" 
                    style="min-height: 300px;"
                    placeholder='{}'
                    onchange="updateScenarioKnowledgeBase(this.value)">${escapeHtml(JSON.stringify(scenario.knowledgeBase || {}, null, 2))}</textarea>
            </div>
        </div>
    `;
}

function updateScenarioField(field, value) {
    if (currentScenarioIndex === -1) return;
    scenarios[currentScenarioIndex][field] = value;
    renderScenarioList();
    renderScenarioJSONView();
}

function updateAgentRefField(field, value) {
    if (currentScenarioIndex === -1) return;
    if (!scenarios[currentScenarioIndex].agents) {
        scenarios[currentScenarioIndex].agents = {};
    }
    scenarios[currentScenarioIndex].agents[field] = value;
    renderScenarioJSONView();
}

function updateScenarioKnowledgeBase(value) {
    if (currentScenarioIndex === -1) return;
    try {
        scenarios[currentScenarioIndex].knowledgeBase = JSON.parse(value);
        renderScenarioJSONView();
    } catch (error) {
        alert('Invalid JSON in Knowledge Base: ' + error.message);
    }
}

// JSON View Functions
function renderAgentJSONView() {
    // Destroy existing CodeMirror instances in JSON view
    if (codeMirrorInstances['jsonTextarea']) {
        codeMirrorInstances['jsonTextarea'].toTextArea();
        delete codeMirrorInstances['jsonTextarea'];
    }
    
    const view = document.getElementById('jsonView');
    if (currentAgentIndex === -1) {
        view.innerHTML = '<div class="empty-state"><h2>No Agent Selected</h2><p>Select an agent from the sidebar or create a new one</p></div>';
        return;
    }

    const agent = agents[currentAgentIndex];
    const jsonString = JSON.stringify(agent, null, 2);

    view.innerHTML = `
        <div class="json-editor">
            <div class="json-status" id="jsonStatus">
                <span class="json-status-indicator valid">✓ Valid JSON</span>
            </div>
            <textarea id="jsonTextarea">${escapeHtml(jsonString)}</textarea>
        </div>
    `;

    // Initialize CodeMirror for the JSON textarea
    setTimeout(() => {
        createCodeMirrorEditor('jsonTextarea', jsonString, (value, cm) => {
            updateAgentFromJSON(value);
        });
    }, 10);
}

function updateAgentFromJSON(value) {
    if (currentAgentIndex === -1) return;
    
    const statusDiv = document.getElementById('jsonStatus');
    
    try {
        const updatedAgent = JSON.parse(value);
        agents[currentAgentIndex] = updatedAgent;
        if (statusDiv) {
            statusDiv.innerHTML = '<span class="json-status-indicator valid">✓ Valid JSON</span>';
        }
        renderAgentList();
        // Don't re-render editor view to avoid losing focus
    } catch (error) {
        if (statusDiv) {
            statusDiv.innerHTML = `<span class="json-status-indicator invalid">✗ Invalid JSON: ${escapeHtml(error.message)}</span>`;
        }
    }
}

function renderScenarioJSONView() {
    // Destroy existing CodeMirror instances in JSON view
    if (codeMirrorInstances['jsonTextarea']) {
        codeMirrorInstances['jsonTextarea'].toTextArea();
        delete codeMirrorInstances['jsonTextarea'];
    }
    
    const view = document.getElementById('jsonView');
    if (currentScenarioIndex === -1) {
        view.innerHTML = '<div class="empty-state"><h2>No Scenario Selected</h2><p>Select a scenario from the sidebar or create a new one</p></div>';
        return;
    }

    const scenario = scenarios[currentScenarioIndex];
    const jsonString = JSON.stringify(scenario, null, 2);

    view.innerHTML = `
        <div class="json-editor">
            <div class="json-status" id="jsonStatus">
                <span class="json-status-indicator valid">✓ Valid JSON</span>
            </div>
            <textarea id="jsonTextarea">${escapeHtml(jsonString)}</textarea>
        </div>
    `;

    // Initialize CodeMirror for the JSON textarea
    setTimeout(() => {
        createCodeMirrorEditor('jsonTextarea', jsonString, (value, cm) => {
            updateScenarioFromJSON(value);
        });
    }, 10);
}

function updateScenarioFromJSON(value) {
    if (currentScenarioIndex === -1) return;
    
    const statusDiv = document.getElementById('jsonStatus');
    
    try {
        const updatedScenario = JSON.parse(value);
        scenarios[currentScenarioIndex] = updatedScenario;
        if (statusDiv) {
            statusDiv.innerHTML = '<span class="json-status-indicator valid">✓ Valid JSON</span>';
        }
        renderScenarioList();
        // Don't re-render editor view to avoid losing focus
    } catch (error) {
        if (statusDiv) {
            statusDiv.innerHTML = `<span class="json-status-indicator invalid">✗ Invalid JSON: ${escapeHtml(error.message)}</span>`;
        }
    }
}

// Create/Import/Export/Save Functions
function createNewAgent() {
    const newAgent = {
        type: "agent",
        agentName: "New Agent",
        agentId: "new-agent-" + Date.now(),
        principal: { type: "", name: "", description: "" },
        situation: "",
        systemPrompt: "",
        tools: [],
        knowledgeBase: {}
    };
    agents.push(newAgent);
    currentItemType = 'agent';
    currentAgentIndex = agents.length - 1;
    
    // Switch to agent tab if not already
    switchSidebarTab('agent');
    renderAgentList();
    renderEditorView();
    renderJSONView();
}

function createNewScenario() {
    const newScenario = {
        type: "scenario",
        title: "New Scenario",
        id: "new-scenario-" + Date.now(),
        description: "",
        background: "",
        agents: {
            initiating_agent_id: "",
            responding_agent_id: ""
        },
        knowledgeBase: {}
    };
    scenarios.push(newScenario);
    currentItemType = 'scenario';
    currentScenarioIndex = scenarios.length - 1;
    
    // Switch to scenario tab if not already
    switchSidebarTab('scenario');
    renderScenarioList();
    renderEditorView();
    renderJSONView();
}

function importJSON() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
        const file = e.target.files[0];
        const reader = new FileReader();
        reader.onload = (event) => {
            try {
                const data = JSON.parse(event.target.result);
                
                if (data.type === 'agent') {
                    // Check for duplicate agentId
                    const existingAgent = agents.find(a => a.agentId === data.agentId);
                    if (existingAgent) {
                        alert(`An agent with ID "${data.agentId}" already exists. Cannot import duplicate agent.`);
                        return;
                    }
                    
                    agents.push(data);
                    currentItemType = 'agent';
                    currentAgentIndex = agents.length - 1;
                    switchSidebarTab('agent');
                    renderAgentList();
                    renderEditorView();
                    renderJSONView();
                } else if (data.type === 'scenario') {
                    // Check for duplicate scenario id
                    const existingScenario = scenarios.find(s => s.id === data.id);
                    if (existingScenario) {
                        alert(`A scenario with ID "${data.id}" already exists. Cannot import duplicate scenario.`);
                        return;
                    }
                    
                    scenarios.push(data);
                    currentItemType = 'scenario';
                    currentScenarioIndex = scenarios.length - 1;
                    switchSidebarTab('scenario');
                    renderScenarioList();
                    renderEditorView();
                    renderJSONView();
                } else {
                    alert('Invalid JSON: missing or unknown "type" field. Expected "agent" or "scenario".');
                }
            } catch (error) {
                alert('Error parsing JSON: ' + error.message);
            }
        };
        reader.readAsText(file);
    };
    input.click();
}

function saveItem() {
    if (currentItemType === 'agent') {
        if (currentAgentIndex === -1) return;
        saveAgentsToStorage();
        alert('Agent saved successfully!');
    } else if (currentItemType === 'scenario') {
        if (currentScenarioIndex === -1) return;
        saveScenariosToStorage();
        alert('Scenario saved successfully!');
    }
}

function exportItem() {
    let data, filename;
    
    if (currentItemType === 'agent') {
        if (currentAgentIndex === -1) return;
        data = agents[currentAgentIndex];
        filename = (data.agentId || 'agent') + '.json';
    } else if (currentItemType === 'scenario') {
        if (currentScenarioIndex === -1) return;
        data = scenarios[currentScenarioIndex];
        filename = (data.id || 'scenario') + '.json';
    } else {
        return;
    }
    
    const dataStr = JSON.stringify(data, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
}

// Update the visibility of the Run Scenario button
function updateRunScenarioButtonVisibility() {
    const btn = document.getElementById('runScenarioBtn');
    if (btn) {
        if (currentItemType === 'scenario' && currentScenarioIndex >= 0) {
            btn.style.display = 'flex';
        } else {
            btn.style.display = 'none';
        }
    }
}

// Run Scenario function
async function runScenario() {
    if (currentItemType !== 'scenario' || currentScenarioIndex === -1) {
        alert('Please select a scenario first.');
        return;
    }
    
    const scenario = scenarios[currentScenarioIndex];
    
    // Get the agent IDs from the scenario
    const initiatingAgentId = scenario.agents?.initiating_agent_id;
    const respondingAgentId = scenario.agents?.responding_agent_id;
    
    if (!initiatingAgentId || !respondingAgentId) {
        alert('Scenario must have both initiating_agent_id and responding_agent_id defined in the agents section.');
        return;
    }
    
    // Find the agents by their IDs
    const initiatingAgent = agents.find(a => a.agentId === initiatingAgentId);
    const respondingAgent = agents.find(a => a.agentId === respondingAgentId);
    
    // Validate both agents exist
    const missingAgents = [];
    if (!initiatingAgent) {
        missingAgents.push(`Initiating agent "${initiatingAgentId}"`);
    }
    if (!respondingAgent) {
        missingAgents.push(`Responding agent "${respondingAgentId}"`);
    }
    
    if (missingAgents.length > 0) {
        alert(`Cannot run scenario. The following agents are not found in the editor:\n\n${missingAgents.join('\n')}\n\nPlease import or create these agents first.`);
        return;
    }
    
    // Add the initiating message to the initiating agent if it's defined in the scenario
    const initiatingAgentWithMessage = { ...initiatingAgent };
    if (scenario.agents?.messageToUseWhenInitiatingConversation) {
        initiatingAgentWithMessage.messageToUseWhenInitiatingConversation = scenario.agents.messageToUseWhenInitiatingConversation;
    }
    
    // Build the combined JSON structure
    const combinedData = {
        metadata: {
            id: scenario.id,
            title: scenario.title,
            description: scenario.description,
            background: scenario.background,
            tags: scenario.tags || []
        },
        scenario: {},
        knowledgeBase: scenario.knowledgeBase || {},
        agents: [
            initiatingAgentWithMessage,
            respondingAgent
        ]
    };
    
    console.log('Combined scenario data:', combinedData);
    
    // Send to the backend
    try {
        const response = await fetch('http://127.0.0.1:5002/run-scenario', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(combinedData)
        });
        
        if (response.ok) {
            const result = await response.json();
            alert(`Scenario "${scenario.title}" is now running!\n\nA browser window should open with the chat interface.`);
        } else {
            const error = await response.text();
            alert(`Failed to run scenario: ${error}`);
        }
    } catch (error) {
        alert(`Failed to connect to the scenario runner server.\n\nMake sure the server is running with:\npython run_scenario.py --server\n\nError: ${error.message}`);
    }
}
