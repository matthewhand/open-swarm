// My Blueprints page logic (loaded via {% static %} from my_blueprints.html).
document.addEventListener('DOMContentLoaded', function() {
    // Handle run blueprint buttons
    document.querySelectorAll('.btn-run-blueprint').forEach(button => {
        button.addEventListener('click', function() {
            const blueprintId = this.dataset.blueprintId;
            const blueprintName = this.dataset.blueprintName;
            const blueprintCode = this.dataset.blueprintCode;
            
            openBlueprintRunner(blueprintId, blueprintName, blueprintCode);
        });
    });

    document.querySelectorAll('.btn-bp-preview').forEach((button) => {
        button.addEventListener('click', () => previewBlueprint(button.dataset.blueprintId));
    });
    document.querySelectorAll('.btn-bp-remove').forEach((button) => {
        button.addEventListener('click', () => removeBlueprint(button.dataset.blueprintId, button.dataset.blueprintName));
    });
    document.querySelectorAll('.btn-bp-edit').forEach((button) => {
        button.addEventListener('click', () => editBlueprint(button.dataset.blueprintId));
    });
    document.querySelectorAll('.btn-bp-delete').forEach((button) => {
        button.addEventListener('click', () => deleteBlueprint(button.dataset.blueprintId, button.dataset.blueprintName));
    });

    // Handle run button in modal
    document.getElementById('runBlueprintBtn').addEventListener('click', function() {
        runBlueprint();
    });

    // Handle clear output button
    document.getElementById('clearOutputBtn').addEventListener('click', function() {
        document.getElementById('blueprintOutput').innerHTML = `
            <div class="text-muted text-center py-5">
                <i class="fas fa-terminal fa-2x mb-3"></i>
                <p>Output will appear here when you run the blueprint...</p>
            </div>
        `;
    });

    // Handle save blueprint button
    document.getElementById('saveBlueprintBtn').addEventListener('click', function() {
        const blueprintId = document.getElementById('edit_blueprint_id').value;
        const data = {
            name: document.getElementById('edit_name').value,
            category: document.getElementById('edit_category').value,
            description: document.getElementById('edit_description').value,
            tags: document.getElementById('edit_tags').value.split(',').map(tag => tag.trim()).filter(tag => tag),
            requirements: document.getElementById('edit_requirements').value,
            code: document.getElementById('edit_code').value
        };

        fetch(`/v1/blueprints/custom/${blueprintId}/`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (response.ok) {
                location.reload();
            } else {
                alert('Error: Failed to save changes');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while saving changes');
        });
    });
});

function openBlueprintRunner(blueprintId, blueprintName, blueprintCode) {
    document.getElementById('runnerBlueprintName').textContent = blueprintName;

    window.currentBlueprint = {
        id: blueprintId,
        name: blueprintName,
        code: blueprintCode
    };

    const chatLink = document.getElementById('runnerChatLink');
    if (chatLink && blueprintId) {
        chatLink.href = `/chat?blueprint=${encodeURIComponent(blueprintId)}`;
    }

    const modal = new bootstrap.Modal(document.getElementById('blueprintRunnerModal'));
    modal.show();
}

async function runBlueprint() {
    const input = document.getElementById('blueprintInput').value;
    const outputDiv = document.getElementById('blueprintOutput');
    const blueprint = window.currentBlueprint;

    if (!blueprint || !blueprint.id) {
        showStatus('No blueprint selected', 'warning');
        return;
    }
    if (!input.trim()) {
        showStatus('Please enter some input for the blueprint', 'warning');
        return;
    }

    const runBtn = document.getElementById('runBlueprintBtn');
    showStatus('Calling /v1/chat/completions…', 'info');
    if (runBtn) {
        runBtn.disabled = true;
        runBtn.setAttribute('aria-busy', 'true');
        runBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Running…';
    }
    outputDiv.innerHTML = '<div class="text-center py-3" role="status" aria-live="polite"><div class="spinner-border text-primary" role="status"></div><p class="mt-2 mb-0">Executing blueprint…</p></div>';

    const resetRunBtn = () => {
        if (!runBtn) return;
        runBtn.disabled = false;
        runBtn.removeAttribute('aria-busy');
        runBtn.innerHTML = '<i class="fas fa-play me-1" aria-hidden="true"></i>Run via API';
    };

    try {
        const response = await fetch('/v1/chat/completions/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({
                model: blueprint.id,
                messages: [{ role: 'user', content: input }],
            }),
        });
        const raw = await response.text();
        let data = null;
        try {
            data = raw ? JSON.parse(raw) : null;
        } catch (_parseErr) {
            data = null;
        }

        outputDiv.replaceChildren();
        const pre = document.createElement('pre');
        pre.className = 'mb-0';

        if (!response.ok) {
            const detail =
                (data && (data.error?.message || data.detail || data.error)) ||
                raw ||
                response.statusText;
            pre.textContent = `HTTP ${response.status}: ${typeof detail === 'string' ? detail : JSON.stringify(detail, null, 2)}`;
            outputDiv.appendChild(pre);
            showStatus(
                'API run failed — try Open in Chat or Teams launch, or enable user blueprint discovery for custom agents',
                'warning'
            );
            resetRunBtn();
            return;
        }

        const content =
            data?.choices?.[0]?.message?.content ??
            data?.choices?.[0]?.delta?.content ??
            (data ? JSON.stringify(data, null, 2) : raw);
        pre.textContent = content == null ? '' : String(content);
        outputDiv.appendChild(pre);
        showStatus('Blueprint run finished', 'success');
    } catch (error) {
        outputDiv.replaceChildren();
        const pre = document.createElement('pre');
        pre.className = 'mb-0';
        pre.textContent = `Request failed: ${error && error.message ? error.message : error}`;
        outputDiv.appendChild(pre);
        showStatus('Network or browser error calling chat completions', 'danger');
    } finally {
        resetRunBtn();
    }
}

function showStatus(message, type) {
    const statusDiv = document.getElementById('runnerStatus');
    const statusMessage = document.getElementById('statusMessage');
    
    statusMessage.textContent = message;
    statusDiv.className = `alert alert-${type}`;
    statusDiv.classList.remove('d-none');
}

function previewBlueprint(blueprintId) {
    window.open(`/blueprint/${encodeURIComponent(blueprintId)}/`, '_blank');
}

function removeBlueprint(blueprintId, blueprintName) {
    const label = blueprintName || 'this blueprint';
    if (!confirm(`Remove ${label} from your library?`)) {
        return;
    }
    fetch(`/blueprint-library/remove/${encodeURIComponent(blueprintId)}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert('Error: ' + (data.error || 'Failed to remove blueprint'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while removing the blueprint');
    });
}

function editBlueprint(blueprintId) {
    fetch(`/v1/blueprints/custom/${encodeURIComponent(blueprintId)}/`)
        .then(response => response.json())
        .then(blueprint => {
            document.getElementById('edit_blueprint_id').value = blueprint.id;
            document.getElementById('edit_name').value = blueprint.name;
            document.getElementById('edit_category').value = blueprint.category;
            document.getElementById('edit_description').value = blueprint.description;
            document.getElementById('edit_tags').value = (blueprint.tags || []).join(', ');
            document.getElementById('edit_requirements').value = blueprint.requirements || '';
            document.getElementById('edit_code').value = blueprint.code || '';

            const modal = new bootstrap.Modal(document.getElementById('editBlueprintModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while fetching blueprint details');
        });
}

function deleteBlueprint(blueprintId, blueprintName) {
    const label = blueprintName || 'this custom blueprint';
    if (!confirm(`Delete ${label}? This cannot be undone.`)) {
        return;
    }
    fetch(`/v1/blueprints/custom/${encodeURIComponent(blueprintId)}/`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        }
    })
    .then(response => {
        if (response.ok) {
            location.reload();
        } else {
            alert('Error: Failed to delete blueprint');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while deleting the blueprint');
    });
}
