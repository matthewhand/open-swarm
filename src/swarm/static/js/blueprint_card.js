// Blueprint card actions (loaded via {% static %} from blueprint_library.html).
function previewBlueprint(blueprintId) {
    // Highlighted Python page — not the JSON /v1/blueprints/<id>/source API.
    window.open(`/blueprint-library/${encodeURIComponent(blueprintId)}/source/`, '_blank');
}

function launchBlueprint(blueprintId) {
    window.open(`/teams/launch/?blueprint=${encodeURIComponent(blueprintId)}`, '_blank');
}

async function generateAvatar(blueprintId, button) {
    const originalContent = button.innerHTML;
    try {
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        button.disabled = true;

        const style = prompt('Choose avatar style (professional, cartoon, anime, realistic, icon):', 'professional');
        if (!style) {
            return;
        }

        const formData = new FormData();
        formData.append('avatar_style', style);

        const response = await fetch(`/blueprint-library/generate-avatar/${encodeURIComponent(blueprintId)}/`, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            }
        });

        const result = await response.json();

        if (result.success) {
            location.reload();
        } else {
            alert('Error generating avatar: ' + result.error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error generating avatar');
    } finally {
        button.innerHTML = originalContent;
        button.disabled = false;
    }
}

document.addEventListener('click', function(event) {
    const previewBtn = event.target.closest('.btn-bp-preview');
    if (previewBtn) {
        previewBlueprint(previewBtn.dataset.blueprintId);
        return;
    }
    const launchBtn = event.target.closest('.btn-bp-launch');
    if (launchBtn) {
        launchBlueprint(launchBtn.dataset.blueprintId);
        return;
    }
    const avatarBtn = event.target.closest('.btn-bp-avatar');
    if (avatarBtn) {
        generateAvatar(avatarBtn.dataset.blueprintId, avatarBtn);
    }
});
