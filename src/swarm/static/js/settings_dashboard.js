// Settings dashboard page logic (loaded via {% static %} from settings_dashboard.html).
// Server data arrives via Django json_script island #swarm-settings-data (not inline JS).
// Dynamic handlers use data-* + autoescape (not onclick JS strings): HTML entity
// decoding would otherwise reintroduce quotes into the handler source.
const settingsData = JSON.parse(document.getElementById("swarm-settings-data").textContent);

function toggleGroup(groupId) {
  const content = document.getElementById(`content-${groupId}`);
  const header = document.getElementById(`header-${groupId}`)
    || document.querySelector(`#group-${groupId} .group-header`);
  if (!content || !header) return;

  const expanded = content.classList.toggle('expanded');
  header.classList.toggle('expanded', expanded);
  header.setAttribute('aria-expanded', expanded ? 'true' : 'false');
}

function viewObject(groupId, settingName) {
  const setting = settingsData[groupId].settings[settingName];
  const modal = new bootstrap.Modal(document.getElementById('objectModal'));
  
  document.getElementById('objectContent').textContent = JSON.stringify(setting.value, null, 2);
  document.querySelector('#objectModal .modal-title').textContent = `${settingName} Configuration`;
  
  // Apply syntax highlighting if available
  if (window.Prism) {
    Prism.highlightElement(document.querySelector('#objectContent code'));
  }
  
  modal.show();
}

function copyObjectContent() {
  const content = document.getElementById('objectContent').textContent;
  navigator.clipboard.writeText(content);
  showToast('Object content copied to clipboard', 'success');
}

function copyEnvVar(envVar) {
  navigator.clipboard.writeText(envVar);
  showToast(`Environment variable "${envVar}" copied to clipboard`, 'success');
}

function exportSettings() {
  const data = {
    timestamp: new Date().toISOString(),
    settings: settingsData
  };
  
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `open-swarm-settings-${new Date().toISOString().split('T')[0]}.json`;
  a.click();
  URL.revokeObjectURL(url);
  
  showToast('Settings exported successfully', 'success');
}

function refreshSettings() {
  window.location.reload();
}

function setAlertMessage(container, message, kind) {
  container.replaceChildren();
  const alert = document.createElement('div');
  alert.className = `alert alert-${kind}`;
  alert.textContent = message;
  container.appendChild(alert);
}

async function viewEnvironment() {
  const modal = new bootstrap.Modal(document.getElementById('envModal'));
  const content = document.getElementById('envContent');

  content.replaceChildren();
  const loading = document.createElement('div');
  loading.className = 'text-center';
  loading.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading environment variables...';
  content.appendChild(loading);
  modal.show();
  
  try {
    const response = await fetch('/settings/environment/');
    const data = await response.json();
    
    if (data.success) {
      content.replaceChildren();
      const summary = document.createElement('div');
      summary.className = 'env-summary';
      summary.textContent = `Found ${data.count} environment variables`;
      content.appendChild(summary);

      const grid = document.createElement('div');
      grid.className = 'env-grid';

      for (const [key, value] of Object.entries(data.environment_variables)) {
        const item = document.createElement('div');
        item.className = 'env-item';

        const keyEl = document.createElement('div');
        keyEl.className = 'env-key';
        keyEl.textContent = key;

        const valueEl = document.createElement('div');
        valueEl.className = 'env-value';
        const code = document.createElement('code');
        code.textContent = value;
        valueEl.appendChild(code);

        const copyBtn = document.createElement('button');
        copyBtn.type = 'button';
        copyBtn.className = 'btn btn-sm btn-outline-secondary';
        copyBtn.setAttribute('aria-label', 'Copy environment variable name');
        copyBtn.dataset.envVar = key;
        copyBtn.innerHTML = '<i class="fas fa-copy" aria-hidden="true"></i>';
        copyBtn.addEventListener('click', () => copyEnvVar(key));

        item.appendChild(keyEl);
        item.appendChild(valueEl);
        item.appendChild(copyBtn);
        grid.appendChild(item);
      }

      content.appendChild(grid);
    } else {
      setAlertMessage(content, `Error: ${data.error}`, 'danger');
    }
  } catch (error) {
    setAlertMessage(content, `Network error: ${error.message}`, 'danger');
  }
}

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `alert alert-${type} position-fixed`;
  toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
  // textContent keeps the message XSS-safe; announce it for assistive tech.
  const assertive = type === 'danger' || type === 'error' || type === 'warning';
  toast.setAttribute('role', assertive ? 'alert' : 'status');
  toast.setAttribute('aria-live', assertive ? 'assertive' : 'polite');
  toast.setAttribute('aria-atomic', 'true');

  const text = document.createElement('span');
  text.textContent = message;
  toast.appendChild(text);

  const closeBtn = document.createElement('button');
  closeBtn.type = 'button';
  closeBtn.className = 'btn-close';
  closeBtn.setAttribute('aria-label', 'Close');
  closeBtn.addEventListener('click', () => toast.remove());
  toast.appendChild(closeBtn);

  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.remove();
  }, 5000);
}

const SETTINGS_DASHBOARD_ACTIONS = {
  'export-settings': exportSettings,
  'refresh-settings': refreshSettings,
  'view-environment': viewEnvironment,
  'copy-object-content': copyObjectContent,
};

document.querySelector('.settings-page')?.addEventListener('click', (event) => {
  const btn = event.target.closest('[data-action]');
  if (!btn || !event.currentTarget.contains(btn)) return;
  const handler = SETTINGS_DASHBOARD_ACTIONS[btn.getAttribute('data-action')];
  if (typeof handler === 'function') handler();
});

document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.group-header[data-group-id]').forEach((header) => {
    const groupId = header.dataset.groupId;
    header.addEventListener('click', () => toggleGroup(groupId));
    header.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        toggleGroup(groupId);
      }
    });
  });

  document.querySelectorAll('.btn-view-object').forEach((btn) => {
    btn.addEventListener('click', () => viewObject(btn.dataset.groupId, btn.dataset.settingName));
  });
  document.querySelectorAll('.btn-copy-env').forEach((btn) => {
    btn.addEventListener('click', () => copyEnvVar(btn.dataset.envVar));
  });

  const firstGroup = document.querySelector('.settings-group');
  if (firstGroup) {
    const groupId = firstGroup.id.replace('group-', '');
    toggleGroup(groupId);
  }
});
