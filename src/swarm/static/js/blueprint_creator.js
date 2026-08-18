// Blueprint creator page logic (loaded via {% static %} from blueprint_creator.html).
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('blueprintCreatorForm');
    const createButton = document.getElementById('createButton');
    
    // Check ComfyUI status on page load
    checkComfyUIStatus();
    
    // Toggle avatar options visibility
    const avatarCheckbox = document.getElementById('generate_avatar');
    if (avatarCheckbox) {
        avatarCheckbox.addEventListener('change', function() {
            const avatarOptions = document.getElementById('avatarOptions');
            if (this.checked) {
                avatarOptions.classList.remove('d-none');
            } else {
                avatarOptions.classList.add('d-none');
            }
        });
    }
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Show loading modal
        const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
        loadingModal.show();
        
        // Disable button
        createButton.disabled = true;
        createButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Generating...';
        
        // Collect form data
        const formData = new FormData(form);
        const postUrl = form.getAttribute('action') || form.dataset.createUrl || window.location.pathname;

        // Submit form
        fetch(postUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            }
        })
        .then(response => response.json())
        .then(data => {
            loadingModal.hide();
            
            if (data.success) {
                // Show success modal with blueprint details
                showSuccessModal(data.blueprint);
            } else {
                showError(data.error || 'An error occurred while creating the blueprint');
            }
        })
        .catch(error => {
            loadingModal.hide();
            console.error('Error:', error);
            showError('An error occurred while creating the blueprint');
        })
        .finally(() => {
            // Re-enable button
            createButton.disabled = false;
            createButton.innerHTML = '<i class="fas fa-magic me-1"></i>Generate Blueprint';
        });
    });
});

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text == null ? '' : String(text);
    return div.innerHTML;
}

function showSuccessModal(blueprint) {
    const previewDiv = document.getElementById('blueprintPreview');
    const tags = Array.isArray(blueprint.tags) ? blueprint.tags : [];
    previewDiv.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h6>Blueprint Details</h6>
                <ul class="list-unstyled">
                    <li><strong>Name:</strong> ${escapeHtml(blueprint.name)}</li>
                    <li><strong>Category:</strong> ${escapeHtml(blueprint.category)}</li>
                    <li><strong>Author:</strong> ${escapeHtml(blueprint.author)}</li>
                    <li><strong>Created:</strong> ${escapeHtml(blueprint.created_at)}</li>
                </ul>
            </div>
            <div class="col-md-6">
                <h6>Description</h6>
                <p class="text-muted">${escapeHtml(blueprint.description)}</p>
                ${tags.length > 0 ? `
                <h6>Tags</h6>
                <div>
                    ${tags.map(tag => `<span class="badge bg-light text-dark me-1">${escapeHtml(tag)}</span>`).join('')}
                </div>
                ` : ''}
            </div>
        </div>
    `;
    
    const successModal = new bootstrap.Modal(document.getElementById('successModal'));
    successModal.show();
}

function showError(message) {
    // You can implement a toast or alert here
    alert('Error: ' + message);
}

async function checkComfyUIStatus() {
    try {
        const response = await fetch('/blueprint-library/comfyui-status/');
        const status = await response.json();
        
        const avatarCheckbox = document.getElementById('generate_avatar');
        const avatarOptions = document.getElementById('avatarOptions');
        const comfyuiAlert = document.querySelector('.alert-info');
        
        if (avatarCheckbox && comfyuiAlert) {
            if (status.available) {
                avatarCheckbox.disabled = false;
                comfyuiAlert.innerHTML = '<i class="fas fa-check-circle me-2 text-success"></i><strong>ComfyUI Available:</strong> Avatar generation is ready to use.';
                comfyuiAlert.className = 'alert alert-success';
            } else {
                avatarCheckbox.disabled = true;
                comfyuiAlert.innerHTML = '<i class="fas fa-exclamation-triangle me-2 text-warning"></i><strong>ComfyUI Not Available:</strong> Avatar generation requires ComfyUI to be running and configured.';
                comfyuiAlert.className = 'alert alert-warning';
            }
        }
    } catch (error) {
        console.error('Error checking ComfyUI status:', error);
    }
}

function resetForm() {
    document.getElementById('blueprintCreatorForm').reset();
}
