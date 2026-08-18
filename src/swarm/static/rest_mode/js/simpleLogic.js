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
    const blueprintName = document.getElementById('blueprintTitle')?.textContent;
    if (!message) return;

    input.value = '';
    const history = document.getElementById('messageHistory');
    if (!history) return;
    appendMessage(history, 'user-message', message);

    try {
        const response = await fetch('/v1/chat/completions/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content,
            },
            body: JSON.stringify({
                model: blueprintName,
                messages: [{ role: 'user', content: message }],
            }),
        });
        const data = await response.json();
        appendMessage(history, 'assistant-message', data.choices[0].message.content);
        history.scrollTop = history.scrollHeight;
    } catch (error) {
        appendMessage(history, 'error-message', `Error: ${error.message}`);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('sendButton')?.addEventListener('click', handleSubmit);
    document.getElementById('userInput')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSubmit(e);
    });
});
