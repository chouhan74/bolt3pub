// Advanced Proctoring System
class ProctoringManager {
    constructor() {
        this.isActive = false;
        this.violations = [];
        this.eventBuffer = [];
        this.lastActivity = Date.now();
        this.tabSwitchCount = 0;
        this.copyPasteCount = 0;
        this.suspiciousActivityCount = 0;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.startActivityMonitoring();
        this.isActive = true;
        console.log('Proctoring system activated');
    }

    setupEventListeners() {
        // Tab/Window focus detection
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.logEvent('tab_switch', { 
                    action: 'tab_hidden',
                    timestamp: Date.now()
                }, 'high');
                this.tabSwitchCount++;
                this.showWarning('Tab switching detected! This action has been logged.');
            } else {
                this.logEvent('window_focus', { 
                    action: 'tab_visible',
                    timestamp: Date.now()
                }, 'medium');
            }
        });

        // Window blur/focus
        window.addEventListener('blur', () => {
            this.logEvent('window_blur', {
                timestamp: Date.now()
            }, 'medium');
        });

        window.addEventListener('focus', () => {
            this.logEvent('window_focus', {
                timestamp: Date.now()
            }, 'low');
        });

        // Copy/Paste detection
        document.addEventListener('copy', (e) => {
            this.logEvent('copy_paste', {
                action: 'copy',
                timestamp: Date.now(),
                selection: window.getSelection().toString().substring(0, 100)
            }, 'medium');
            this.copyPasteCount++;
        });

        document.addEventListener('paste', (e) => {
            const pastedData = (e.clipboardData || window.clipboardData).getData('text');
            this.logEvent('copy_paste', {
                action: 'paste',
                timestamp: Date.now(),
                data: pastedData.substring(0, 100)
            }, 'high');
            this.copyPasteCount++;
            this.showWarning('Paste operation detected and logged.');
        });

        // Right-click detection
        document.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            this.logEvent('right_click', {
                x: e.clientX,
                y: e.clientY,
                target: e.target.tagName,
                timestamp: Date.now()
            }, 'medium');
            this.showWarning('Right-click is disabled during the assessment.');
        });

        // Key combination detection
        document.addEventListener('keydown', (e) => {
            this.detectSuspiciousKeystrokes(e);
        });

        // Window resize detection
        window.addEventListener('resize', () => {
            this.logEvent('window_resize', {
                width: window.innerWidth,
                height: window.innerHeight,
                timestamp: Date.now()
            }, 'low');
        });

        // Fullscreen change detection
        document.addEventListener('fullscreenchange', () => {
            if (!document.fullscreenElement) {
                this.logEvent('fullscreen_exit', {
                    timestamp: Date.now()
                }, 'medium');
            }
        });

        // Mouse movement tracking (for suspicious patterns)
        let mouseMovements = [];
        document.addEventListener('mousemove', (e) => {
            mouseMovements.push({
                x: e.clientX,
                y: e.clientY,
                timestamp: Date.now()
            });

            // Keep only last 50 movements
            if (mouseMovements.length > 50) {
                mouseMovements = mouseMovements.slice(-50);
            }

            // Detect rapid movements (potential automation)
            if (mouseMovements.length >= 10) {
                const recent = mouseMovements.slice(-10);
                const avgSpeed = this.calculateMouseSpeed(recent);
                
                if (avgSpeed > 2000) { // pixels per second threshold
                    this.logEvent('suspicious_activity', {
                        type: 'rapid_mouse_movement',
                        avgSpeed: avgSpeed,
                        timestamp: Date.now()
                    }, 'high');
                    this.suspiciousActivityCount++;
                }
            }
        });

        // Detect developer tools
        this.detectDevTools();
    }

    detectSuspiciousKeystrokes(e) {
        const suspiciousKeys = [
            { key: 'F12', severity: 'high' },
            { key: 'F5', severity: 'medium' },
            { ctrl: true, shift: true, key: 'I', severity: 'high' },
            { ctrl: true, shift: true, key: 'C', severity: 'high' },
            { ctrl: true, shift: true, key: 'J', severity: 'high' },
            { ctrl: true, key: 'U', severity: 'high' },
            { ctrl: true, key: 'S', severity: 'low' }, // Save - allowed but logged
            { alt: true, key: 'Tab', severity: 'high' }
        ];

        for (const combo of suspiciousKeys) {
            if (this.matchesKeyCombo(e, combo)) {
                e.preventDefault();
                e.stopPropagation();
                
                this.logEvent('key_combination', {
                    key: combo.key,
                    ctrl: combo.ctrl || false,
                    shift: combo.shift || false,
                    alt: combo.alt || false,
                    timestamp: Date.now()
                }, combo.severity);

                if (combo.severity === 'high') {
                    this.showViolation(`Blocked key combination: ${this.formatKeyCombo(combo)}`);
                }
                break;
            }
        }
    }

    matchesKeyCombo(event, combo) {
        return event.key === combo.key &&
               (combo.ctrl === undefined || event.ctrlKey === combo.ctrl) &&
               (combo.shift === undefined || event.shiftKey === combo.shift) &&
               (combo.alt === undefined || event.altKey === combo.alt);
    }

    formatKeyCombo(combo) {
        let parts = [];
        if (combo.ctrl) parts.push('Ctrl');
        if (combo.shift) parts.push('Shift');
        if (combo.alt) parts.push('Alt');
        parts.push(combo.key);
        return parts.join('+');
    }

    calculateMouseSpeed(movements) {
        if (movements.length < 2) return 0;

        let totalDistance = 0;
        let totalTime = 0;

        for (let i = 1; i < movements.length; i++) {
            const prev = movements[i - 1];
            const curr = movements[i];
            
            const distance = Math.sqrt(
                Math.pow(curr.x - prev.x, 2) + Math.pow(curr.y - prev.y, 2)
            );
            const time = curr.timestamp - prev.timestamp;
            
            totalDistance += distance;
            totalTime += time;
        }

        return totalTime > 0 ? (totalDistance / totalTime) * 1000 : 0; // pixels per second
    }

    detectDevTools() {
        // Method 1: Console detection
        let devtools = {
            open: false,
            orientation: null
        };

        const threshold = 160;

        setInterval(() => {
            if (window.outerHeight - window.innerHeight > threshold || 
                window.outerWidth - window.innerWidth > threshold) {
                if (!devtools.open) {
                    devtools.open = true;
                    this.logEvent('suspicious_activity', {
                        type: 'devtools_detected',
                        method: 'window_size_detection',
                        timestamp: Date.now()
                    }, 'high');
                    this.showViolation('Developer tools detected!');
                }
            } else {
                devtools.open = false;
            }
        }, 500);

        // Method 2: Console.log override
        const originalLog = console.log;
        console.log = function(...args) {
            this.logEvent('suspicious_activity', {
                type: 'console_usage',
                timestamp: Date.now()
            }, 'medium');
            return originalLog.apply(console, args);
        }.bind(this);
    }

    startActivityMonitoring() {
        // Monitor for periods of inactivity
        setInterval(() => {
            const now = Date.now();
            const inactiveTime = now - this.lastActivity;
            
            if (inactiveTime > 300000) { // 5 minutes
                this.logEvent('suspicious_activity', {
                    type: 'prolonged_inactivity',
                    duration: inactiveTime,
                    timestamp: now
                }, 'medium');
            }
        }, 60000); // Check every minute

        // Update last activity on any user interaction
        ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(event => {
            document.addEventListener(event, () => {
                this.lastActivity = Date.now();
            }, true);
        });
    }

    async logEvent(eventType, eventData, severity = 'medium') {
        const event = {
            event_type: eventType,
            event_data: eventData,
            severity: severity,
            timestamp: Date.now()
        };

        this.eventBuffer.push(event);

        // Determine if this is a violation
        const isViolation = severity === 'high' || 
                           (eventType === 'copy_paste' && !this.isAllowedCopyPaste()) ||
                           (eventType === 'tab_switch' && !this.isAllowedTabSwitch());

        if (isViolation) {
            this.violations.push(event);
        }

        // Send to server
        try {
            await fetch('/api/proctoring-event', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    event_type: eventType,
                    event_data: eventData,
                    severity: severity
                })
            });
        } catch (error) {
            console.error('Failed to log proctoring event:', error);
            // Store locally for retry
            localStorage.setItem('pendingProctoringEvents', 
                JSON.stringify(this.eventBuffer));
        }

        // Flush buffer periodically
        if (this.eventBuffer.length > 10) {
            this.eventBuffer = this.eventBuffer.slice(-5);
        }
    }

    isAllowedCopyPaste() {
        // Check assessment settings (would be passed from backend)
        return window.assessmentSettings?.allow_copy_paste || false;
    }

    isAllowedTabSwitch() {
        // Check assessment settings
        return window.assessmentSettings?.allow_tab_switching || false;
    }

    showWarning(message) {
        this.showNotification(message, 'warning');
    }

    showViolation(message) {
        this.showNotification(message, 'violation');
        
        // Increment violation count
        this.suspiciousActivityCount++;
        
        // Auto-submit if too many violations
        if (this.suspiciousActivityCount >= 5) {
            this.showNotification('Too many violations detected. Assessment will be auto-submitted.', 'violation');
            setTimeout(() => {
                if (window.submitAssessment) {
                    window.submitAssessment();
                }
            }, 3000);
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 max-w-sm ${
            type === 'violation' ? 'bg-red-500 text-white' :
            type === 'warning' ? 'bg-yellow-500 text-white' :
            'bg-blue-500 text-white'
        }`;
        
        notification.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0">
                    <i class="fas ${
                        type === 'violation' ? 'fa-exclamation-triangle' :
                        type === 'warning' ? 'fa-exclamation-circle' :
                        'fa-info-circle'
                    }"></i>
                </div>
                <div class="ml-3">
                    <p class="text-sm font-medium">${message}</p>
                </div>
                <div class="ml-auto pl-3">
                    <button onclick="this.parentElement.parentElement.parentElement.remove()" 
                            class="text-white hover:text-gray-200">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    getViolationSummary() {
        return {
            totalViolations: this.violations.length,
            tabSwitches: this.tabSwitchCount,
            copyPasteEvents: this.copyPasteCount,
            suspiciousActivities: this.suspiciousActivityCount,
            violations: this.violations
        };
    }

    disable() {
        this.isActive = false;
        console.log('Proctoring system deactivated');
    }
}

// Initialize proctoring when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Only activate on assessment pages
    if (window.location.pathname.includes('/candidate/')) {
        window.proctoringManager = new ProctoringManager();
    }
});