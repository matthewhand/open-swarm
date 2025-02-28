async function fetchBlueprints() {
    const response = await fetch('/v1/models/');
    const data = await response.json();
    return data.data.filter(model => model.object === 'model');
}

function populateChannelList(blueprints) {
    const list = document.getElementById('channelList');
    list.innerHTML = '';
    blueprints.forEach(bp => {
        const li = document.createElement('li');
        li.textContent = `# ${bp.title}`;
        li.dataset.blueprintId = bp.id;
        li.addEventListener('click', () => switchChannel(bp.id));
        list.appendChild(li);
    });
}

let currentBlueprint = null;
function switchChannel(blueprintId) {
    currentBlueprint = blueprintId;
    document.getElementById('messageHistory').innerHTML = '';
    document.getElementById('blueprintTitle').textContent = blueprintId;
    console.log(`Switched to channel: ${blueprintId}`);
}

async function handleSubmit(event) {
    event.preventDefault();
    const input = document.getElementById('userInput');
    const message = input.value.trim();
    if (!message || !currentBlueprint) return;

    input.value = '';
    const history = document.getElementById('messageHistory');
    history.innerHTML += `<div class="user-message">${message}</div>`;

    try {
        const response = await fetch('/v1/chat/completions/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify({
                model: currentBlueprint,
                messages: [{ role: 'user', content: message }]
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
    populateChannelList(blueprints);
    if (blueprints.length > 0) switchChannel(blueprints[0].id);

    document.getElementById('sendButton').addEventListener('click', handleSubmit);
    document.getElementById('userInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSubmit(e);
    });
});
