async function handleSubmit(event) {
    event.preventDefault();
    const input = document.getElementById('userInput');
    const message = input.value.trim();
    const blueprintName = document.getElementById('blueprintTitle').textContent;
    if (!message) return;

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
                model: blueprintName,
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

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('sendButton').addEventListener('click', handleSubmit);
    document.getElementById('userInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSubmit(e);
    });
});
