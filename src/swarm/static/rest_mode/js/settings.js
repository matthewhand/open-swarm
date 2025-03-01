const DEBUG_MODE = true;

import { showToast } from './toast.js';

export let llmConfig = {};

/**
 * Logs debug messages if debug mode is enabled.
 * @param {string} message - The message to log.
 * @param {any} data - Additional data to include in the log.
 */
export function debugLog(message, data = null) {
    if (DEBUG_MODE) {
        console.log(`[DEBUG] ${message}`, data);
    }
}

/**
 * Fetch and load LLM configuration.
 */
export async function loadLLMConfig() {
    debugLog("Attempting to load LLM configuration...");
    try {
        const response = await fetch('/config/swarm_config.json');
        debugLog("Received response from LLM config fetch.", { status: response.status });

        if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);
        const config = await response.json();
        debugLog("LLM configuration loaded successfully.", config);

        llmConfig = config.llm || {};
        updateLLMSettingsPane(llmConfig);
    } catch (error) {
        console.error("Error loading LLM config:", error);
        showToast("⚠️ LLM settings could not be loaded. Please check the server.", "warning");
    }
}

/**
 * Updates the settings pane with collapsible LLM modes and toggles.
 * @param {Object} config - The LLM configuration object.
 */
function updateLLMSettingsPane(config) {
    debugLog("Updating LLM settings pane...", config);

    const llmContainer = document.getElementById('llmConfiguration');
    if (!llmContainer) {
        console.warn("[DEBUG] LLM configuration container not found in the DOM.");
        return;
    }

    llmContainer.innerHTML = Object.entries(config)
        .map(([mode, details]) => {
            const isDefault = mode === 'default';
            const toggleHTML = `
                <div class="svg-toggle ${isDefault ? 'disabled' : ''}" data-state="on" id="toggle-${mode}">
                    <img src="/static/rest_mode/svg/toggle_on.svg" alt="Toggle On">
                </div>
            `;

            const fields = Object.entries(details)
                .map(([key, value]) => `
                    <div class="llm-field">
                        <label>${key}:</label>
                        <input type="text" value="${value}" readonly>
                    </div>
                `)
                .join('');

            return `
                <div class="llm-mode collapsible">
                    <h4 class="collapsible-toggle">
                        ${toggleHTML} ${mode.charAt(0).toUpperCase() + mode.slice(1)} Mode
                        <span>▼</span>
                    </h4>
                    <div class="collapsible-content hidden">
                        ${fields}
                    </div>
                </div>
            `;
        })
        .join('');

    initializeLLMModeToggles();
    initializeCollapsibleSections();
}

/**
 * Initialize toggles for LLM modes.
 */
function initializeLLMModeToggles() {
    Object.keys(llmConfig).forEach((mode) => {
        const toggle = document.getElementById(`toggle-${mode}`);
        if (toggle && mode !== 'default') {
            toggle.addEventListener('click', (event) => {
                event.stopPropagation();
                const isOn = toggle.dataset.state === 'on';
                toggle.dataset.state = isOn ? 'off' : 'on';
                toggle.querySelector('img').src = isOn
                    ? '/static/rest_mode/svg/toggle_off.svg'
                    : '/static/rest_mode/svg/toggle_on.svg';
                showToast(`${mode.charAt(0).toUpperCase() + mode.slice(1)} Mode ${isOn ? 'disabled' : 'enabled'}`);
            });
        }
    });
}

/**
 * Initialize collapsible behavior for LLM modes and sections.
 */
function initializeCollapsibleSections() {
    document.querySelectorAll('.collapsible-toggle').forEach((toggle) => {
        toggle.addEventListener('click', () => {
            const content = toggle.nextElementSibling;
            if (content) {
                content.classList.toggle('hidden');
                const isOpen = !content.classList.contains('hidden');
                toggle.querySelector('span').textContent = isOpen ? '▲' : '▼';
            }
        });
    });
}

/**
 * Initialize settings logic.
 */
document.addEventListener('DOMContentLoaded', () => {
    debugLog("Settings page initialized.");
    loadLLMConfig();
});
