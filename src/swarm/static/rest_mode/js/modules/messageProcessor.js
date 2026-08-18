// src/swarm/static/rest_mode/js/modules/messageProcessor.js

import { showToast } from '../toast.js';
import { appendRawMessage } from '../messages.js';
import { showLoadingIndicator, hideLoadingIndicator } from '../ui.js';

import { submitMessage } from './apiService.js';
import { debugLog } from './debugLogger.js';
import { validateMessage } from './validation.js';
import { chatHistory, contextVariables } from './state.js'; // Assuming state.js manages shared state
import { createChatHistoryEntry } from './chatHistory.js';

/**
 * Processes the assistant's response and updates context variables.
 * @param {Object} data - The response data from the server.
 * @param {Object} contextVariables - The current context variables.
 */
export function processAssistantResponse(data, contextVariables) {
    if (!data.choices || !Array.isArray(data.choices)) {
        debugLog('Invalid response structure:', data);
        showToast('⚠️ Invalid response from server.', 'error');
        return;
    }

    data.choices.forEach((choice) => {
        const rawMessage = { ...choice.message };

        const role = rawMessage.role || 'assistant';
        const content = rawMessage.content || 'No content';
        const sender = rawMessage.sender || (role === 'user' ? 'User' : 'Assistant');

        appendRawMessage(role, { content }, sender, rawMessage.metadata);
    });

    debugLog('Assistant response processed successfully.', data);
}

/**
 * Handles user message submission.
 * @returns {Promise<void>}
 */
export async function handleSubmit() {
    const userInput = document.getElementById("userInput");
    if (!userInput) {
        debugLog("User input element not found.");
        return;
    }

    const userMessageContent = userInput.value.trim();
    if (!userMessageContent) {
        showToast("❌ You cannot send an empty message.", "error");
        debugLog("Empty message submission blocked.");
        return;
    }

    // Clear input field
    userInput.value = "";

    const userMessage = {
        role: "user",
        content: userMessageContent,
        sender: "User",
        metadata: {},
    };
    chatHistory.push(userMessage);
    debugLog("User message added to chat history.", userMessage);

    const isFirstUserMessage = chatHistory.filter((msg) => msg.role === "user").length === 1;

    // Validate the message
    const error = validateMessage(userMessage);
    if (error) return;

    // Render the user message in the UI
    appendRawMessage(userMessage.role, { content: userMessage.content }, userMessage.sender, userMessage.metadata);

    // If it's the first user message, update the persistent message and create a new chat history entry
    if (isFirstUserMessage) {
        const persistentMessageElement = document.getElementById('firstUserMessage');
        if (persistentMessageElement) {
            persistentMessageElement.replaceChildren();
            const label = document.createElement('b');
            label.textContent = 'Persist:';
            const body = document.createElement('p');
            body.textContent = `User: ${userMessageContent}`;
            persistentMessageElement.appendChild(label);
            persistentMessageElement.appendChild(body);
            debugLog("Persistent message updated with the first user message.");
        }
        createChatHistoryEntry("New Chat", userMessageContent);
    }

    showLoadingIndicator(); // Show loading spinner

    try {
        const urlPath = window.location.pathname;
        const modelName = urlPath.split("/").filter(Boolean).pop() || "";
        debugLog("Submitting message to model.", { modelName, message: userMessageContent });

        const response = await fetch("/v1/chat/completions", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "",
            },
            body: JSON.stringify({
                model: modelName,
                messages: chatHistory,
                context_variables: contextVariables,
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }

        const data = await response.json();
        debugLog("Message successfully processed by the model.", data);
        processAssistantResponse(data, contextVariables); // Ensure this matches your function signature
    } catch (err) {
        console.error("Error submitting message:", err);
        showToast("⚠️ Error submitting message. Please try again.", "error");
    } finally {
        hideLoadingIndicator(); // Hide loading spinner
    }
}
