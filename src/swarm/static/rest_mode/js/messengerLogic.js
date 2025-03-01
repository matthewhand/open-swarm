async function fetchBlueprints() {
    console.log('Fetching blueprints from /v1/models/ at:', new Date().toISOString());
    try {
        const response = await fetch('/v1/models/');
        if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
        const data = await response.json();
        console.log('Raw response from /v1/models/:', data); // Print the raw response
        const blueprints = data.data.filter(model => model.object === 'model');
        console.log('Filtered blueprints:', blueprints);
        return blueprints;
    } catch (error) {
        console.error('Error fetching blueprints:', error);
        return [];
    }
}

function populateChannelList(blueprints) {
    console.log('Populating channel list with blueprints:', blueprints);
    const list = document.getElementById('channelList');
    if (!list) {
        console.error('Channel list element not found!');
        return;
    }
    console.log('Channel list found, initial HTML:', list.innerHTML);
    list.innerHTML = ''; // Clear to ensure test data
    // Preserve or add pseudo-channel
    const existingPseudo = list.querySelector('li[data-blueprint-id="welcome"]');
    if (!existingPseudo) {
        list.innerHTML += '<li data-blueprint-id="welcome">#Welcome to Open-Swarm</li>';
        console.log('Added pseudo-channel');
    }
    // Force test data
    const testData = [
        { id: 'test1', title: 'Test Channel 1' },
        { id: 'test2', title: 'Test Channel 2' }
    ];
    testData.forEach(bp => {
        if (!list.querySelector(`li[data-blueprint-id="${bp.id}"]`)) {
            const li = document.createElement('li');
            li.textContent = `# ${bp.title}`;
            li.dataset.blueprintId = bp.id;
            li.addEventListener('click', () => switchChannel(bp.id));
            list.appendChild(li);
            console.log('Added test channel:', bp.title);
        }
    });
    blueprints.forEach(bp => {
        if (!list.querySelector(`li[data-blueprint-id="${bp.id}"]`)) {
            const li = document.createElement('li');
            li.textContent = `# ${bp.title}`;
            li.dataset.blueprintId = bp.id;
            li.addEventListener('click', () => switchChannel(bp.id));
            list.appendChild(li);
            console.log('Added blueprint:', bp.title);
        }
    });
    console.log('Channel list updated:', list.innerHTML);
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
    if (!message || !currentBlueprint) {
        console.log('No message or blueprint selected, skipping submission');
        return;
    }
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
        console.error('Error submitting message:', error);
        history.innerHTML += `<div class="error-message">Error: ${error.message}</div>`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded, initializing Messenger at:', new Date().toISOString());
    const blueprints = []; // Disable fetch to test DOM with test data
    populateChannelList(blueprints);
    if (blueprints.length > 0) {
        switchChannel(blueprints[0].id);
    } else {
        console.log('No blueprints available, using test data at:', new Date().toISOString());
    }
    document.getElementById('sendButton').addEventListener('click', handleSubmit);
    document.getElementById('userInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSubmit(e);
    });
});
// Append debugging and test data
console.log('Appending debug at:', new Date().toISOString());
const originalPopulate = populateChannelList;
populateChannelList = function(blueprints) {
    console.log('Original populate called with:', blueprints);
    originalPopulate(blueprints); // Call your original function
    // Force test data
    const testData = [
        { id: 'test1', title: 'Test Channel 1' },
        { id: 'test2', title: 'Test Channel 2' }
    ];
    const list = document.getElementById('channelList');
    if (list) {
        testData.forEach(bp => {
            if (!list.querySelector(`li[data-blueprint-id="${bp.id}"]`)) {
                const li = document.createElement('li');
                li.textContent = `# ${bp.title}`;
                li.dataset.blueprintId = bp.id;
                li.addEventListener('click', () => switchChannel(bp.id));
                list.appendChild(li);
                console.log('Added test channel:', bp.title, 'at:', new Date().toISOString());
            }
        });
        console.log('Channel list updated with test data:', list.innerHTML);
    } else {
        console.error('Channel list not found during test data append!');
    }
};
// Append debug and test data
console.log('Appending debug at:', new Date().toISOString());
const originalFetch = fetchBlueprints;
fetchBlueprints = async function() {
    console.log('Fetching blueprints with debug at:', new Date().toISOString());
    const blueprints = await originalFetch();
    console.log('Fetch result:', blueprints);
    return blueprints;
};
const originalPopulate = populateChannelList;
populateChannelList = function(blueprints) {
    console.log('Populating with debug:', blueprints);
    originalPopulate(blueprints);
    if (blueprints.length === 0) {
        const testData = [
            { id: 'test1', title: 'Test Channel 1' },
            { id: 'test2', title: 'Test Channel 2' }
        ];
        const list = document.getElementById('channelList');
        if (list) {
            testData.forEach(bp => {
                if (!list.querySelector(`li[data-blueprint-id="${bp.id}"]`)) {
                    const li = document.createElement('li');
                    li.textContent = `# ${bp.title}`;
                    li.dataset.blueprintId = bp.id;
                    li.addEventListener('click', () => switchChannel(bp.id));
                    list.appendChild(li);
                    console.log('Added test channel:', bp.title);
                }
            });
            console.log('Updated with test data:', list.innerHTML);
        }
    }
};
// Append debug and test data
console.log('Debug append at:', new Date().toISOString());
const originalPopulate = populateChannelList;
populateChannelList = function(blueprints) {
    console.log('Populating with:', blueprints);
    originalPopulate(blueprints);
    const testData = [
        { id: 'test1', title: 'Test Channel 1' },
        { id: 'test2', title: 'Test Channel 2' }
    ];
    const list = document.getElementById('channelList');
    if (list) {
        testData.forEach(bp => {
            if (!list.querySelector(`li[data-blueprint-id="${bp.id}"]`)) {
                const li = document.createElement('li');
                li.textContent = `# ${bp.title}`;
                li.dataset.blueprintId = bp.id;
                li.addEventListener('click', () => switchChannel(bp.id));
                list.appendChild(li);
                console.log('Added test:', bp.title);
            }
        });
        console.log('List after test:', list.innerHTML);
    } else {
        console.error('No channel list found!');
    }
};
// Append debug and test data
console.log('MessengerLogic debug append at:', new Date().toISOString());
const originalFetch = fetchBlueprints;
fetchBlueprints = async function() {
    console.log('Executing fetchBlueprints at:', new Date().toISOString());
    const response = await originalFetch();
    console.log('Fetch result from /v1/models/:', response);
    return response;
};
const originalPopulate = populateChannelList;
populateChannelList = function(blueprints) {
    console.log('Executing populateChannelList with:', blueprints);
    originalPopulate(blueprints);
    if (blueprints.length === 0 || !blueprints) {
        console.log('No blueprints, forcing test data at:', new Date().toISOString());
        const testData = [
            { id: 'test1', title: 'Test Channel 1' },
            { id: 'test2', title: 'Test Channel 2' }
        ];
        const list = document.getElementById('channelList');
        if (list) {
            testData.forEach(bp => {
                if (!list.querySelector(`li[data-blueprint-id="${bp.id}"]`)) {
                    const li = document.createElement('li');
                    li.textContent = `# ${bp.title}`;
                    li.dataset.blueprintId = bp.id;
                    li.addEventListener('click', () => switchChannel(bp.id));
                    list.appendChild(li);
                    console.log('Populated test channel:', bp.title);
                }
            });
            console.log('Channel list after population:', list.innerHTML);
        } else {
            console.error('Channel list not found!');
        }
    }
};
// Append debug and test data
console.log('MessengerLogic debug append at:', new Date().toISOString());
const originalFetch = fetchBlueprints;
fetchBlueprints = async function() {
    console.log('Executing fetchBlueprints at:', new Date().toISOString());
    const response = await originalFetch();
    console.log('Fetch result from /v1/models/:', response);
    return response;
};
const originalPopulate = populateChannelList;
populateChannelList = function(blueprints) {
    console.log('Executing populateChannelList with:', blueprints);
    originalPopulate(blueprints);
    if (blueprints.length === 0 || !blueprints) {
        console.log('No blueprints, forcing test data at:', new Date().toISOString());
        const testData = [
            { id: 'test1', title: 'Test Channel 1' },
            { id: 'test2', title: 'Test Channel 2' }
        ];
        const list = document.getElementById('channelList');
        if (list) {
            testData.forEach(bp => {
                if (!list.querySelector(`li[data-blueprint-id="${bp.id}"]`)) {
                    const li = document.createElement('li');
                    li.textContent = `# ${bp.title}`;
                    li.dataset.blueprintId = bp.id;
                    li.addEventListener('click', () => switchChannel(bp.id));
                    list.appendChild(li);
                    console.log('Populated test channel:', bp.title);
                }
            });
            console.log('Channel list after population:', list.innerHTML);
        } else {
            console.error('Channel list not found!');
        }
    }
};
// Append load check and test data
console.log('MessengerLogic loaded at:', new Date().toISOString());
const originalPopulate = populateChannelList;
populateChannelList = function(blueprints) {
    console.log('Populating with blueprints at:', new Date().toISOString(), blueprints);
    originalPopulate(blueprints);
    if (!blueprints || blueprints.length === 0) {
        console.log('No blueprints, adding test data at:', new Date().toISOString());
        const testData = [
            { id: 'test1', title: 'Test Channel 1' },
            { id: 'test2', title: 'Test Channel 2' }
        ];
        const list = document.getElementById('channelList');
        if (list) {
            testData.forEach(bp => {
                if (!list.querySelector(`li[data-blueprint-id="${bp.id}"]`)) {
                    const li = document.createElement('li');
                    li.textContent = `# ${bp.title}`;
                    li.dataset.blueprintId = bp.id;
                    li.addEventListener('click', () => switchChannel(bp.id));
                    list.appendChild(li);
                    console.log('Added test channel:', bp.title);
                }
            });
            console.log('Channel list updated:', list.innerHTML);
        } else {
            console.error('Channel list not found!');
        }
    }
};
// Append debug and combine ideas
console.log('Debug append at:', new Date().toISOString());
const originalFetch = fetchBlueprints;
fetchBlueprints = async function() {
    console.log('Fetching blueprints like dropdown at:', new Date().toISOString());
    const blueprints = await originalFetch();
    console.log('Fetch result (like Chatbot dropdown):', blueprints);
    return blueprints;
};
const originalPopulate = populateChannelList;
populateChannelList = function(blueprints) {
    console.log('Populating like pseudo-channel with:', blueprints);
    originalPopulate(blueprints); // Your logic
    if (!blueprints || blueprints.length === 0) {
        console.log('No blueprints, adding test channels at:', new Date().toISOString());
        const testData = [
            { id: 'test1', title: 'Test Channel 1' },
            { id: 'test2', title: 'Test Channel 2' }
        ];
        const list = document.getElementById('channelList');
        if (list) {
            testData.forEach(bp => {
                if (!list.querySelector(`li[data-blueprint-id="${bp.id}"]`)) {
                    const li = document.createElement('li');
                    li.textContent = `# ${bp.title}`;
                    li.dataset.blueprintId = bp.id;
                    li.addEventListener('click', () => switchChannel(bp.id));
                    list.appendChild(li);
                    console.log('Added test channel (like pseudo):', bp.title);
                }
            });
            console.log('Channel list updated:', list.innerHTML);
        }
    }
};
// Append fetch debug
console.log('Debug append at:', new Date().toISOString());
const originalFetch = fetchBlueprints;
fetchBlueprints = async function() {
    console.log('Fetching blueprints at:', new Date().toISOString());
    try {
        const response = await originalFetch();
        console.log('Fetch result from /v1/models/:', response);
        return response;
    } catch (error) {
        console.error('Fetch error:', error);
        return [];
    }
};
