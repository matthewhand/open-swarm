async function fetchBlueprints() {
    const response = await fetch('/v1/models/');
    const data = await response.json();
    return data.data.filter((model) => model.object === 'model');
}

function populateBlueprintDropdown(blueprints) {
    const dropdown = document.getElementById('blueprintDropdown');
    if (!dropdown) return;
    dropdown.innerHTML = '<option value="">Select a Blueprint</option>';
    blueprints.forEach((bp) => {
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
    const history = document.getElementById('messageHistory');
    if (history) history.innerHTML = '';
    const title = document.getElementById('blueprintTitle');
    if (title) title.textContent = blueprintId || 'No Blueprint Selected';
    console.log(`Switched to blueprint: ${blueprintId}, mode: ${currentMode}`);
}

function setMode(mode) {
    currentMode = mode;
    console.log(`Mode set to: ${mode}`);
}

function appendMessage(history, className, text) {
    const div = document.createElement('div');
    div.className = className;
    div.textContent = text == null ? '' : String(text);
    history.appendChild(div);
}

async function handleSubmit(event) {
    event.preventDefault();
    const input = document.getElementById('userInput');
    const message = input?.value.trim();
    if (!message || !currentBlueprint) {
        console.log('No message or blueprint selected');
        return;
    }

    input.value = '';
    const history = document.getElementById('messageHistory');
    if (!history) return;
    appendMessage(history, 'user-message', `${message} (Mode: ${currentMode})`);

    try {
        const response = await fetch('/v1/chat/completions/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content,
            },
            body: JSON.stringify({
                model: currentBlueprint,
                messages: [{ role: 'user', content: message }],
                context_variables: { mode: currentMode },
            }),
        });
        const data = await response.json();
        appendMessage(history, 'assistant-message', data.choices[0].message.content);
        history.scrollTop = history.scrollHeight;
    } catch (error) {
        appendMessage(history, 'error-message', `Error: ${error.message}`);
    }
}

/** Wired from ui.js initializeUI — keeps chatLogic a proper ESM export. */
export async function initializeChatLogic() {
    const dropdown = document.getElementById('blueprintDropdown');
    const sendButton = document.getElementById('sendButton');
    const userInput = document.getElementById('userInput');
    if (!dropdown || !userInput) {
        // Demo markup not present (canonical SPA/Django chat elsewhere).
        return;
    }

    const blueprints = await fetchBlueprints();
    populateBlueprintDropdown(blueprints);
    if (blueprints.length > 0) switchBlueprint(blueprints[0].id);

    dropdown.addEventListener('change', (e) => switchBlueprint(e.target.value));
    document.querySelectorAll('.mode-button').forEach((button) => {
        button.addEventListener('click', () => setMode(button.dataset.mode));
    });
    sendButton?.addEventListener('click', handleSubmit);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSubmit(e);
    });
}
