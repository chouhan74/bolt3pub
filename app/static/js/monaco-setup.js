// Monaco Editor Setup and Configuration
class MonacoEditorManager {
    constructor() {
        this.editor = null;
        this.currentLanguage = 'python';
        this.autoSaveInterval = null;
        this.changeTimeout = null;
    }

    async initialize(containerId, initialCode = '', language = 'python') {
        // Load Monaco Editor
        require.config({ 
            paths: { 
                'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.39.0/min/vs' 
            }
        });

        return new Promise((resolve) => {
            require(['vs/editor/editor.main'], () => {
                this.editor = monaco.editor.create(document.getElementById(containerId), {
                    value: initialCode,
                    language: this.getMonacoLanguage(language),
                    theme: 'vs-light',
                    automaticLayout: true,
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineNumbers: 'on',
                    roundedSelection: false,
                    scrollBeyondLastLine: false,
                    readOnly: false,
                    wordWrap: 'bounded',
                    folding: true,
                    lineDecorationsWidth: 10,
                    lineNumbersMinChars: 3,
                    glyphMargin: false,
                    contextmenu: false, // Disable right-click menu for proctoring
                    quickSuggestions: {
                        other: true,
                        comments: false,
                        strings: false
                    },
                    suggestOnTriggerCharacters: true,
                    acceptSuggestionOnEnter: 'on',
                    tabCompletion: 'on',
                    wordBasedSuggestions: true,
                    parameterHints: {
                        enabled: true
                    }
                });

                this.currentLanguage = language;
                this.setupEventListeners();
                resolve(this.editor);
            });
        });
    }

    setupEventListeners() {
        if (!this.editor) return;

        // Auto-save on content change
        this.editor.onDidChangeModelContent(() => {
            this.scheduleAutoSave();
        });

        // Disable certain key combinations for proctoring
        this.editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyA, () => {
            // Allow select all
        });

        // Block F12, Ctrl+Shift+I, etc.
        this.editor.onKeyDown((e) => {
            if (e.keyCode === monaco.KeyCode.F12 ||
                (e.ctrlKey && e.shiftKey && e.keyCode === monaco.KeyCode.KeyI) ||
                (e.ctrlKey && e.keyCode === monaco.KeyCode.KeyU)) {
                e.preventDefault();
                e.stopPropagation();
                this.logProctoringEvent('blocked_key_combination', {
                    keyCode: e.keyCode,
                    ctrlKey: e.ctrlKey,
                    shiftKey: e.shiftKey
                });
            }
        });
    }

    getMonacoLanguage(lang) {
        const mapping = {
            'python': 'python',
            'cpp': 'cpp',
            'c': 'c',
            'java': 'java',
            'javascript': 'javascript',
            'js': 'javascript'
        };
        return mapping[lang] || 'python';
    }

    changeLanguage(newLanguage) {
        if (this.editor && newLanguage !== this.currentLanguage) {
            monaco.editor.setModelLanguage(
                this.editor.getModel(), 
                this.getMonacoLanguage(newLanguage)
            );
            this.currentLanguage = newLanguage;
        }
    }

    getValue() {
        return this.editor ? this.editor.getValue() : '';
    }

    setValue(value) {
        if (this.editor) {
            this.editor.setValue(value);
        }
    }

    scheduleAutoSave() {
        if (this.changeTimeout) {
            clearTimeout(this.changeTimeout);
        }

        this.changeTimeout = setTimeout(() => {
            this.performAutoSave();
        }, 3000); // Auto-save after 3 seconds of inactivity
    }

    async performAutoSave() {
        if (!this.editor) return;

        try {
            const code = this.getValue();
            const questionId = window.currentQuestionId; // Set this globally

            if (questionId && code.trim()) {
                await fetch('/api/auto-save', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        question_id: questionId,
                        code: code
                    })
                });
            }
        } catch (error) {
            console.error('Auto-save failed:', error);
        }
    }

    async logProctoringEvent(eventType, eventData) {
        try {
            await fetch('/api/proctoring-event', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    event_type: eventType,
                    event_data: eventData,
                    severity: 'medium'
                })
            });
        } catch (error) {
            console.error('Failed to log proctoring event:', error);
        }
    }

    focus() {
        if (this.editor) {
            this.editor.focus();
        }
    }

    dispose() {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
        }
        if (this.changeTimeout) {
            clearTimeout(this.changeTimeout);
        }
        if (this.editor) {
            this.editor.dispose();
        }
    }
}

// Global Monaco Editor instance
window.monacoManager = new MonacoEditorManager();