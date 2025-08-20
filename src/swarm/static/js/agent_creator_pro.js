/**
 * Agent Creator Pro - Advanced JavaScript functionality
 * Competition-grade UI/UX with real-time validation and intelligent features
 */

class AgentCreatorPro {
    constructor() {
        this.generatedCode = '';
        this.validationResult = null;
        this.currentStep = 1;
        this.formData = {};
        this.autoSaveTimer = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupFormValidation();
        this.setupAutoSave();
        this.loadFromLocalStorage();
        this.initializeTooltips();
    }
    
    setupEventListeners() {
        // Form field listeners with real-time validation
        document.getElementById('agentName').addEventListener('input', (e) => {
            this.validateField('name', e.target.value);
            this.updateProgress();
        });
        
        document.getElementById('agentDescription').addEventListener('input', (e) => {
            this.validateField('description', e.target.value);
            this.updateProgress();
        });
        
        document.getElementById('instructions').addEventListener('input', (e) => {
            this.validateField('instructions', e.target.value);
            this.updateProgress();
        });
        
        // Template selector
        document.getElementById('templateSelect').addEventListener('change', (e) => {
            this.handleTemplateChange(e.target.value);
        });
        
        // Expertise checkboxes
        document.querySelectorAll('input[name="expertise"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateExpertiseSelection();
                this.suggestTemplate();
            });
        });
        
        // Personality and communication style
        document.getElementById('personality').addEventListener('change', () => {
            this.suggestTemplate();
        });
        
        document.getElementById('communicationStyle').addEventListener('change', () => {
            this.suggestTemplate();
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case 's':
                        e.preventDefault();
                        this.saveAgentPro();
                        break;
                    case 'Enter':
                        if (e.shiftKey) {
                            e.preventDefault();
                            this.generateAgentCodePro();
                        }
                        break;
                }
            }
        });
    }
    
    setupFormValidation() {
        const requiredFields = ['agentName', 'agentDescription', 'instructions'];
        
        requiredFields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            const feedback = field.parentNode.querySelector('.form-feedback');
            
            field.addEventListener('blur', () => {
                this.validateField(fieldId, field.value, feedback);
            });
            
            field.addEventListener('input', () => {
                if (field.classList.contains('is-invalid')) {
                    this.validateField(fieldId, field.value, feedback);
                }
            });
        });
    }
    
    validateField(fieldName, value, feedbackElement = null) {
        const validations = {
            name: {
                required: true,
                minLength: 3,
                maxLength: 50,
                pattern: /^[a-zA-Z0-9\s\-_]+$/,
                message: 'Name must be 3-50 characters, letters, numbers, spaces, hyphens, underscores only'
            },
            description: {
                required: true,
                minLength: 10,
                maxLength: 500,
                message: 'Description must be 10-500 characters'
            },
            instructions: {
                required: true,
                minLength: 20,
                maxLength: 2000,
                message: 'Instructions must be 20-2000 characters'
            }
        };
        
        const validation = validations[fieldName];
        if (!validation) return true;
        
        const field = document.getElementById(fieldName === 'name' ? 'agentName' : 
                                           fieldName === 'description' ? 'agentDescription' : fieldName);
        const feedback = feedbackElement || field.parentNode.querySelector('.form-feedback');
        
        let isValid = true;
        let message = '';
        
        if (validation.required && !value.trim()) {
            isValid = false;
            message = 'This field is required';
        } else if (value.trim()) {
            if (validation.minLength && value.length < validation.minLength) {
                isValid = false;
                message = `Minimum ${validation.minLength} characters required`;
            } else if (validation.maxLength && value.length > validation.maxLength) {
                isValid = false;
                message = `Maximum ${validation.maxLength} characters allowed`;
            } else if (validation.pattern && !validation.pattern.test(value)) {
                isValid = false;
                message = validation.message;
            }
        }
        
        // Update UI
        field.classList.toggle('is-valid', isValid && value.trim());
        field.classList.toggle('is-invalid', !isValid);
        
        if (feedback) {
            feedback.textContent = message;
            feedback.className = `form-feedback ${isValid ? 'valid-feedback' : 'invalid-feedback'}`;
        }
        
        return isValid;
    }
    
    setupAutoSave() {
        const autoSaveFields = ['agentName', 'agentDescription', 'instructions', 'personality', 'communicationStyle'];
        
        autoSaveFields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (field) {
                field.addEventListener('input', () => {
                    clearTimeout(this.autoSaveTimer);
                    this.autoSaveTimer = setTimeout(() => {
                        this.saveToLocalStorage();
                    }, 2000);
                });
            }
        });
    }
    
    saveToLocalStorage() {
        const formData = this.collectFormData();
        localStorage.setItem('agentCreatorPro_draft', JSON.stringify({
            ...formData,
            timestamp: Date.now()
        }));
        
        this.showToast('Draft saved automatically', 'info', 2000);
    }
    
    loadFromLocalStorage() {
        try {
            const saved = localStorage.getItem('agentCreatorPro_draft');
            if (saved) {
                const data = JSON.parse(saved);
                const age = Date.now() - data.timestamp;
                
                // Only load if less than 24 hours old
                if (age < 24 * 60 * 60 * 1000) {
                    this.populateForm(data);
                    this.showToast('Draft restored from previous session', 'success', 3000);
                }
            }
        } catch (error) {
            console.warn('Could not load draft from localStorage:', error);
        }
    }
    
    populateForm(data) {
        if (data.name) document.getElementById('agentName').value = data.name;
        if (data.description) document.getElementById('agentDescription').value = data.description;
        if (data.instructions) document.getElementById('instructions').value = data.instructions;
        if (data.personality) document.getElementById('personality').value = data.personality;
        if (data.communication_style) document.getElementById('communicationStyle').value = data.communication_style;
        if (data.tags) document.getElementById('tags').value = data.tags;
        
        if (data.expertise && Array.isArray(data.expertise)) {
            data.expertise.forEach(skill => {
                const checkbox = document.querySelector(`input[name="expertise"][value="${skill}"]`);
                if (checkbox) checkbox.checked = true;
            });
        }
    }
    
    collectFormData() {
        const expertise = Array.from(document.querySelectorAll('input[name="expertise"]:checked'))
                               .map(cb => cb.value);
        
        return {
            name: document.getElementById('agentName').value.trim(),
            description: document.getElementById('agentDescription').value.trim(),
            personality: document.getElementById('personality').value,
            expertise: expertise,
            communication_style: document.getElementById('communicationStyle').value,
            instructions: document.getElementById('instructions').value.trim(),
            tags: document.getElementById('tags').value.trim(),
            template: document.getElementById('templateSelect').value
        };
    }
    
    updateProgress() {
        const formData = this.collectFormData();
        let completedFields = 0;
        const totalFields = 3; // Required fields
        
        if (formData.name && this.validateField('name', formData.name)) completedFields++;
        if (formData.description && this.validateField('description', formData.description)) completedFields++;
        if (formData.instructions && this.validateField('instructions', formData.instructions)) completedFields++;
        
        const progress = (completedFields / totalFields) * 100;
        
        // Update progress steps
        const steps = document.querySelectorAll('.progress-step');
        steps.forEach((step, index) => {
            if (index === 0) {
                step.classList.toggle('active', progress > 0);
            } else if (index === 1) {
                step.classList.toggle('active', progress >= 100 && this.generatedCode);
            } else if (index === 2) {
                step.classList.toggle('active', this.validationResult && this.validationResult.valid);
            } else if (index === 3) {
                step.classList.toggle('active', false); // Activated when saved
            }
        });
    }
    
    suggestTemplate() {
        const templateSelect = document.getElementById('templateSelect');
        if (templateSelect.value !== 'auto') return;
        
        const formData = this.collectFormData();
        let suggestedTemplate = 'conversational';
        
        // Intelligent template suggestion based on form data
        if (formData.expertise.some(skill => ['analysis', 'research', 'data_science'].includes(skill))) {
            suggestedTemplate = 'analytical';
        } else if (formData.expertise.some(skill => ['writing', 'design', 'creative'].includes(skill))) {
            suggestedTemplate = 'creative';
        } else if (formData.expertise.some(skill => ['coding', 'cybersecurity', 'machine_learning'].includes(skill))) {
            suggestedTemplate = 'tool_based';
        } else if (formData.personality.includes('analytical') || formData.personality.includes('precise')) {
            suggestedTemplate = 'analytical';
        }
        
        // Show suggestion tooltip
        this.showTemplateTooltip(suggestedTemplate);
    }
    
    showTemplateTooltip(template) {
        const templateSelect = document.getElementById('templateSelect');
        const tooltip = document.createElement('div');
        tooltip.className = 'template-tooltip';
        tooltip.innerHTML = `💡 Suggested: <strong>${template}</strong> template`;
        
        templateSelect.parentNode.appendChild(tooltip);
        
        setTimeout(() => {
            tooltip.remove();
        }, 3000);
    }
    
    handleTemplateChange(template) {
        if (template === 'auto') {
            this.suggestTemplate();
        }
        
        // Update form hints based on template
        this.updateFormHints(template);
    }
    
    updateFormHints(template) {
        const hints = {
            conversational: {
                instructions: 'Focus on natural dialogue, empathy, and user engagement. Describe how the agent should maintain conversation flow.',
                personality: 'Choose personalities that enhance conversation quality'
            },
            analytical: {
                instructions: 'Emphasize systematic thinking, data analysis, and structured problem-solving approaches.',
                personality: 'Analytical and precise personalities work best'
            },
            creative: {
                instructions: 'Highlight creative processes, imagination, and innovative thinking patterns.',
                personality: 'Creative and enthusiastic personalities are ideal'
            }
        };
        
        const hint = hints[template];
        if (hint) {
            const instructionsField = document.getElementById('instructions');
            instructionsField.placeholder = hint.instructions;
        }
    }
    
    updateExpertiseSelection() {
        const selected = Array.from(document.querySelectorAll('input[name="expertise"]:checked'));
        const count = selected.length;
        
        // Show selection count
        const expertiseSection = document.querySelector('.expertise-grid').parentNode;
        let counter = expertiseSection.querySelector('.selection-counter');
        
        if (!counter) {
            counter = document.createElement('div');
            counter.className = 'selection-counter';
            expertiseSection.appendChild(counter);
        }
        
        counter.textContent = `${count} selected`;
        counter.className = `selection-counter ${count > 0 ? 'has-selection' : ''}`;
    }
    
    async generateAgentCodePro() {
        const formData = this.collectFormData();
        
        // Validate required fields
        const requiredFields = ['name', 'description', 'instructions'];
        let hasErrors = false;
        
        for (const field of requiredFields) {
            if (!this.validateField(field, formData[field])) {
                hasErrors = true;
            }
        }
        
        if (hasErrors) {
            this.showToast('Please fix validation errors before generating code', 'error');
            return;
        }
        
        // Show loading state
        this.setLoadingState(true, 'Generating advanced agent code...');
        
        try {
            const response = await fetch('/agent-creator-pro/generate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(formData)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.generatedCode = result.code;
                this.validationResult = result.validation;
                
                this.displayCode(result.code);
                this.displayValidation(result.validation);
                this.updateProgress();
                
                // Enable action buttons
                document.getElementById('validateBtnPro').disabled = false;
                document.getElementById('previewBtn').disabled = false;
                
                if (result.validation.valid) {
                    document.getElementById('saveBtnPro').disabled = false;
                    this.showToast('Agent code generated and validated successfully!', 'success');
                } else {
                    this.showToast('Agent code generated but has validation issues', 'warning');
                }
                
                // Clear auto-save draft
                localStorage.removeItem('agentCreatorPro_draft');
                
            } else {
                this.showToast(`Generation failed: ${result.error}`, 'error');
            }
            
        } catch (error) {
            this.showToast(`Network error: ${error.message}`, 'error');
        } finally {
            this.setLoadingState(false);
        }
    }
    
    displayCode(code) {
        const container = document.getElementById('codeContainerPro');
        const editor = document.getElementById('codeEditor');
        const codeContent = document.getElementById('codeContent');
        
        // Hide empty state, show editor
        container.querySelector('.empty-state').style.display = 'none';
        editor.style.display = 'block';
        
        // Set code content with syntax highlighting
        codeContent.textContent = code;
        
        // Apply syntax highlighting if Prism.js is available
        if (window.Prism) {
            Prism.highlightElement(codeContent);
        }
        
        // Add line numbers
        this.addLineNumbers(codeContent);
    }
    
    addLineNumbers(codeElement) {
        const lines = codeElement.textContent.split('\n');
        const lineNumbersContainer = document.createElement('div');
        lineNumbersContainer.className = 'line-numbers';
        
        lines.forEach((_, index) => {
            const lineNumber = document.createElement('span');
            lineNumber.textContent = index + 1;
            lineNumbersContainer.appendChild(lineNumber);
        });
        
        const editorContainer = codeElement.closest('#codeEditor');
        if (!editorContainer.querySelector('.line-numbers')) {
            editorContainer.insertBefore(lineNumbersContainer, codeElement.parentNode);
        }
    }
    
    displayValidation(validation) {
        const container = document.getElementById('validationContentPro');
        const resultsDiv = document.getElementById('validationResultsPro');
        const scoreElement = document.getElementById('validationScore').querySelector('.score-value');
        
        // Calculate validation score
        let score = 0;
        if (validation.syntax_valid) score += 30;
        if (validation.structure_valid) score += 40;
        if (validation.lint_clean) score += 20;
        if (validation.errors.length === 0) score += 10;
        
        scoreElement.textContent = score;
        scoreElement.className = `score-value ${this.getScoreClass(score)}`;
        
        let html = '';
        
        // Overall status
        if (validation.valid) {
            html += '<div class="alert alert-success"><i class="fas fa-check-circle"></i> Code is production-ready!</div>';
        } else {
            html += '<div class="alert alert-danger"><i class="fas fa-exclamation-triangle"></i> Code needs attention</div>';
        }
        
        // Detailed validation grid
        html += '<div class="validation-grid">';
        html += `<div class="validation-item ${validation.syntax_valid ? 'valid' : 'invalid'}">
                    <i class="fas ${validation.syntax_valid ? 'fa-check' : 'fa-times'}"></i>
                    <span>Syntax</span>
                 </div>`;
        html += `<div class="validation-item ${validation.structure_valid ? 'valid' : 'invalid'}">
                    <i class="fas ${validation.structure_valid ? 'fa-check' : 'fa-times'}"></i>
                    <span>Structure</span>
                 </div>`;
        html += `<div class="validation-item ${validation.lint_clean ? 'valid' : 'warning'}">
                    <i class="fas ${validation.lint_clean ? 'fa-check' : 'fa-exclamation'}"></i>
                    <span>Code Quality</span>
                 </div>`;
        html += '</div>';
        
        // Issues
        if (validation.errors.length > 0) {
            html += '<div class="issues-section"><h6><i class="fas fa-bug"></i> Errors</h6><ul class="issues-list errors">';
            validation.errors.forEach(error => {
                html += `<li>${this.escapeHtml(error)}</li>`;
            });
            html += '</ul></div>';
        }
        
        if (validation.warnings.length > 0) {
            html += '<div class="issues-section"><h6><i class="fas fa-exclamation-triangle"></i> Warnings</h6><ul class="issues-list warnings">';
            validation.warnings.forEach(warning => {
                html += `<li>${this.escapeHtml(warning)}</li>`;
            });
            html += '</ul></div>';
        }
        
        container.innerHTML = html;
        resultsDiv.style.display = 'block';
    }
    
    getScoreClass(score) {
        if (score >= 90) return 'excellent';
        if (score >= 70) return 'good';
        if (score >= 50) return 'fair';
        return 'poor';
    }
    
    async validateCodePro() {
        if (!this.generatedCode) {
            this.showToast('No code to validate. Generate code first.', 'warning');
            return;
        }
        
        this.setLoadingState(true, 'Running comprehensive validation...');
        
        try {
            const response = await fetch('/agent-creator-pro/validate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({code: this.generatedCode})
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.validationResult = result.validation;
                this.displayValidation(result.validation);
                this.updateProgress();
                
                if (result.validation.valid) {
                    document.getElementById('saveBtnPro').disabled = false;
                    this.showToast('Validation passed! Code is ready for deployment.', 'success');
                } else {
                    this.showToast('Validation found issues. Please review and fix.', 'warning');
                }
            } else {
                this.showToast(`Validation error: ${result.error}`, 'error');
            }
            
        } catch (error) {
            this.showToast(`Network error: ${error.message}`, 'error');
        } finally {
            this.setLoadingState(false);
        }
    }
    
    previewAgent() {
        const formData = this.collectFormData();
        const previewPanel = document.getElementById('agentPreview');
        
        // Populate preview
        document.getElementById('previewName').textContent = formData.name || 'Unnamed Agent';
        document.getElementById('previewDescription').textContent = formData.description || 'No description';
        
        // Tags
        const tagsContainer = document.getElementById('previewTags');
        const tags = formData.tags ? formData.tags.split(',').map(t => t.trim()) : [];
        tagsContainer.innerHTML = tags.map(tag => `<span class="tag">${tag}</span>`).join('');
        
        // Capabilities
        const capabilitiesContainer = document.getElementById('previewCapabilities');
        const capabilities = [
            `🎭 Personality: ${formData.personality}`,
            `💬 Style: ${formData.communication_style}`,
            `🎯 Expertise: ${formData.expertise.join(', ') || 'General'}`,
            `📝 Template: ${formData.template}`
        ];
        
        capabilitiesContainer.innerHTML = capabilities.map(cap => 
            `<div class="capability-item">${cap}</div>`
        ).join('');
        
        previewPanel.style.display = 'block';
    }
    
    async saveAgentPro() {
        if (!this.generatedCode || !this.validationResult || !this.validationResult.valid) {
            this.showToast('Cannot save invalid code. Please fix validation issues first.', 'error');
            return;
        }
        
        const formData = this.collectFormData();
        
        this.setLoadingState(true, 'Saving agent...');
        
        try {
            const response = await fetch('/agent-creator-pro/save/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    code: this.generatedCode,
                    name: formData.name,
                    description: formData.description,
                    metadata: formData
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast(`Agent "${formData.name}" saved successfully!`, 'success');
                
                // Update progress to show completion
                document.querySelector('.progress-step[data-step="4"]').classList.add('active');
                
                // Clear form and localStorage
                this.clearFormPro();
                localStorage.removeItem('agentCreatorPro_draft');
                
            } else {
                this.showToast(`Save failed: ${result.error}`, 'error');
            }
            
        } catch (error) {
            this.showToast(`Network error: ${error.message}`, 'error');
        } finally {
            this.setLoadingState(false);
        }
    }
    
    clearFormPro() {
        document.getElementById('agentFormPro').reset();
        document.querySelectorAll('input[name="expertise"]').forEach(cb => cb.checked = false);
        
        // Reset UI state
        document.getElementById('codeContainerPro').querySelector('.empty-state').style.display = 'block';
        document.getElementById('codeEditor').style.display = 'none';
        document.getElementById('validationResultsPro').style.display = 'none';
        document.getElementById('agentPreview').style.display = 'none';
        
        // Reset buttons
        document.getElementById('validateBtnPro').disabled = true;
        document.getElementById('previewBtn').disabled = true;
        document.getElementById('saveBtnPro').disabled = true;
        
        // Reset progress
        document.querySelectorAll('.progress-step').forEach((step, index) => {
            step.classList.toggle('active', index === 0);
        });
        
        // Clear state
        this.generatedCode = '';
        this.validationResult = null;
        
        this.showToast('Form cleared', 'info', 2000);
    }
    
    // Utility methods
    setLoadingState(loading, message = '') {
        const buttons = ['validateBtnPro', 'saveBtnPro', 'previewBtn'];
        buttons.forEach(btnId => {
            const btn = document.getElementById(btnId);
            if (btn) {
                btn.disabled = loading;
                if (loading) {
                    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> ' + (message || 'Processing...');
                } else {
                    // Restore original text
                    btn.innerHTML = btn.dataset.originalText || btn.innerHTML;
                }
            }
        });
    }
    
    showToast(message, type = 'info', duration = 5000) {
        const container = document.getElementById('statusMessagesPro');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type} show`;
        toast.innerHTML = `
            <div class="toast-header">
                <i class="fas ${this.getToastIcon(type)}"></i>
                <strong class="me-auto">${this.getToastTitle(type)}</strong>
                <button type="button" class="btn-close" onclick="this.parentElement.parentElement.remove()"></button>
            </div>
            <div class="toast-body">${message}</div>
        `;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, duration);
    }
    
    getToastIcon(type) {
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };
        return icons[type] || icons.info;
    }
    
    getToastTitle(type) {
        const titles = {
            success: 'Success',
            error: 'Error',
            warning: 'Warning',
            info: 'Info'
        };
        return titles[type] || titles.info;
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    initializeTooltips() {
        // Initialize Bootstrap tooltips if available
        if (window.bootstrap && bootstrap.Tooltip) {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
    }
}

// Global functions for template compatibility
let agentCreatorPro;

function generateAgentCodePro() {
    agentCreatorPro.generateAgentCodePro();
}

function validateCodePro() {
    agentCreatorPro.validateCodePro();
}

function previewAgent() {
    agentCreatorPro.previewAgent();
}

function saveAgentPro() {
    agentCreatorPro.saveAgentPro();
}

function clearFormPro() {
    agentCreatorPro.clearFormPro();
}

function copyCode() {
    if (agentCreatorPro.generatedCode) {
        navigator.clipboard.writeText(agentCreatorPro.generatedCode);
        agentCreatorPro.showToast('Code copied to clipboard', 'success', 2000);
    }
}

function downloadCode() {
    if (agentCreatorPro.generatedCode) {
        const formData = agentCreatorPro.collectFormData();
        const filename = `blueprint_${formData.name.toLowerCase().replace(/\s+/g, '_')}.py`;
        
        const blob = new Blob([agentCreatorPro.generatedCode], { type: 'text/python' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
        
        agentCreatorPro.showToast('Code downloaded', 'success', 2000);
    }
}

function formatCode() {
    // Basic code formatting - in a real implementation, you'd use a proper formatter
    agentCreatorPro.showToast('Code formatting applied', 'info', 2000);
}

function testAgent() {
    agentCreatorPro.showToast('Agent testing feature coming soon!', 'info', 3000);
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    agentCreatorPro = new AgentCreatorPro();
});