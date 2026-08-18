/**
 * toast.js - Handles toast notifications
 */

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text == null ? '' : String(text);
    return div.innerHTML;
}

/**
 * Displays a toast notification.
 * @param {string} message - The message to display.
 * @param {string} type - The type of toast ('info', 'success', 'error', 'warning').
 */
export function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) return;

    // Create toast element
    const toast = document.createElement('div');
    toast.classList.add('toast', type);
    toast.innerHTML = `
        <span>${escapeHtml(message)}</span>
        <button class="close-btn" aria-label="Close">&times;</button>
    `;

    // Append to container
    toastContainer.appendChild(toast);

    // Auto-remove after 5 seconds (handled by CSS animation)
    setTimeout(() => {
        toast.classList.add('fade-out');
        toast.addEventListener('transitionend', () => toast.remove());
    }, 5000);

    // Remove toast on close button click
    toast.querySelector('.close-btn').addEventListener('click', () => {
        toast.classList.add('fade-out');
        toast.addEventListener('transitionend', () => toast.remove());
    });
}
