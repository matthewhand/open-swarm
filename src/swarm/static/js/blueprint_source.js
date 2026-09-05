// Inline save for /blueprint-library/<id>/source/ (REQ-211).
(function () {
  const editor = document.getElementById('os-source-editor');
  const saveBtn = document.getElementById('os-source-save');
  const status = document.getElementById('os-source-status');
  if (!editor || !saveBtn) return;

  function csrfToken() {
    const input = document.querySelector('[name=csrfmiddlewaretoken]');
    if (input && input.value) return input.value;
    const match = document.cookie
      .split('; ')
      .find(function (row) { return row.startsWith('csrftoken='); });
    return match ? decodeURIComponent(match.split('=').slice(1).join('=')) : '';
  }

  function setStatus(text, isError) {
    if (!status) return;
    status.textContent = text || '';
    status.classList.toggle('text-danger', Boolean(isError));
    status.classList.toggle('text-muted', !isError);
  }

  saveBtn.addEventListener('click', async function () {
    const id = editor.getAttribute('data-blueprint-id') || '';
    const file = editor.getAttribute('data-file') || '';
    if (!id) {
      setStatus('Missing blueprint id.', true);
      return;
    }
    saveBtn.disabled = true;
    setStatus('Saving…', false);
    try {
      const body = { content: editor.value };
      if (file) body.file = file;
      const response = await fetch(
        '/v1/blueprints/' + encodeURIComponent(id) + '/source/',
        {
          method: 'PUT',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken(),
          },
          credentials: 'same-origin',
          body: JSON.stringify(body),
        }
      );
      const data = await response.json().catch(function () { return {}; });
      if (!response.ok) {
        setStatus(data.error || ('Save failed (' + response.status + ').'), true);
        return;
      }
      if (typeof data.content === 'string') {
        editor.value = data.content;
      }
      setStatus('Saved. Reloaded as the updated blueprint.', false);
    } catch (err) {
      setStatus('Save failed. Prior source is unchanged.', true);
    } finally {
      saveBtn.disabled = false;
    }
  });
})();
