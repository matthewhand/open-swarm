 // src/swarm/static/rest_mode/js/modules/chatHistory.js

import { showToast } from '../toast.js';
import { appendRawMessage } from '../messages.js';
import { escapeAttr, escapeHtml } from '../htmlSafe.js';
import { deleteChat } from './apiService.js';
import { debugLog } from './debugLogger.js';
import { chatHistory, contextVariables } from './state.js';

/**
 * Truncates long messages and adds a "more..." link if needed.
 * @param {string} content - The message content to truncate.
 * @param {number} maxLength - The maximum length before truncation.
 * @returns {string} - The truncated message with a "more..." link if applicable.
 */
function truncateMessage(content, maxLength = 50) {
    const text = content == null ? '' : String(content);
    if (text.length > maxLength) {
        const truncated = escapeHtml(text.slice(0, maxLength));
        return `<span data-full-content="${escapeAttr(text)}">${truncated}... <a href="#" class="read-more">more</a></span>`;
    }
    return escapeHtml(text);
}

/**
 * Creates a new chat history entry in the sidebar.
 * @param {string} firstMessage - The user's first message in the chat.
 */
export function createChatHistoryEntry(chatName, firstMessage) {
    const chatHistoryPane = document.getElementById('chatHistoryPane');
    if (!chatHistoryPane) {
        debugLog('Chat history pane element not found.');
        return;
    }

    // Create new chat history item
    const chatItem = document.createElement('li');
    chatItem.className = 'chat-history-item';

    // Generate truncated message with "more..." link if necessary
    const truncatedMessage = truncateMessage(firstMessage);
    const trashIcon = escapeAttr(window.STATIC_URLS?.trashIcon || '');

    // Populate the chat history item
    chatItem.innerHTML = `
        <details>
            <summary>${escapeHtml(chatName)}</summary>
            <p>${truncatedMessage}</p>
            <span class="chat-item-time">${escapeHtml(new Date().toLocaleString())}</span>
                <div class="chat-item-tools">
                    <!-- Tag Buttons and Delete Button -->
                    <div class="chat-item-tags">
                        <button class="tag-button" aria-label="Filter by General">General</button>
                        <button class="tag-button" aria-label="Filter by Introduction">Introduction</button>
                        <button class="tag-button" aria-label="Filter by Welcome">Welcome</button>
                        <button class="tag-button add-tag-btn" aria-label="Add Tag">+</button>
                        <!-- Delete Button -->
                        <button class="toolbar-btn delete-chat-btn" title="Delete Chat" aria-label="Delete Chat">
                            <img src="${trashIcon}" alt="Delete Chat">
                        </button>
                    </div>
                </div>
        </details>
    `;

    // Add the new chat item to the top of the list
    const chatList = chatHistoryPane.querySelector('.chat-history-list');
    if (chatList) {
        chatList.prepend(chatItem); // Insert at the top
        debugLog('New chat history entry created and added to the list.', chatItem);
    }

    // Event listener for "more..." links — textContent, never innerHTML of stored content
    chatItem.querySelectorAll('.read-more').forEach(link => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            const parent = link.parentElement;
            if (parent) {
                parent.textContent = parent.getAttribute('data-full-content') || '';
            }
        });
    });

    // Event listener for delete button
    const deleteBtn = chatItem.querySelector('.delete-chat-btn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', () => deleteChat(chatItem));
    }

    // Event listener for selecting the chat item
    chatItem.addEventListener('click', (event) => {
        // Prevent triggering when clicking on "more..." link or delete button
        if (event.target.classList.contains('read-more') || event.target.closest('.delete-chat-btn')) {
            return;
        }
        handleChatHistoryClick(chatItem);
    });
}

/**
 * Handles chat history item click.
 * @param {HTMLElement} item - The clicked chat history item.
 */
export function handleChatHistoryClick(item) {
    const chatName = item.querySelector('summary').textContent.trim();
    showToast(`Selected: "${chatName}"`, 'info');

    const chatHistoryItems = document.querySelectorAll('.chat-history-pane li');
    chatHistoryItems.forEach((i) => i.classList.remove('active'));
    item.classList.add('active');

    // Additional logic to load the selected chat can be added here
}
