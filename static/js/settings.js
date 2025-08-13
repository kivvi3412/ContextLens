// Settings page JavaScript
class SettingsManager {
    constructor() {
        this.init();
        this.bindEvents();
    }

    static getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    init() {
        // Modal elements
        this.apiConfigModal = document.getElementById('apiConfigModal');
        this.templateModal = document.getElementById('templateModal');
        this.analysisConfigModal = document.getElementById('analysisConfigModal');

        // Forms
        this.apiConfigForm = document.getElementById('apiConfigForm');
        this.templateForm = document.getElementById('templateForm');
        this.analysisConfigForm = document.getElementById('analysisConfigForm');

        // Buttons
        this.addApiConfigBtn = document.getElementById('addApiConfigBtn');
        this.addTranslationTemplateBtn = document.getElementById('addTranslationTemplateBtn');
        this.addAnalysisTemplateBtn = document.getElementById('addAnalysisTemplateBtn');
        this.addSentenceTemplateBtn = document.getElementById('addSentenceTemplateBtn');
        this.editAnalysisConfigBtn = document.getElementById('editAnalysisConfigBtn');

        // Modal controls
        this.apiConfigModalTitle = document.getElementById('apiConfigModalTitle');
        this.templateModalTitle = document.getElementById('templateModalTitle');

        // Form fields
        this.templateTypeField = document.getElementById('templateType');

        // Toast container
        this.toastContainer = document.getElementById('toast-container');

        // State
        this.currentEditingId = null;
        this.currentEditingType = null;
    }

    bindEvents() {
        // Add buttons
        this.addApiConfigBtn.addEventListener('click', () => this.showApiConfigModal());
        this.addTranslationTemplateBtn.addEventListener('click', () => this.showTemplateModal('translation'));
        this.addAnalysisTemplateBtn.addEventListener('click', () => this.showTemplateModal('word_analysis'));
        if (this.addSentenceTemplateBtn) {
        this.addSentenceTemplateBtn.addEventListener('click', () => this.showTemplateModal('sentence_analysis'));
        }
        this.editAnalysisConfigBtn.addEventListener('click', () => this.showAnalysisConfigModal());

        // Form submissions
        this.apiConfigForm.addEventListener('submit', (e) => this.handleApiConfigSubmit(e));
        this.templateForm.addEventListener('submit', (e) => this.handleTemplateSubmit(e));
        this.analysisConfigForm.addEventListener('submit', (e) => this.handleAnalysisConfigSubmit(e));

        // Modal close buttons
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', (e) => this.closeModal(e.target.closest('.modal')));
        });

        // Cancel buttons
        document.getElementById('cancelApiConfigBtn').addEventListener('click', () => this.closeModal(this.apiConfigModal));
        document.getElementById('cancelTemplateBtn').addEventListener('click', () => this.closeModal(this.templateModal));
        document.getElementById('cancelAnalysisConfigBtn').addEventListener('click', () => this.closeModal(this.analysisConfigModal));

        // Click outside to close modal
        this.apiConfigModal.addEventListener('click', (e) => {
            if (e.target === this.apiConfigModal) this.closeModal(this.apiConfigModal);
        });
        this.templateModal.addEventListener('click', (e) => {
            if (e.target === this.templateModal) this.closeModal(this.templateModal);
        });
        this.analysisConfigModal.addEventListener('click', (e) => {
            if (e.target === this.analysisConfigModal) this.closeModal(this.analysisConfigModal);
        });

        // Card action buttons
        this.bindCardEvents();

        // Escape key to close modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal(document.querySelector('.modal.show'));
            }
        });
    }

    bindCardEvents() {
        // Bind events to existing cards
        this.bindApiConfigCards();
        this.bindTemplateCards();
    }

    bindApiConfigCards() {
        document.querySelectorAll('.config-card').forEach(card => {
            const configId = card.dataset.configId;

            // Edit button
            const editBtn = card.querySelector('.edit-config-btn');
            if (editBtn) {
                editBtn.addEventListener('click', () => this.editApiConfig(configId));
            }

            // Delete button
            const deleteBtn = card.querySelector('.delete-config-btn');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', () => this.deleteApiConfig(configId));
            }
        });
    }

    bindTemplateCards() {
        document.querySelectorAll('.template-card').forEach(card => {
            const templateId = card.dataset.templateId;

            // Edit button
            const editBtn = card.querySelector('.edit-template-btn');
            if (editBtn) {
                editBtn.addEventListener('click', () => this.editTemplate(templateId));
            }

            // Delete button
            const deleteBtn = card.querySelector('.delete-template-btn');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', () => this.deleteTemplate(templateId));
            }
        });
    }

    // API Configuration Methods
    showApiConfigModal(configId = null) {
        this.currentEditingId = configId;
        this.currentEditingType = 'config';

        const apiKeyField = document.getElementById('apiKey');

        if (configId) {
            this.apiConfigModalTitle.textContent = 'Edit API Configuration';
            // Make API key not required when editing
            apiKeyField.required = false;
            this.loadApiConfigData(configId);
        } else {
            this.apiConfigModalTitle.textContent = 'Add API Configuration';
            // Make API key required when adding new
            apiKeyField.required = true;
            apiKeyField.placeholder = 'Enter API key';
            this.apiConfigForm.reset();
        }

        this.showModal(this.apiConfigModal);
    }

    async loadApiConfigData(configId) {
        try {
            const data = await this.apiRequest(`/api/configs/${configId}/`);

            document.getElementById('configName').value = data.name;
            document.getElementById('baseUrl').value = data.base_url;
            document.getElementById('modelName').value = data.model_name;

            // Set API key field to show placeholder for existing keys
            const apiKeyField = document.getElementById('apiKey');
            if (data.has_api_key) {
                apiKeyField.placeholder = '••••••••••••••••••••';
                apiKeyField.value = '';
            } else {
                apiKeyField.placeholder = 'Enter API key';
                apiKeyField.value = '';
            }

        } catch (error) {
            console.error('Error loading API config:', error);
            this.showToast('Failed to load configuration data', 'error');
        }
    }

    async handleApiConfigSubmit(e) {
        e.preventDefault();

        const formData = new FormData(this.apiConfigForm);
        const data = Object.fromEntries(formData.entries());

        try {
            let result;
            if (this.currentEditingId) {
                result = await this.apiRequest(`/api/configs/${this.currentEditingId}/`, {
                    method: 'PUT',
                    body: JSON.stringify(data)
                });
            } else {
                result = await this.apiRequest('/api/configs/', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
            }

            this.showToast(result.message, 'success');
            this.closeModal(this.apiConfigModal);
            this.refreshPage();

        } catch (error) {
            console.error('Error saving API config:', error);
            this.showToast(error.message, 'error');
        }
    }

    async editApiConfig(configId) {
        this.showApiConfigModal(configId);
    }

    async deleteApiConfig(configId) {
        if (!confirm('Are you sure you want to delete this API configuration? This action cannot be undone.')) {
            return;
        }

        try {
            const result = await this.apiRequest(`/api/configs/${configId}/`, {
                method: 'DELETE'
            });

            this.showToast(result.message, 'success');
            this.refreshPage();

        } catch (error) {
            console.error('Error deleting API config:', error);
            this.showToast(error.message, 'error');
        }
    }

    // Template Methods
    showTemplateModal(templateType = null, templateId = null) {
        this.currentEditingId = templateId;
        this.currentEditingType = 'template';

        if (templateId) {
            this.templateModalTitle.textContent = 'Edit Template';
            this.templateTypeField.disabled = true; // Disable when editing
            this.loadTemplateData(templateId);
        } else {
            this.templateModalTitle.textContent = 'Add Template';
            this.templateForm.reset();
            if (templateType) {
                this.templateTypeField.value = templateType;
                this.templateTypeField.disabled = false; // Keep enabled for new templates with pre-selected type
            } else {
                this.templateTypeField.disabled = false; // Enable for new templates
            }
        }

        this.showModal(this.templateModal);
    }

    async loadTemplateData(templateId) {
        try {
            const data = await this.apiRequest(`/api/templates/${templateId}/`);

            document.getElementById('templateName').value = data.name;
            document.getElementById('templateType').value = data.template_type;
            document.getElementById('apiConfigSelect').value = data.api_config_id;
            document.getElementById('reasoningEffort').value = data.reasoning_effort;
            document.getElementById('isActive').checked = data.is_active;
            document.getElementById('promptText').value = data.prompt_text;

            // Disable template type field when editing
            this.templateTypeField.disabled = true;

        } catch (error) {
            console.error('Error loading template:', error);
            this.showToast('Failed to load template data', 'error');
        }
    }

    async handleTemplateSubmit(e) {
        e.preventDefault();

        const formData = new FormData(this.templateForm);
        const data = Object.fromEntries(formData.entries());

        // Handle disabled template_type field - get value directly from element
        if (this.templateTypeField.disabled) {
            data.template_type = this.templateTypeField.value;
        }

        // Convert checkbox to boolean
        data.is_active = document.getElementById('isActive').checked;

        // Debug log to check data
        console.log('Submitting template data:', data);

        try {
            let result;
            if (this.currentEditingId) {
                result = await this.apiRequest(`/api/templates/${this.currentEditingId}/`, {
                    method: 'PUT',
                    body: JSON.stringify(data)
                });
            } else {
                result = await this.apiRequest('/api/templates/', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
            }

            this.showToast(result.message, 'success');
            this.closeModal(this.templateModal);
            this.refreshPage();

        } catch (error) {
            console.error('Error saving template:', error);
            this.showToast(error.message, 'error');
        }
    }

    async editTemplate(templateId) {
        this.showTemplateModal(null, templateId);
    }

    async deleteTemplate(templateId) {
        if (!confirm('Are you sure you want to delete this template? This action cannot be undone.')) {
            return;
        }

        try {
            const result = await this.apiRequest(`/api/templates/${templateId}/`, {
                method: 'DELETE'
            });

            this.showToast(result.message, 'success');
            this.refreshPage();

        } catch (error) {
            console.error('Error deleting template:', error);
            this.showToast(error.message, 'error');
        }
    }

    // Analysis Configuration Methods
    showAnalysisConfigModal() {
        this.loadAnalysisConfigData();
        this.showModal(this.analysisConfigModal);
    }

    async loadAnalysisConfigData() {
        try {
            const data = await this.apiRequest('/api/analysis-config/');
            
            document.getElementById('wordGroupThreshold').value = data.word_group_threshold;
            
            // Update the preview text
            const thresholdPreview = document.getElementById('thresholdPreview');
            if (thresholdPreview) {
                thresholdPreview.textContent = data.word_group_threshold;
            }
            const thresholdPreview2 = document.getElementById('thresholdPreview2');
            if (thresholdPreview2) {
                thresholdPreview2.textContent = data.word_group_threshold;
            }

        } catch (error) {
            console.error('Error loading analysis config:', error);
            this.showToast('Failed to load analysis configuration', 'error');
        }
    }

    async handleAnalysisConfigSubmit(e) {
        e.preventDefault();

        const formData = new FormData(this.analysisConfigForm);
        const data = Object.fromEntries(formData.entries());

        // Convert to integer
        data.word_group_threshold = parseInt(data.word_group_threshold);

        try {
            const result = await this.apiRequest('/api/analysis-config/', {
                method: 'POST',
                body: JSON.stringify(data)
            });

            this.showToast(result.message, 'success');
            this.closeModal(this.analysisConfigModal);
            this.refreshPage();

        } catch (error) {
            console.error('Error saving analysis config:', error);
            this.showToast(error.message, 'error');
        }
    }

    // Modal Methods
    showModal(modal) {
        modal.classList.remove('hidden');
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';

        // Focus first input field
        const firstInput = modal.querySelector('input, select, textarea');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    }

    closeModal(modal) {
        if (!modal) return;

        modal.classList.remove('show');
        setTimeout(() => {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
        }, 300);

        // Reset form and state
        const form = modal.querySelector('form');
        if (form) form.reset();

        this.currentEditingId = null;
        this.currentEditingType = null;

        // Re-enable template type field
        if (this.templateTypeField) {
            this.templateTypeField.disabled = false;
        }
    }

    // Utility Methods
    showToast(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        this.toastContainer.appendChild(toast);

        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 10);

        // Auto remove
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, duration);

        // Click to dismiss
        toast.addEventListener('click', () => {
            toast.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        });
    }

    refreshPage() {
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }

    async apiRequest(url, options = {}) {
        const csrftoken = SettingsManager.getCookie('csrftoken');

        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
                'X-Requested-With': 'XMLHttpRequest'
            }
        };

        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };

        const response = await fetch(url, mergedOptions);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        return response.json();
    }
}

// Initialize settings manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.settingsManager = new SettingsManager();
    console.log('Settings Manager initialized successfully');
});

// Export for potential module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SettingsManager;
}