// ContextLens Main JavaScript
class ContextLens {
    constructor() {
        this.init();
        this.bindEvents();
    }

    // Utility methods
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

    static async apiRequest(url, options = {}) {
        const csrftoken = ContextLens.getCookie('csrftoken');

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

    init() {
        // DOM elements
        this.inputText = document.getElementById('inputText');
        this.translationOutput = document.getElementById('translationOutput');
        this.analysisOutput = document.getElementById('analysisOutput');
        this.translationLoading = document.getElementById('translationLoading');
        this.analysisLoading = document.getElementById('analysisLoading');
        this.translationThinking = document.getElementById('translationThinking');
        this.analysisThinking = document.getElementById('analysisThinking');
        this.translateBtn = document.getElementById('translateBtn');
        this.clearBtn = document.getElementById('clearBtn');

        // Collapsible sections
        this.translationHeader = document.getElementById('translationHeader');
        this.translationContent = document.getElementById('translationContent');
        this.translationCollapseBtn = document.getElementById('translationCollapseBtn');
        this.analysisHeader = document.getElementById('analysisHeader');
        this.analysisContent = document.getElementById('analysisContent');
        this.analysisCollapseBtn = document.getElementById('analysisCollapseBtn');

        // Toast container
        this.toastContainer = document.getElementById('toast-container');

        // State
        this.currentSelection = '';
        this.isTranslating = false;
        this.isAnalyzing = false;
        this.selectionTimeout = null; // For delayed text selection processing
        this.analysisBuffer = ''; // Buffer for streaming markdown content

        // Initialize collapsed states from localStorage
        this.loadCollapsedStates();
        
        // Load persisted input text
        this.loadInputText();
    }

    bindEvents() {
        // Button events
        this.translateBtn.addEventListener('click', () => this.translateText());
        this.clearBtn.addEventListener('click', () => this.clearAll());

        // Text selection events
        this.inputText.addEventListener('mouseup', (e) => this.handleTextSelection(e));
        this.inputText.addEventListener('keyup', (e) => this.handleTextSelection(e));
        
        // Save input text on change
        this.inputText.addEventListener('input', () => this.saveInputText());

        // Collapsible section events
        this.translationHeader.addEventListener('click', () => this.toggleSection('translation'));
        this.analysisHeader.addEventListener('click', () => this.toggleSection('analysis'));

        // Prevent default drag behavior on text selection
        this.inputText.addEventListener('selectstart', (e) => e.preventDefault);

        // Auto-resize textarea
        // Removed auto-resize to show full text
        // this.inputText.addEventListener('input', () => this.autoResizeTextarea());

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));

        // Initialize collapsed states from localStorage
        this.loadCollapsedStates();
    }

    handleTextSelection(e) {
        // Clear any existing timeout
        if (this.selectionTimeout) {
            clearTimeout(this.selectionTimeout);
        }

        // Delay the selection processing to handle double-click scenarios
        this.selectionTimeout = setTimeout(() => {
            const selection = window.getSelection();
            const selectedText = selection.toString().trim();
            const allText = this.inputText.value.trim();

            if (selectedText && selectedText !== this.currentSelection) {
                // 检查是否选中了超过90%的内容（防止全选误操作）
                const selectionRatio = selectedText.length / allText.length;
                if (selectionRatio > 0.9) {
                    console.log('检测到全选或近似全选，不进行分析');
                    return;
                }
                
                this.currentSelection = selectedText;
                this.analyzeSelection(selectedText);
            } else if (!selectedText && this.currentSelection) {
                // Only clear if there was a previous selection - preserve content on random clicks
                this.currentSelection = '';
            }
        }, 300); // 300ms delay to allow for double-click completion
    }

    async translateText() {
        const text = this.inputText.value.trim();
        if (!text) {
            this.showToast('Please enter some text to translate', 'warning');
            return;
        }

        if (this.isTranslating) return;

        this.isTranslating = true;
        this.translateBtn.disabled = true;
        this.translateBtn.textContent = 'Translating...';
        this.translationOutput.textContent = '';
        this.translationOutput.style.color = ''; // Reset color
        this.translationLoading.classList.remove('hidden');

        try {
            const response = await fetch('/api/stream-translate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({text})
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            await this.handleStreamResponse(response, this.translationOutput);
        } catch (error) {
            console.error('Translation error:', error);
            this.translationOutput.textContent = `Error: ${error.message}`;
            this.translationOutput.style.color = 'var(--error-color)';
            this.showToast(error.message, 'error');
        } finally {
            this.isTranslating = false;
            this.translateBtn.disabled = false;
            this.translateBtn.textContent = 'Translate';
            this.translationLoading.classList.add('hidden');
        }
    }

    async analyzeSelection(selectedText) {
        const allText = this.inputText.value.trim();
        if (!allText || this.isAnalyzing) return;

        // 判断是单词/短语还是句子
        const wordCount = selectedText.split(/\s+/).filter(word => word.length > 0).length;
        const isWord = wordCount <= 4;
        const analysisType = isWord ? '词汇分析' : '句子分析';
        
        // 更新分析标题
        const analysisTitle = document.querySelector('#analysisHeader h3');
        if (analysisTitle) {
            analysisTitle.textContent = `Word Analysis (${analysisType})`;
        }

        this.isAnalyzing = true;
        this.analysisOutput.innerHTML = ''; // Use innerHTML for markdown
        this.analysisOutput.style.color = ''; // Reset color
        this.analysisBuffer = ''; // Reset buffer
        this.analysisLoading.classList.remove('hidden');

        try {
            const response = await fetch('/api/stream-analyze/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    all_text: allText,
                    selected_text: selectedText
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            await this.handleStreamResponse(response, this.analysisOutput, true); // true for markdown
        } catch (error) {
            console.error('Analysis error:', error);
            this.analysisOutput.textContent = `Error: ${error.message}`;
            this.analysisOutput.style.color = 'var(--error-color)';
            this.showToast(error.message, 'error');
        } finally {
            this.isAnalyzing = false;
            this.analysisLoading.classList.add('hidden');
            
            // 恢复原始标题
            if (analysisTitle) {
                analysisTitle.textContent = 'Word Analysis';
            }
        }
    }

    async handleStreamResponse(response, outputElement, isMarkdown = false) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        // Get the appropriate thinking element
        const thinkingElement = isMarkdown ? this.analysisThinking : this.translationThinking;
        let hasStartedContent = false; // Track if we've started receiving content

        try {
            while (true) {
                const {done, value} = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, {stream: true});
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            console.log('Received data:', data); // Debug log
                            
                            if (data.type === 'thinking' && data.content) {
                                console.log('Processing thinking content:', data.content); // Debug log
                                // Display thinking content, accumulate the text
                                const currentText = thinkingElement.textContent || '';
                                thinkingElement.textContent = currentText + data.content;
                            } else if (data.type === 'thinking_done') {
                                console.log('Thinking done, starting new thinking section'); // Debug log
                                // Clear thinking content for next section
                                thinkingElement.textContent = '';
                            } else if (data.type === 'content' && data.content) {
                                // Clear thinking content when we start receiving actual content
                                if (!hasStartedContent) {
                                    thinkingElement.textContent = isMarkdown ? 'Analyzing...' : 'Translating...';
                                    hasStartedContent = true;
                                }
                                
                                if (isMarkdown) {
                                    // For analysis output, accumulate content and render as markdown
                                    this.analysisBuffer += data.content;
                                    // Parse and render markdown with custom renderer
                                    if (window.marked) {
                                        // Configure marked with normal spacing for better readability
                                        const renderer = new marked.Renderer();

                                        // Override paragraph rendering with normal margins
                                        renderer.paragraph = function (text) {
                                            return '<p style="margin-bottom:1em;line-height:1.5;">' + text + '</p>';
                                        };

                                        // Override list rendering with normal spacing
                                        renderer.list = function (body, ordered, start) {
                                            const type = ordered ? 'ol' : 'ul';
                                            const startatt = (ordered && start !== 1) ? (' start="' + start + '"') : '';
                                            return '<' + type + ' style="margin-bottom:1em;padding-left:2em;">' + body + '</' + type + '>';
                                        };

                                        renderer.listitem = function (text) {
                                            return '<li style="margin-bottom:0.5em;line-height:1.5;">' + text + '</li>';
                                        };

                                        // Override heading rendering with normal spacing
                                        renderer.heading = function (text, level, raw) {
                                            const marginTop = level <= 2 ? '1.5em' : '1em';
                                            const marginBottom = '0.5em';
                                            return '<h' + level + ' style="margin-top:' + marginTop + ';margin-bottom:' + marginBottom + ';line-height:1.3;font-weight:bold;">' + text + '</h' + level + '>';
                                        };

                                        // Configure marked options
                                        marked.setOptions({
                                            renderer: renderer,
                                            breaks: false,
                                            gfm: true
                                        });

                                        outputElement.innerHTML = marked.parse(this.analysisBuffer);
                                    } else {
                                        outputElement.textContent = this.analysisBuffer;
                                    }
                                } else {
                                    // For translation output, append directly as text
                                    outputElement.textContent += data.content;
                                }
                                // Auto-scroll to bottom
                                outputElement.scrollTop = outputElement.scrollHeight;
                            } else if (data.type === 'error' && data.content) {
                                if (isMarkdown) {
                                    outputElement.innerHTML = `<p style="color: var(--error-color);">${data.content}</p>`;
                                } else {
                                    outputElement.textContent += data.content;
                                    outputElement.style.color = 'var(--error-color)';
                                }
                                this.showToast(data.content, 'error');
                            } else if (data.type === 'done') {
                                // Reset thinking text when done
                                thinkingElement.textContent = isMarkdown ? 'Analyzing...' : 'Translating...';
                                return;
                            }
                        } catch (e) {
                            console.warn('Failed to parse streaming data:', e);
                        }
                    }
                }
            }
        } catch (error) {
            const errorMsg = `Connection error: ${error.message}`;
            if (isMarkdown) {
                outputElement.innerHTML = `<p style="color: var(--error-color);">${errorMsg}</p>`;
            } else {
                outputElement.textContent += `\n\n${errorMsg}`;
                outputElement.style.color = 'var(--error-color)';
            }
            this.showToast('Connection failed. Please check your network and try again.', 'error');
        } finally {
            reader.releaseLock();
            // Reset thinking text
            thinkingElement.textContent = isMarkdown ? 'Analyzing...' : 'Translating...';
        }
    }

    clearAll() {
        this.inputText.value = '';
        this.translationOutput.textContent = 'Translation will appear here...';
        this.translationOutput.style.color = ''; // Reset color
        this.analysisOutput.innerHTML = 'Select a word or phrase in the input text to see detailed analysis...';
        this.analysisOutput.style.color = ''; // Reset color
        this.analysisBuffer = ''; // Reset buffer
        this.currentSelection = '';
        
        // Reset thinking content
        this.translationThinking.textContent = 'Translating...';
        this.analysisThinking.textContent = 'Analyzing...';

        // Clear any pending selection timeout
        if (this.selectionTimeout) {
            clearTimeout(this.selectionTimeout);
            this.selectionTimeout = null;
        }
        
        // Clear persisted input text
        this.clearInputText();

        this.inputText.focus();
    }

    toggleSection(sectionType) {
        const content = sectionType === 'translation' ? this.translationContent : this.analysisContent;
        const collapseBtn = sectionType === 'translation' ? this.translationCollapseBtn : this.analysisCollapseBtn;
        const icon = collapseBtn.querySelector('.collapse-icon');

        const isCollapsed = content.classList.contains('collapsed');

        if (isCollapsed) {
            content.classList.remove('collapsed');
            content.style.height = 'auto';
            icon.textContent = '−';
            icon.style.transform = 'rotate(0deg)';
        } else {
            content.classList.add('collapsed');
            content.style.height = '0';
            icon.textContent = '+';
            icon.style.transform = 'rotate(90deg)';
        }

        // Save state to localStorage
        this.saveCollapsedState(sectionType, !isCollapsed);
    }

    saveCollapsedState(sectionType, isCollapsed) {
        localStorage.setItem(`contextlens_${sectionType}_collapsed`, isCollapsed.toString());
    }

    loadCollapsedStates() {
        // Load translation section state
        const translationCollapsed = localStorage.getItem('contextlens_translation_collapsed') === 'true';
        if (translationCollapsed) {
            this.translationContent.classList.add('collapsed');
            this.translationContent.style.height = '0';
            const icon = this.translationCollapseBtn.querySelector('.collapse-icon');
            icon.textContent = '+';
            icon.style.transform = 'rotate(90deg)';
        }

        // Load analysis section state
        const analysisCollapsed = localStorage.getItem('contextlens_analysis_collapsed') === 'true';
        if (analysisCollapsed) {
            this.analysisContent.classList.add('collapsed');
            this.analysisContent.style.height = '0';
            const icon = this.analysisCollapseBtn.querySelector('.collapse-icon');
            icon.textContent = '+';
            icon.style.transform = 'rotate(90deg)';
        }
    }

    autoResizeTextarea() {
        this.inputText.style.height = 'auto';
        this.inputText.style.height = Math.min(this.inputText.scrollHeight, 400) + 'px';
    }

    handleKeyboardShortcuts(e) {
        // Ctrl/Cmd + Enter to translate
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            this.translateText();
        }

        // Escape to clear selection
        if (e.key === 'Escape') {
            window.getSelection().removeAllRanges();
            this.currentSelection = '';
            this.analysisOutput.textContent = 'Select a word or phrase in the input text to see detailed analysis...';
        }
    }

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
    
    // 持久化存储功能
    saveInputText() {
        const text = this.inputText.value;
        localStorage.setItem('contextlens_input_text', text);
    }
    
    loadInputText() {
        const savedText = localStorage.getItem('contextlens_input_text');
        if (savedText) {
            this.inputText.value = savedText;
        }
    }
    
    clearInputText() {
        localStorage.removeItem('contextlens_input_text');
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.contextLens = new ContextLens();

    // Add some helpful console messages for debugging
    console.log('ContextLens initialized successfully');
    console.log('Keyboard shortcuts:');
    console.log('  Ctrl/Cmd + Enter: Translate text');
    console.log('  Escape: Clear text selection');
});

// Export for potential module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ContextLens;
}