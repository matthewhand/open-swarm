async function fetchBlueprints() {
    const response = await fetch('/v1/models/');
    const data = await response.json();
    return data.data.filter(model => model.object === 'model');
}

function populateBlueprintDropdown(blueprints) {
    const dropdown = document.getElementById('blueprintDropdown');
    dropdown.innerHTML = '<option value="">Select a Blueprint</option>';
    blueprints.forEach(bp => {
        const option = document.createElement('option');
        option.value = bp.id;
        option.textContent = bp.title;
        dropdown.appendChild(option);
    });
}

let currentBlueprint = null;
let currentMode = 'default';
function switchBlueprint(blueprintId) {
    currentBlueprint = blueprintId;
    document.getElementById('messageHistory').innerHTML = '';
    document.getElementById('blueprintTitle').textContent = blueprintId || 'No Blueprint Selected';
    console.log(`Switched to blueprint: ${blueprintId}, mode: ${currentMode}`);
}

function setMode(mode) {
    currentMode = mode;
    console.log(`Mode set to: ${mode}`);
}

async function handleSubmit(event) {
    event.preventDefault();
    const input = document.getElementById('userInput');
    const message = input.value.trim();
    if (!message || !currentBlueprint) {
        console.log('No message or blueprint selected');
        return;
    }

    input.value = '';
    const history = document.getElementById('messageHistory');
    history.innerHTML += `<div class="user-message">${message} (Mode: ${currentMode})</div>`;

    try {
        const response = await fetch('/v1/chat/completions/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify({
                model: currentBlueprint,
                messages: [{ role: 'user', content: message }],
                context_variables: { mode: currentMode }
            })
        });
        const data = await response.json();
        history.innerHTML += `<div class="assistant-message">${data.choices[0].message.content}</div>`;
        history.scrollTop = history.scrollHeight;
    } catch (error) {
        history.innerHTML += `<div class="error-message">Error: ${error.message}</div>`;
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const blueprints = await fetchBlueprints();
    populateBlueprintDropdown(blueprints);
    if (blueprints.length > 0) switchBlueprint(blueprints[0].id);

    document.getElementById('blueprintDropdown').addEventListener('change', (e) => switchBlueprint(e.target.value));
    document.querySelectorAll('.mode-button').forEach(button => {
        button.addEventListener('click', () => setMode(button.dataset.mode));
    });
    document.getElementById('sendButton')?.addEventListener('click', handleSubmit);
    document.getElementById('userInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSubmit(e);
    });
});
