// src/swarm/static/rest_mode/js/debug.js

import { showToast } from './toast.js';
import { escapeHtml } from './htmlSafe.js';
import { chatHistory } from './modules/state.js';
import { contextVariables } from './modules/state.js';
export { debugLog } from './modules/debugLogger.js'; 

/**
 * Toggles the Debug pane.
 * Displays raw messages and key info from the most recent message.
 */
export function toggleDebugPane() {
    const debugPane = document.getElementById("debugPane");
    if (!debugPane) return;

    if (debugPane.style.display === "block") {
        debugPane.style.display = "none";
        showToast("🐞 Debug pane hidden.", "info");
    } else {
        debugPane.style.display = "block";
        showToast("🐞 Debug pane shown.", "info");
        renderRelevantDebugInfo();
    }
}

/**
 * Handles Tech Support Button Click Inside Debug Pane
 */
export function handleTechSupport() {
    showToast("🛠️ Tech Support feature coming soon!", "info");
}

/**
 * Renders relevant debug information from the most recent message in chatHistory.
 */
function renderRelevantDebugInfo() {
    const debugContent = document.getElementById("debugContent");
    if (!debugContent) return;

    if (chatHistory.length === 0) {
        debugContent.innerHTML = "<p>No messages yet.</p>";
        return;
    }

    const latestMessage = chatHistory[chatHistory.length - 1];
    const { role, content, sender, metadata } = latestMessage;

    debugContent.innerHTML = `
        <p><strong>Role:</strong> ${escapeHtml(role)}</p>
        <p><strong>Sender:</strong> ${escapeHtml(sender)}</p>
        <p><strong>Content:</strong> ${escapeHtml(content || "No content provided.")}</p>
        <p><strong>Metadata:</strong> <pre>${escapeHtml(JSON.stringify(metadata || {}, null, 2))}</pre></p>
    `;

    if (contextVariables.active_agent_name) {
        const activeAgentElement = document.createElement("div");
        activeAgentElement.className = "debug-active-agent";
        const label = document.createElement("strong");
        label.textContent = "Active Agent:";
        activeAgentElement.appendChild(label);
        activeAgentElement.appendChild(
            document.createTextNode(` ${contextVariables.active_agent_name}`),
        );
        debugContent.appendChild(activeAgentElement);
    }

    debugContent.scrollTop = debugContent.scrollHeight;
}
