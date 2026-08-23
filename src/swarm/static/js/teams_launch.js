// Team launcher page logic (loaded via {% static %} from teams_launch.html).
(function() {
  const sel = (id) => document.getElementById(id);
  const bpSelect = sel('blueprintSelect');
  const instruction = sel('instruction');
  const profileInput = sel('profileInput');
  const output = sel('output');
  const launchBtn = sel('launchBtn');
  const clearBtn = sel('clearBtn');
  const tokenInput = sel('tokenInput');
  const outputEmpty = sel('outputEmpty');
  const launchError = sel('launchError');

  // Show the output pre (hide the empty-state placeholder)
  function showOutput() {
    if (outputEmpty) outputEmpty.classList.add('os-hide');
    output.classList.remove('os-hide');
  }
  // Reset back to the empty-state placeholder
  function resetOutput() {
    output.textContent = '';
    output.classList.add('os-hide');
    if (outputEmpty) outputEmpty.classList.remove('os-hide');
  }
  // Inline validation instead of blocking alert()s
  function showError(msg) {
    if (!launchError) return;
    launchError.textContent = msg;
    launchError.classList.toggle('os-hide', !msg);
  }
  // Toggle the Launch button between idle and in-flight states
  function setLaunching(on) {
    launchBtn.disabled = on;
    const label = launchBtn.querySelector('.launch-label');
    const spin = launchBtn.querySelector('.launch-spinner');
    if (label) label.classList.toggle('os-hide', on);
    if (spin) spin.classList.toggle('os-hide', !on);
  }
  function setStatus(visible) {
    const statusEl = sel('streamStatus');
    if (statusEl) statusEl.classList.toggle('os-hide', !visible);
  }

  // Load/save token if present
  if (tokenInput) {
    try { tokenInput.value = localStorage.getItem('swarm_api_token') || ''; } catch {}
    tokenInput?.addEventListener('change', () => {
      try { localStorage.setItem('swarm_api_token', tokenInput.value.trim()); } catch {}
    });
  }

  async function loadBlueprints() {
    // Try richer endpoint first; fall back to /v1/models
    const endpoints = ['/v1/blueprints', '/v1/models'];
    let data = null;
    for (const ep of endpoints) {
      try {
        const res = await fetch(ep);
        if (!res.ok) continue;
        const json = await res.json();
        if (json && Array.isArray(json.data)) { data = json.data; break; }
      } catch (e) { /* try next */ }
    }
    bpSelect.innerHTML = '';
    if (!data || !data.length) {
      bpSelect.innerHTML = '<option disabled selected>No blueprints found</option>';
      return;
    }
    for (const item of data) {
      const id = item.id || item.name;
      const name = item.name || id;
      const opt = document.createElement('option');
      opt.value = id;
      opt.textContent = `${name}`;
      bpSelect.appendChild(opt);
    }
    // Deep-link preselect: /teams/launch/?blueprint=<id> (linked from the
    // blueprint library cards). Unknown ids are ignored so the first
    // option stays selected.
    try {
      const requested = new URLSearchParams(window.location.search).get('blueprint');
      if (requested) {
        const match = Array.from(bpSelect.options).find((o) => o.value === requested);
        if (match) bpSelect.value = requested;
      }
    } catch (e) { /* query param parsing is best-effort */ }
  }

  function append(text) {
    showOutput();
    output.textContent += text;
    // auto-scroll
    output.scrollTop = output.scrollHeight;
  }

  function appendLine(text) { append(text + '\n'); }

  async function launch() {
    const model = bpSelect.value;
    const task = instruction.value.trim();
    const profile = profileInput.value.trim();
    if (!model) { showError('Select a team blueprint to launch.'); bpSelect.focus(); return; }
    if (!task) { showError('Enter a task or instruction for the team.'); instruction.focus(); return; }
    showError('');

    setLaunching(true);
    append(`\n--- Launching ${model} ---\n`);
    setStatus(true);

    const body = {
      model,
      messages: [{ role: 'user', content: task }],
      stream: true,
      params: profile ? { llmProfile: profile } : undefined,
    };

    const headers = { 'Content-Type': 'application/json' };
    // Optional bearer token
    let token = '';
    try { token = (tokenInput && tokenInput.value) || localStorage.getItem('swarm_api_token') || ''; } catch {}
    if (token) headers['Authorization'] = `Bearer ${token.trim()}`;

    let res;
    try {
      res = await fetch('/v1/chat/completions', {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      });
    } catch (e) {
      appendLine(`Request error: ${e}`);
      setLaunching(false);
      setStatus(false);
      return;
    }
    if (!res.ok) {
      try {
        const err = await res.json();
        appendLine(`HTTP ${res.status}: ${JSON.stringify(err)}`);
      } catch {
        appendLine(`HTTP ${res.status}`);
      }
      setLaunching(false);
      setStatus(false);
      return;
    }

    // Stream parse text/event-stream from fetch body
    try {
      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        // Split by SSE events
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';
        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith('data:')) continue;
          const payload = line.slice(5).trim();
          if (payload === '[DONE]') { appendLine('\n--- Completed ---'); break; }
          try {
            const json = JSON.parse(payload);
            const choice = json?.choices?.[0];
            const delta = choice?.delta;
            if (delta?.content) append(delta.content);
          } catch (e) {
            // Not JSON or error chunk
            appendLine(`\n[!] ${payload}`);
          }
        }
      }
    } catch (e) {
      appendLine(`Stream error: ${e}`);
    } finally {
      setLaunching(false);
      setStatus(false);
    }
  }

  clearBtn.addEventListener('click', () => { resetOutput(); showError(''); });
  launchBtn.addEventListener('click', launch);
  loadBlueprints();
})();
