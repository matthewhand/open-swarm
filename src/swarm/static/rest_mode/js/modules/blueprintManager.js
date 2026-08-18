// src/swarm/static/rest_mode/js/modules/blueprintManager.js

import { fetchBlueprintMetadata as fetchMetadataAPI } from './apiService.js';
import { showToast } from '../toast.js';
import { appendRawMessage } from '../messages.js';
import { escapeAttr, escapeHtml } from '../htmlSafe.js';
import { debugLog } from './debugLogger.js';
import { createChatHistoryEntry } from './chatHistory.js';

/**
 * Populates the blueprint selection dialog and dropdown.
 * @param {Array} blueprints - The list of blueprints fetched from the API.
 */
function populateBlueprintDialog(blueprints) {
    const blueprintDialogElement = document.getElementById('blueprintDialog');
    const blueprintDropdown = document.getElementById('blueprintDropdown');
    const currentPath = window.location.pathname; // Get the current URL path

    if (!blueprintDialogElement) {
        debugLog('Blueprint dialog not found.');
        return;
    }

    // Populate dialog (escape API title/description/id before innerHTML)
    blueprintDialogElement.innerHTML = blueprints
        .map(
            (bp) => `
        <div class="blueprint-option" data-id="${escapeAttr(bp.id)}">
            <p class="blueprint-title">${escapeHtml(bp.title)}</p>
            <p class="blueprint-description">${escapeHtml(bp.description)}</p>
        </div>`
        )
        .join('');

    if (!blueprintDropdown) {
        debugLog('Blueprint dropdown element not found.');
        return;
    }

    // Populate dropdown
    blueprintDropdown.innerHTML = blueprints
        .map(
            (bp) => `
        <option value="${escapeAttr(bp.id)}">${escapeHtml(bp.title)}</option>`
        )
        .join('');

    // Add click event for each dialog option
    blueprintDialogElement.querySelectorAll('.blueprint-option').forEach((option) => {
        option.addEventListener('click', () => {
            const selectedId = option.getAttribute('data-id');
            const selectedBlueprint = blueprints.find((bp) => bp.id === selectedId);
            if (selectedBlueprint) {
                selectBlueprint(selectedBlueprint, true); // User-initiated selection
            }
        });
    });

    // Add change event for dropdown
    blueprintDropdown.addEventListener('change', (event) => {
        const selectedId = event.target.value;
        const selectedBlueprint = blueprints.find((bp) => bp.id === selectedId);
        if (selectedBlueprint) {
            selectBlueprint(selectedBlueprint, true); // User-initiated selection
        }
    });
}

/**
 * Updates the UI and metadata when a blueprint is selected.
 * @param {Object} blueprint - The selected blueprint.
 * @param {boolean} isUserInitiated - Indicates if the selection was made by the user.
 */
export function selectBlueprint(blueprint, isUserInitiated = false) {
    const blueprintMetadataElement = document.getElementById('blueprintMetadata');
    const blueprintTitleElement = document.getElementById('blueprintTitle');
    const blueprintDialogElement = document.getElementById('blueprintDialog');
    const blueprintDropdown = document.getElementById('blueprintDropdown');

    if (!blueprintMetadataElement || !blueprintTitleElement || !blueprintDropdown) {
        debugLog('Required elements for blueprint selection not found.');
        return;
    }

    const blueprintName = blueprint.title;
    const blueprintDescription = blueprint.description;

    // Update UI (escape untrusted API metadata before innerHTML)
    blueprintMetadataElement.innerHTML =
        `<h2>${escapeHtml(blueprintName)}</h2><p>${escapeHtml(blueprintDescription)}</p>`;
    blueprintTitleElement.textContent = blueprintName;

    // Update Dropdown Value
    blueprintDropdown.value = blueprint.id;

    // Hide the blueprint dialog
    if (blueprintDialogElement) {
        blueprintDialogElement.classList.add('hidden');
    }

    // Optionally, show the dropdown if in advanced mode
    // For simple chat mode, keep it hidden
    // blueprintDropdown.classList.remove('hidden'); // Uncomment if needed

    // Notify user about blueprint change only if it's user-initiated
    if (isUserInitiated) {
        appendRawMessage(
            'assistant',
            {
                content: `Blueprint loaded: ${blueprintName}`,
            },
            'Assistant'
        );
    }

    debugLog('Blueprint selected and UI updated.', blueprint);
}

/**
 * Initializes blueprint management by fetching metadata and populating the UI.
 */
export async function initializeBlueprints() {
    debugLog('Initializing blueprint management.');
    try {
        const blueprints = await fetchMetadataAPI();
        if (blueprints.length === 0) throw new Error('No blueprints available.');

        // Populate blueprint dialog and dropdown
        populateBlueprintDialog(blueprints);

        // Extract blueprint ID from the current path
        const currentPath = window.location.pathname;
        const pathSegments = currentPath.split('/').filter(segment => segment.length > 0);
        const blueprintId = pathSegments.length > 0 ? pathSegments[pathSegments.length - 1] : null;

        debugLog('Current Path:', currentPath);
        debugLog('Extracted Blueprint ID:', blueprintId);

        // Find the blueprint with the extracted ID
        const matchedBlueprint = blueprints.find(bp => bp.id === blueprintId);

        if (matchedBlueprint) {
            debugLog('Matched Blueprint:', matchedBlueprint);
            selectBlueprint(matchedBlueprint, false); // Programmatic selection
        } else {
            debugLog('No matched blueprint found. Selecting default blueprint:', blueprints[0]);
            // If no matching blueprint, select the first blueprint as default
            const defaultBlueprint = blueprints[0];
            selectBlueprint(defaultBlueprint, false); // Programmatic selection
        }
    } catch (error) {
        debugLog('Error fetching blueprint metadata:', error);
        console.error('Error initializing blueprints:', error);

        appendRawMessage(
            'assistant',
            {
                content:
                    'Could not retrieve blueprint metadata. Check out the troubleshooting guide at <a href="https://github.com/matthewhand/open-swarm/TROUBLESHOOTING.md">Troubleshooting Guide</a>.',
            },
            'Assistant'
        );
    }
}
