// Team creator page logic (loaded via {% static %} from team_creator.html).
// LLM profiles arrive via json_script island #team-creator-profiles (not inline JS).
let teamMemberCount = 0;
let generatedTeamCode = '';
let teamValidationResult = null;

function getTeamProfiles() {
    const el = document.getElementById('team-creator-profiles');
    if (!el) return ['default'];
    try {
        const parsed = JSON.parse(el.textContent);
        return Array.isArray(parsed) && parsed.length ? parsed : ['default'];
    } catch (e) {
        return ['default'];
    }
}

function profileOptionsHtml() {
    return getTeamProfiles().map((profile) => {
        const safe = escapeHtml(String(profile));
        return `<option value="${safe}">${safe}</option>`;
    }).join('');
}

function addTeamMember() {
    teamMemberCount++;
    const container = document.getElementById('teamMembers');

    const memberHtml = `
        <div class="border rounded p-3 mb-3" id="member-${teamMemberCount}">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h6>Team Member ${teamMemberCount}</h6>
                <button type="button" class="btn btn-sm btn-outline-danger" data-action="remove-member" data-member-id="${teamMemberCount}">
                    ✕ Remove
                </button>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <label class="form-label" for="member_name_${teamMemberCount}">Agent Name *</label>
                    <input type="text" class="form-control member-name" id="member_name_${teamMemberCount}" name="member_name_${teamMemberCount}" required>
                </div>
                <div class="col-md-6">
                    <label class="form-label" for="member_role_${teamMemberCount}">Role/Specialization</label>
                    <input type="text" class="form-control member-role" id="member_role_${teamMemberCount}" name="member_role_${teamMemberCount}"
                           placeholder="e.g., Writer, Researcher, Analyst">
                </div>
            </div>

            <div class="mt-2">
                <label class="form-label" for="member_description_${teamMemberCount}">Description</label>
                <textarea class="form-control member-description" id="member_description_${teamMemberCount}" name="member_description_${teamMemberCount}" rows="2"
                          placeholder="What does this team member do?"></textarea>
            </div>

            <div class="mt-2">
                <label class="form-label" for="member_instructions_${teamMemberCount}">System Prompt</label>
                <textarea class="form-control member-instructions" id="member_instructions_${teamMemberCount}" name="member_instructions_${teamMemberCount}" rows="3"
                          placeholder="System prompt for this bot (role, behavior, constraints)"></textarea>
            </div>

            <div class="row mt-2">
                <div class="col-md-6">
                    <label class="form-label" for="member_model_${teamMemberCount}">Model Profile</label>
                    <select class="form-select member-model" id="member_model_${teamMemberCount}" name="member_model_${teamMemberCount}">
                        ${profileOptionsHtml()}
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label" for="member_tools_${teamMemberCount}">Tools/Functions (comma-separated)</label>
                    <input type="text" class="form-control member-tools" id="member_tools_${teamMemberCount}" name="member_tools_${teamMemberCount}"
                           placeholder="e.g., read_file, write_file, list_files, execute_shell_command">
                </div>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', memberHtml);
}

function removeMember(memberId) {
    const memberElement = document.getElementById(`member-${memberId}`);
    if (memberElement) {
        memberElement.remove();
    }
}

function generateTeamCode() {
    const teamData = collectTeamData();
    if (!teamData) {
        return;
    }
    showTeamMessage('Building client-side preview draft (not the saved blueprint)...', 'info');
    generateSimpleTeamCode(teamData);
}

function generateSimpleTeamCode(teamData) {
    // Client-side preview draft only — Save uses the server renderer.
    const className = sanitizeClassName(teamData.name) + 'TeamBlueprint';
    const blueprintId = teamData.name.toLowerCase().replace(/\s+/g, '-');

    const agentInitCode = teamData.agents.map(agent => {
        const agentVar = agent.name.toLowerCase().replace(/\s+/g, '_');
        return `        # Initialize ${agent.name}
        ${agentVar}_config = AgentConfig(
            name="${agent.name}",
            description="${agent.description}",
            instructions="${agent.system_prompt}",
            model_profile="${agent.model_profile}"
        )
        self.agents["${agent.name}"] = self.create_agent_from_config(${agentVar}_config)`;
    }).join('\n\n');

    const memberDescriptions = teamData.agents.map(agent =>
        `- ${agent.name}: ${agent.description}`
    ).join('\n');

    const teamCode = `"""
${teamData.description}
"""
from collections.abc import AsyncGenerator
from typing import Any
from swarm.core.blueprint_base import BlueprintBase
from swarm.core.agent_config import AgentConfig

class ${className}(BlueprintBase):
    """
    ${teamData.description}
    """

    metadata = {
        "name": "${teamData.name}",
        "description": "${teamData.description}",
        "version": "1.0.0",
        "author": "User Generated",
        "tags": ${JSON.stringify(teamData.tags)},
        "team_structure": {
            "coordinator": "${teamData.coordinator_name}",
            "agents": ${JSON.stringify(teamData.agents.map(a => a.name))}
        }
    }

    def __init__(self, blueprint_id: str = None, config_path: str = None, **kwargs):
        super().__init__(blueprint_id or "${blueprintId}", config_path=config_path, **kwargs)
        self.agents = {}

    async def run(self, messages: list[dict[str, Any]], **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
        """
        Main execution method for the ${teamData.name} team.
        """
        user_message = messages[-1].get("content", "") if messages else ""

        # Initialize team agents
        await self._initialize_agents()

        # Simple coordination: delegate to first available agent
        # In a real implementation, add sophisticated coordination logic
        primary_agent = "${teamData.agents[0].name}"

        if primary_agent in self.agents:
            async for result in self.agents[primary_agent].run(messages):
                yield result
        else:
            yield {
                "messages": [{
                    "role": "assistant",
                    "content": f"Error: Agent {primary_agent} not found in team."
                }]
            }

    async def _initialize_agents(self):
        """Initialize all team agents"""
${agentInitCode}

    async def _coordinate_task(self, user_message: str) -> dict:
        """Coordinator decides task delegation"""
        # Simple coordination logic - extend this for sophisticated routing
        return {
            "primary_agent": "${teamData.agents[0].name}",
            "supporting_agents": [],
            "task_breakdown": user_message
        }
`;

    generatedTeamCode = teamCode;
    displayTeamCode(teamCode);

    // Simple validation (just check syntax)
    try {
        // Basic validation - in real implementation, call backend
        const validation = {
            valid: true,
            errors: [],
            warnings: ['Preview draft only — Save Swarm writes the real server-rendered blueprint'],
            syntax_valid: true,
            structure_valid: true,
            lint_clean: true
        };

        teamValidationResult = validation;
        displayTeamValidation(validation);
        document.getElementById('validateTeamBtn').disabled = false;
        document.getElementById('saveTeamBtn').disabled = false;
        showTeamMessage('Preview draft ready. Save Swarm to write the real blueprint.', 'success');

    } catch (error) {
        showTeamMessage('Preview draft error: ' + error.message, 'danger');
    }
}

function displayTeamCode(code) {
    const container = document.getElementById('teamCodeContainer');
    container.innerHTML = `<pre><code class="language-python">${escapeHtml(code)}</code></pre>`;
}

function displayTeamValidation(validation) {
    const container = document.getElementById('teamValidationContent');
    const resultsDiv = document.getElementById('teamValidationResults');

    let html = '';

    if (validation.valid) {
        html += '<div class="alert alert-info">ℹ️ Preview draft sketch ready (not server-validated).</div>';
    } else {
        html += '<div class="alert alert-danger">❌ Preview draft has issues</div>';
    }

    if (validation.warnings.length > 0) {
        html += '<div class="mt-3"><strong>Notes:</strong><ul class="text-info">';
        validation.warnings.forEach(warning => {
            html += `<li>${escapeHtml(warning)}</li>`;
        });
        html += '</ul></div>';
    }

    container.innerHTML = html;
    resultsDiv.style.display = 'block';
}

function validateTeamCode() {
    showTeamMessage(
        'Validate is not available: no server-side team validation is wired yet. Review the code before saving.',
        'warning'
    );
}

function saveTeam() {
    const teamData = collectTeamData();
    if (!teamData) {
        return;
    }
    showTeamMessage('Saving swarm blueprint...', 'info');
    fetch('/team-creator/save/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify(teamData)
    }).then(async (resp) => {
        const payload = await resp.json();
        if (!resp.ok || !payload.success) {
            const msg = payload.error || 'Save failed.';
            showTeamMessage(msg, 'danger');
            return;
        }
        showTeamMessage(payload.message || `Swarm "${teamData.name}" saved to ${payload.path}`, 'success');
        if (typeof payload.code === 'string' && payload.code.length) {
            generatedTeamCode = payload.code;
            displayTeamCode(payload.code);
        } else {
            showTeamMessage('Save succeeded but response omitted code; refresh or re-save to load the blueprint.', 'warning');
        }
    }).catch((err) => {
        showTeamMessage(`Save failed: ${err}`, 'danger');
    });
}

function clearTeamForm() {
    document.getElementById('teamForm').reset();
    document.getElementById('teamMembers').innerHTML = '';
    document.getElementById('teamCodeContainer').innerHTML = `
        <div class="text-muted text-center p-4">
            <i class="fas fa-users fa-3x mb-3"></i>
            <p>Configure your swarm and click "Preview Draft" for a client-side sketch, or "Save Swarm" for the real blueprint.</p>
        </div>
    `;
    document.getElementById('teamValidationResults').style.display = 'none';
    teamMemberCount = 0;
    generatedTeamCode = '';
    teamValidationResult = null;
    clearTeamMessages();
}

function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

function showTeamMessage(message, type) {
    const container = document.getElementById('teamStatusMessages');
    const alertClass = `alert-${type}`;
    container.innerHTML = `<div class="alert ${alertClass} alert-dismissible fade show" role="alert">
        ${escapeHtml(message)}
        <button type="button" class="btn-close" aria-label="Close" data-bs-dismiss="alert"></button>
    </div>`;
}

function clearTeamMessages() {
    document.getElementById('teamStatusMessages').innerHTML = '';
}

function sanitizeClassName(name) {
    return name.replace(/[^a-zA-Z0-9\s]/g, '').split(' ').map(word =>
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join('');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function collectTeamData() {
    const teamName = document.getElementById('teamName').value.trim();
    const teamDescription = document.getElementById('teamDescription').value.trim();
    const coordinatorName = document.getElementById('coordinatorName').value.trim();

    if (!teamName || !teamDescription) {
        showTeamMessage('Please fill in swarm name and description', 'danger');
        return null;
    }

    const members = [];
    const memberElements = document.querySelectorAll('[id^="member-"]');
    memberElements.forEach(element => {
        const name = element.querySelector('.member-name').value.trim();
        const role = element.querySelector('.member-role').value.trim();
        const description = element.querySelector('.member-description').value.trim();
        const systemPrompt = element.querySelector('.member-instructions').value.trim();
        const model = element.querySelector('.member-model').value.trim();
        const tools = element.querySelector('.member-tools').value.trim();

        if (name) {
            members.push({
                name: name,
                role: role || name,
                description: description || `${name} bot`,
                system_prompt: systemPrompt || `You are ${name}, a member of the ${teamName} swarm.`,
                model_profile: model || 'default',
                tools: tools ? tools.split(',').map(t => t.trim()).filter(Boolean) : []
            });
        }
    });

    if (members.length < 2) {
        showTeamMessage('Swarm needs at least 2 bots. Add more bots.', 'warning');
        return null;
    }

    return {
        name: teamName,
        description: teamDescription,
        coordinator_name: coordinatorName,
        agents: members
    };
}

const TEAM_CREATOR_ACTIONS = {
    'add-member': addTeamMember,
    'generate-team': generateTeamCode,
    'clear-team': clearTeamForm,
    'validate-team': validateTeamCode,
    'save-team': saveTeam,
};

document.getElementById('teamCreator')?.addEventListener('click', (event) => {
    const btn = event.target.closest('[data-action]');
    if (!btn || !event.currentTarget.contains(btn)) return;
    const action = btn.getAttribute('data-action');
    if (action === 'remove-member') {
        removeMember(btn.getAttribute('data-member-id'));
        return;
    }
    const handler = TEAM_CREATOR_ACTIONS[action];
    if (typeof handler === 'function') handler();
});

// Initialize with one team member
document.addEventListener('DOMContentLoaded', function() {
    addTeamMember();
    addTeamMember();
});
