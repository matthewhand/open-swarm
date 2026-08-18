// Blueprint library page logic (loaded via {% static %} from blueprint_library.html).
// Client-side page size for "All Blueprints" to avoid card explosion.
const BP_PAGE_SIZE = 12;
let bpVisibleLimit = BP_PAGE_SIZE;

function applyBlueprintVisibility() {
    const input = document.getElementById('bpSearch');
    const q = input ? input.value.trim().toLowerCase() : '';
    const items = Array.from(document.querySelectorAll('#allBlueprintsGrid .bp-grid-item'));
    let matchCount = 0;
    let rendered = 0;
    items.forEach(el => {
        const match = !q || (el.dataset.bpName || '').includes(q);
        if (!match) {
            el.style.display = 'none';
            return;
        }
        matchCount++;
        if (rendered < bpVisibleLimit) {
            el.style.display = '';
            rendered++;
        } else {
            el.style.display = 'none';
        }
    });
    const countEl = document.getElementById('bpSearchCount');
    if (countEl) {
        countEl.textContent = q
            ? matchCount + ' match' + (matchCount === 1 ? '' : 'es')
            : (matchCount ? matchCount + ' blueprints' : '');
    }
    const emptyEl = document.getElementById('bpSearchEmpty');
    const libraryEmpty = document.getElementById('bpLibraryEmpty');
    const noCatalog = items.length === 0;
    if (emptyEl) emptyEl.style.display = (!noCatalog && matchCount === 0) ? '' : 'none';
    if (libraryEmpty) libraryEmpty.style.display = noCatalog ? '' : 'none';
    const moreWrap = document.getElementById('bpShowMoreWrap');
    const meta = document.getElementById('bpPageMeta');
    if (moreWrap) {
        const hasMore = matchCount > bpVisibleLimit;
        moreWrap.style.display = hasMore || (matchCount > BP_PAGE_SIZE) ? '' : 'none';
        const btn = document.getElementById('bpShowMore');
        if (btn) {
            btn.style.display = hasMore ? '' : 'none';
            btn.textContent = hasMore
                ? 'Show more (' + Math.min(BP_PAGE_SIZE, matchCount - bpVisibleLimit) + ')'
                : 'Show more blueprints';
        }
        if (meta) {
            meta.textContent = matchCount
                ? 'Showing ' + Math.min(bpVisibleLimit, matchCount) + ' of ' + matchCount
                : '';
        }
    }
}

function showMoreBlueprints() {
    bpVisibleLimit += BP_PAGE_SIZE;
    applyBlueprintVisibility();
}

// Live client-side filter over the "All Blueprints" grid (by name).
function filterBlueprints() {
    bpVisibleLimit = BP_PAGE_SIZE;
    applyBlueprintVisibility();
}

function clearBlueprintSearch() {
    const input = document.getElementById('bpSearch');
    if (input) {
        input.value = '';
        input.focus();
    }
    filterBlueprints();
}

const BLUEPRINT_LIBRARY_ACTIONS = {
    'show-more-blueprints': showMoreBlueprints,
    'clear-blueprint-search': clearBlueprintSearch,
    'load-github-marketplace': loadGithubMarketplace,
};

document.addEventListener('click', (event) => {
    const btn = event.target.closest('[data-action]');
    if (!btn) return;
    const handler = BLUEPRINT_LIBRARY_ACTIONS[btn.getAttribute('data-action')];
    if (typeof handler === 'function') handler();
});

document.addEventListener('DOMContentLoaded', function() {
    const search = document.getElementById('bpSearch');
    if (search) search.addEventListener('input', filterBlueprints);
    filterBlueprints();

    // Fetch MCP compliance for all blueprints and update badges
    fetch('/blueprint-library/requirements/')
      .then(resp => resp.json())
      .then(data => {
          (data.blueprints || []).forEach(bp => {
              const el = document.getElementById(`mcp-status-${bp.id}`);
              if (!el) return;
              const comp = bp.compliance || {};
              const status = comp.status || 'partial';
              let cls = 'bg-secondary';
              let icon = 'fa-circle-question';
              let label = 'MCP: Unknown';
              let title = '';
              if (status === 'ok') {
                  cls = 'bg-success';
                  icon = 'fa-check';
                  label = 'MCP: OK';
              } else if (status === 'partial') {
                  cls = 'bg-warning text-dark';
                  icon = 'fa-triangle-exclamation';
                  const unresolved = (comp.unresolved_env || []).length;
                  const bpEnv = (comp.blueprint_env_missing || []).length;
                  label = `MCP: Partial`;
                  title = `Unresolved env: ${unresolved}, Missing blueprint env: ${bpEnv}`;
              } else if (status === 'missing') {
                  cls = 'bg-danger';
                  icon = 'fa-xmark';
                  const missing = (comp.missing_servers || []).length;
                  label = `MCP: Missing (${missing})`;
                  title = `Missing servers: ${(comp.missing_servers || []).join(', ')}`;
              }
              el.className = `badge ${cls}`;
              el.title = title;
              el.innerHTML = `<i class=\"fas ${icon} me-1\"></i>${label}`;
          });
      })
      .catch(() => {/* silently ignore; badges stay in checking state */});

    // Handle add/remove blueprint buttons
    document.querySelectorAll('.btn-add-blueprint, .btn-remove-blueprint').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled) return;

            const blueprintId = this.dataset.blueprintId;
            const action = this.classList.contains('btn-add-blueprint') ? 'add' : 'remove';
            const url = action === 'add' 
                ? `/blueprint-library/add/${blueprintId}/`
                : `/blueprint-library/remove/${blueprintId}/`;
            const originalHtml = this.innerHTML;
            this.disabled = true;
            this.setAttribute('aria-busy', 'true');
            this.innerHTML = action === 'add'
                ? '<i class="fas fa-spinner fa-spin me-1"></i>Adding…'
                : '<i class="fas fa-spinner fa-spin me-1"></i>Removing…';

            const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrf,
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update button state
                    const card = this.closest('.blueprint-card');
                    if (action === 'add') {
                        this.classList.remove('btn-outline-success', 'btn-add-blueprint');
                        this.classList.add('btn-outline-danger', 'btn-remove-blueprint');
                        this.innerHTML = '<i class="fas fa-minus me-1"></i>Remove';
                        card.classList.add('installed');
                    } else {
                        this.classList.remove('btn-outline-danger', 'btn-remove-blueprint');
                        this.classList.add('btn-outline-success', 'btn-add-blueprint');
                        this.innerHTML = '<i class="fas fa-plus me-1"></i>Add to Library';
                        card.classList.remove('installed');
                    }
                    
                    // Show notification
                    showNotification(data.message, 'success');
                } else {
                    this.innerHTML = originalHtml;
                    showNotification(data.error || 'An error occurred', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.innerHTML = originalHtml;
                showNotification('An error occurred while processing your request', 'error');
            })
            .finally(() => {
                this.disabled = false;
                this.removeAttribute('aria-busy');
            });
        });
    });
});

async function loadGithubMarketplace() {
    const container = document.getElementById('ghResults');
    const loading = document.getElementById('ghLoading');
    const empty = document.getElementById('ghEmpty');
    const emptyTitle = document.getElementById('ghEmptyTitle');
    const emptyHint = document.getElementById('ghEmptyHint');
    if (container) container.innerHTML = '';
    if (empty) empty.style.display = 'none';
    if (emptyTitle) emptyTitle.textContent = 'No marketplace results.';
    if (emptyHint) emptyHint.textContent = 'Try a different search or sort order.';
    if (loading) loading.style.display = '';
    try {
        const q = encodeURIComponent(document.getElementById('ghSearch')?.value || '');
        const sort = document.getElementById('ghSort')?.value || 'stars';
        const order = document.getElementById('ghOrder')?.value || 'desc';
        const type = document.getElementById('ghType')?.value || 'blueprints';
        const url = `/marketplace/github/${type}/?search=${q}&sort=${sort}&order=${order}`;
        const resp = await fetch(url);
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`);
        }
        const data = await resp.json();
        const items = data.data || [];
        if (container) {
            container.innerHTML = '';
            items.forEach(item => {
                const col = document.createElement('div');
                col.className = 'col-lg-4 col-md-6';
                col.innerHTML = renderGithubCard(item);
                container.appendChild(col);
            });
        }
        if (empty) empty.style.display = items.length ? 'none' : '';
    } catch (e) {
        console.error('GitHub marketplace load failed', e);
        if (emptyTitle) emptyTitle.textContent = 'Could not load marketplace results.';
        if (emptyHint) emptyHint.textContent = 'Check ENABLE_GITHUB_MARKETPLACE, GitHub rate limits, and your network, then try again.';
        if (empty) empty.style.display = '';
        if (container) container.innerHTML = '';
    } finally {
        if (loading) loading.style.display = 'none';
    }
}

function escapeHtml(text) {
    return String(text == null ? '' : text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/** Allow only http(s) repo links — escaped HTML alone does not stop javascript: hrefs. */
function safeHttpUrl(raw) {
    try {
        const u = new URL(String(raw || ''), window.location.origin);
        if (u.protocol === 'http:' || u.protocol === 'https:') {
            return u.href;
        }
    } catch (_) { /* ignore */ }
    return '';
}

function renderGithubCard(item) {
    const repo = escapeHtml(item.repo_full_name || 'unknown/repo');
    const repoHref = safeHttpUrl(item.repo_url);
    const repoUrlAttr = repoHref ? escapeHtml(repoHref) : '#';
    const title = escapeHtml(item.name || '(untitled)');
    const desc = escapeHtml(item.description || '');
    const tags = (item.tags || []).map(t => `<span class="badge bg-light text-dark tag-badge">${escapeHtml(t)}</span>`).join(' ');
    const kind = item.kind || 'blueprint';
    const kindBadge = kind === 'mcp' ? '<span class="badge bg-info text-dark ms-2">MCP</span>' : '';
    const files = item.file_count != null ? `${item.file_count} file${item.file_count === 1 ? '' : 's'}` : '';
    const lines = item.line_count != null ? `${item.line_count} lines` : '';
    const metrics = (files || lines) ? `<small class="text-muted">${[files, lines].filter(Boolean).join(' • ')}</small>` : '';
    const repoLink = repoHref
        ? `<a class="btn btn-outline-secondary btn-sm" href="${repoUrlAttr}" target="_blank" rel="noopener noreferrer">View Repo</a>`
        : `<span class="btn btn-outline-secondary btn-sm disabled" aria-disabled="true" title="No safe http(s) repo URL">View Repo</span>`;
    return `
    <div class="card h-100">
      <div class="card-body d-flex flex-column">
        <h5 class="card-title">${title} ${kindBadge}</h5>
        <p class="card-text">${desc}</p>
        <div class="mb-2">${tags}</div>
        <div class="mt-auto d-flex justify-content-between align-items-center gap-2">
          <div>
            <small class="text-muted d-block"><i class="fab fa-github me-1" aria-hidden="true"></i>${repo}</small>
            ${metrics}
          </div>
          ${repoLink}
        </div>
      </div>
    </div>`;
}

function showNotification(message, type) {
    const toast = document.getElementById('notificationToast');
    const toastMessage = document.getElementById('toastMessage');
    
    toastMessage.textContent = message;
    
    // Update toast styling based on type
    toast.className = `toast ${type === 'success' ? 'bg-success text-white' : 'bg-danger text-white'}`;
    
    // Show the toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}
