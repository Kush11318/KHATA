class AIAssistant {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.synth = window.speechSynthesis;
        this.chatHistory = []; // Memory
        this.initSpeechRecognition();
        this.createUI();
        this.checkAndPopulateInvoice(); // Check if we need to fill the form
    }

    initSpeechRecognition() {
        if ('webkitSpeechRecognition' in window) {
            this.recognition = new webkitSpeechRecognition();
            this.recognition.continuous = true; // Keep listening through pauses
            this.recognition.interimResults = true; // Transcribe live word-by-word
            this.recognition.lang = 'en-IN'; // Good for Hinglish and Indian accents
            this.silenceTimer = null;

            this.recognition.onstart = () => {
                this.isListening = true;
                this.updateUIState('listening');
                this.finalTranscript = '';
                if (this.silenceTimer) clearTimeout(this.silenceTimer);
            };

            this.recognition.onend = () => {
                this.isListening = false;
                this.updateUIState('idle');
                if (this.silenceTimer) clearTimeout(this.silenceTimer);
            };

            this.recognition.onresult = (event) => {
                let interimTranscript = '';
                let finalTranscript = '';

                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        finalTranscript += event.results[i][0].transcript;
                    } else {
                        interimTranscript += event.results[i][0].transcript;
                    }
                }

                if (finalTranscript) {
                    this.finalTranscript += (this.finalTranscript ? ' ' : '') + finalTranscript;
                }

                // Show live transcribing text in the input box word-by-word
                const liveText = this.finalTranscript + (interimTranscript ? (this.finalTranscript ? ' ' : '') + interimTranscript : '');
                const input = document.getElementById('ai-text-input');
                if (input) {
                    input.value = liveText;
                }

                // Silence detection: reset timer every time speech is detected
                if (this.silenceTimer) {
                    clearTimeout(this.silenceTimer);
                }

                // If user stops speaking for 3 seconds, auto-submit the sentence
                this.silenceTimer = setTimeout(() => {
                    if (this.isListening) {
                        this.recognition.stop(); // Stop recording
                        
                        const finalVal = input ? input.value.trim() : '';
                        if (finalVal) {
                            this.handleUserInput(finalVal);
                            if (input) input.value = '';
                        }
                    }
                }, 3000);
            };

            this.recognition.onerror = (event) => {
                console.error('Speech recognition error', event.error);
                if (event.error !== 'no-speech') {
                    this.speak("Sorry, there was a speech recognition error.");
                }
            };
        } else {
            console.warn('Speech recognition not supported');
        }
    }

    createUI() {
        // Create container wrapper
        const container = document.createElement('div');
        container.id = 'ai-assistant-container';
        container.className = 'ai-assistant-container';
        
        container.innerHTML = `
            <button id="ai-assistant-btn" class="ai-assistant-btn" title="AI Assistant">
                <div class="ai-btn-glow"></div>
                <div class="ai-btn-ripple" id="ai-btn-ripple"></div>
                <div class="ai-btn-content">
                    <i class="fas fa-robot"></i>
                </div>
            </button>
        `;
        document.body.appendChild(container);

        // Welcome entry animation sequence & ripple wave
        const mainBtn = container.querySelector('#ai-assistant-btn');
        const ripple = container.querySelector('#ai-btn-ripple');
        
        mainBtn.classList.add('entrance');
        
        // Trigger glowing ripple wave right as entrance completes
        setTimeout(() => {
            if (ripple) ripple.classList.add('animate');
        }, 500);

        // Create Chat Modal (hidden by default)
        const modal = document.createElement('div');
        modal.id = 'ai-chat-modal';
        modal.className = 'ai-chat-modal';
        modal.innerHTML = `
            <div class="ai-modal-header">
                <h3 class="ai-modal-title"><i class="fas fa-robot"></i> Billing Assistant</h3>
                <button id="ai-close-btn" class="ai-close-btn" title="Close">×</button>
            </div>
            <div id="ai-chat-messages" class="ai-messages">
                <div class="ai-message ai">
                    <div class="ai-avatar"><i class="fas fa-robot"></i></div>
                    <div class="ai-text">Hi! I can help you:<br>
                        • <strong>Database Insights:</strong> "Show business insights" or "How is business?"<br>
                        • <strong>Voice Navigation:</strong> "Go to products", "Show analytics", "Create invoice"<br>
                        • <strong>Add products:</strong> "Add product Milk price 50 stock 100"<br>
                        • <strong>Add customers:</strong> "Add customer John email john@example.com"<br>
                        • <strong>Create invoices:</strong> "Bill for Riya: 2 milks and 1 bread"<br><br>
                        Try saying a command or click one of the quick commands below!
                    </div>
                </div>
            </div>
            <div class="ai-quick-pills">
                <button class="ai-pill-btn" onclick="window.aiAssistant.sendQuickCommand('Show business insights')"><i class="fas fa-chart-line"></i> Insights</button>
                <button class="ai-pill-btn" onclick="window.aiAssistant.sendQuickCommand('Go to products')"><i class="fas fa-box"></i> Products</button>
                <button class="ai-pill-btn" onclick="window.aiAssistant.sendQuickCommand('Show analytics')"><i class="fas fa-chart-bar"></i> Analytics</button>
                <button class="ai-pill-btn" onclick="window.aiAssistant.sendQuickCommand('Create invoice')"><i class="fas fa-plus"></i> Create Invoice</button>
            </div>
            <div class="ai-input-area">
                <button id="ai-mic-btn" class="ai-mic-btn" title="Speak command"><i class="fas fa-microphone"></i></button>
                <input type="text" id="ai-text-input" class="ai-input" placeholder="Type or speak...">
                <button id="ai-send-btn" class="ai-send-btn" title="Send message"><i class="fas fa-paper-plane"></i></button>
            </div>
        `;
        document.body.appendChild(modal);

        // Main button toggle modal
        mainBtn.onclick = () => {
            if (modal.classList.contains('active')) {
                this.closeChatModal();
            } else {
                this.openChatModal();
            }
        };

        // Close button click
        document.getElementById('ai-close-btn').onclick = () => {
            this.closeChatModal();
        };
        
        // Close modal when clicking outside (on the modal backdrop)
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeChatModal();
            }
        });

        // Event listeners for text input
        document.getElementById('ai-send-btn').onclick = () => {
            const input = document.getElementById('ai-text-input');
            if (input.value.trim()) {
                this.handleUserInput(input.value.trim());
                input.value = '';
            }
        };

        document.getElementById('ai-text-input').onkeypress = (e) => {
            if (e.key === 'Enter') {
                document.getElementById('ai-send-btn').click();
            }
        };

        // Event listener for microphone button
        document.getElementById('ai-mic-btn').onclick = () => {
            this.toggleListening();
        };
    }

    openChatModal() {
        const modal = document.getElementById('ai-chat-modal');
        if (modal) {
            modal.classList.add('active');
            const input = document.getElementById('ai-text-input');
            if (input) input.focus();
        }
    }

    closeChatModal() {
        const modal = document.getElementById('ai-chat-modal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    toggleListening() {
        if (!this.recognition) {
            alert("Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.");
            return;
        }

        try {
            if (this.isListening) {
                this.recognition.stop();
            } else {
                this.recognition.start();
            }
        } catch (e) {
            console.error("Error toggling speech recognition:", e);
            try {
                this.recognition.abort(); // Force release the microphone
            } catch (err) {}
            this.isListening = false;
            this.updateUIState('idle');
        }
    }

    updateUIState(state) {
        const micBtn = document.getElementById('ai-mic-btn');
        const textInput = document.getElementById('ai-text-input');
        const mainBtn = document.getElementById('ai-assistant-btn');
        
        if (state === 'listening') {
            if (micBtn) {
                micBtn.innerHTML = '<i class="fas fa-stop" style="color: #ff3b30;"></i>';
                micBtn.classList.add('listening');
            }
            if (mainBtn) {
                mainBtn.classList.add('listening');
            }
            if (textInput) {
                textInput.placeholder = 'Listening... Speak now...';
                textInput.value = '';
            }
        } else {
            if (micBtn) {
                micBtn.innerHTML = '<i class="fas fa-microphone"></i>';
                micBtn.classList.remove('listening');
            }
            if (mainBtn) {
                mainBtn.classList.remove('listening');
            }
            if (textInput) {
                textInput.placeholder = 'Type or click mic to speak...';
            }
        }
    }


    addMessage(text, sender) {
        const container = document.getElementById('ai-chat-messages');
        const div = document.createElement('div');
        div.className = `ai-message ${sender}`;

        if (sender === 'ai') {
            div.innerHTML = `
                <div class="ai-avatar"><i class="fas fa-robot"></i></div>
                <div class="ai-text">${text}</div>
            `;
        } else {
            div.innerHTML = `
                <div class="ai-text">${text}</div>
                <div class="ai-avatar user"><i class="fas fa-user"></i></div>
            `;
        }

        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    async handleUserInput(text) {
        this.addMessage(text, 'user');
        this.chatHistory.push({ role: 'user', content: text });

        // Show loading
        const loadingId = 'ai-loading-' + Date.now();
        const container = document.getElementById('ai-chat-messages');
        const loadingDiv = document.createElement('div');
        loadingDiv.id = loadingId;
        loadingDiv.className = 'ai-message ai';
        loadingDiv.innerHTML = `
            <div class="ai-avatar"><i class="fas fa-robot"></i></div>
            <div class="ai-text"><i class="fas fa-spinner fa-spin"></i> Thinking...</div>
        `;
        container.appendChild(loadingDiv);
        container.scrollTop = container.scrollHeight;

        try {
            const response = await fetch('/api/ai/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    history: this.chatHistory
                })
            });

            const data = await response.json();
            document.getElementById(loadingId).remove();

            if (data.error) {
                this.addMessage("Error: " + data.error, 'ai');
                this.speak("Sorry, something went wrong.");
                return;
            }

            this.addMessage(data.response_text, 'ai');
            this.chatHistory.push({ role: 'model', content: data.response_text });
            this.speak(data.response_text);

            // Handle different intents
            if (data.intent === 'navigation') {
                this.handleNavigation(data.data);
            } else if (data.intent === 'business_insights') {
                this.showBusinessInsights(data.data);
            } else if (data.intent === 'create_invoice') {
                this.showInvoicePreview(data.data);
            } else if (data.intent === 'add_product') {
                if (data.success && data.product_id) {
                    // Product was already added by backend, redirect to products page
                    setTimeout(() => {
                        window.location.href = '/seller/products';
                    }, 1500);
                } else {
                    // Show preview if addition failed or needs confirmation
                    this.showProductPreview(data.data);
                }
            } else if (data.intent === 'add_customer') {
                if (data.success && data.customer_id) {
                    // Customer was already added by backend, redirect to customers page
                    setTimeout(() => {
                        window.location.href = '/seller/customers';
                    }, 1500);
                } else {
                    // Show preview if addition failed or needs confirmation
                    this.showCustomerPreview(data.data);
                }
            }

        } catch (error) {
            const loadingEl = document.getElementById(loadingId);
            if (loadingEl) loadingEl.remove();

            this.addMessage("Network error. Please try again.", 'ai');
            console.error(error);
        }
    }

    speak(text) {
        if (this.synth) {
            // Cancel any current speech in the queue to prevent freezes
            this.synth.cancel();

            // Prepare text for speech synthesis by removing emojis and formatting
            let cleanText = text || '';
            
            // Whitelist only standard alphanumeric characters, basic punctuation, and whitespace
            cleanText = cleanText.replace(/[^a-zA-Z0-9.,!?'"()%\s\-]/g, ' ');

            // Clean up whitespace
            cleanText = cleanText.replace(/\s+/g, ' ').trim();

            if (cleanText) {
                const utterance = new SpeechSynthesisUtterance(cleanText);
                
                // Add error handling to resume/cancel if it gets stuck
                utterance.onerror = (event) => {
                    console.error('SpeechSynthesisUtterance error:', event.error);
                    this.synth.cancel();
                };

                this.synth.speak(utterance);
            }
        }
    }

    showInvoicePreview(data) {
        const container = document.getElementById('ai-chat-messages');

        let itemsHtml = data.items.map(item => `
            <div class="ai-preview-item">
                <span>${item.product_name} x${item.quantity}</span>
                <span>${item.is_new_product ? '(New)' : ''}</span>
            </div>
        `).join('');

        const previewDiv = document.createElement('div');
        previewDiv.className = 'ai-preview-card';
        previewDiv.innerHTML = `
            <div class="ai-preview-header">Invoice Preview</div>
            <div style="margin-bottom: 8px; font-size: 13px;"><strong>Customer:</strong> ${data.customer_name} ${data.is_new_customer ? '(New)' : ''}</div>
            <div class="ai-preview-items">${itemsHtml}</div>
            <div class="ai-preview-actions">
                <button onclick="window.aiAssistant.createInvoice(${JSON.stringify(data).replace(/"/g, '&quot;')})" class="ai-confirm-btn">Confirm & Create</button>
                <button onclick="this.parentElement.parentElement.remove()" class="ai-cancel-btn">Cancel</button>
            </div>
        `;
        container.appendChild(previewDiv);
        container.scrollTop = container.scrollHeight;
    }

    async createInvoice(data) {
        this.addMessage("Redirecting to invoice creation...", 'ai');
        // Store data in session storage
        sessionStorage.setItem('aiInvoiceData', JSON.stringify(data));

        setTimeout(() => {
            window.location.href = '/seller/invoices/create';
        }, 1000);
    }

    checkAndPopulateInvoice() {
        // Check if we are on the create invoice page
        if (window.location.pathname.includes('/seller/invoices/create')) {
            const dataStr = sessionStorage.getItem('aiInvoiceData');
            if (dataStr) {
                try {
                    const data = JSON.parse(dataStr);
                    sessionStorage.removeItem('aiInvoiceData'); // Clear it

                    console.log("Populating invoice from AI data:", data);

                    // Wait for DOM to be fully ready just in case
                    setTimeout(() => {
                        this.populateInvoiceForm(data);
                    }, 500);
                } catch (e) {
                    console.error("Error parsing AI invoice data", e);
                }
            }
        }
    }

    showProductPreview(data) {
        const container = document.getElementById('ai-chat-messages');
        
        const previewDiv = document.createElement('div');
        previewDiv.className = 'ai-preview-card';
        previewDiv.innerHTML = `
            <div class="ai-preview-header">Product Preview</div>
            <div class="ai-preview-items">
                <div class="ai-preview-item">
                    <span><strong>Name:</strong></span>
                    <span>${data.name || 'N/A'}</span>
                </div>
                <div class="ai-preview-item">
                    <span><strong>Price:</strong></span>
                    <span>₹${data.price || '0.00'}</span>
                </div>
                <div class="ai-preview-item">
                    <span><strong>Stock:</strong></span>
                    <span>${data.stock || 0}</span>
                </div>
                ${data.description ? `<div class="ai-preview-item"><span><strong>Description:</strong></span><span>${data.description}</span></div>` : ''}
            </div>
            <div class="ai-preview-actions">
                <button onclick="window.aiAssistant.confirmAddProduct(${JSON.stringify(data).replace(/"/g, '&quot;')})" class="ai-confirm-btn">Confirm & Add</button>
                <button onclick="this.parentElement.parentElement.remove()" class="ai-cancel-btn">Cancel</button>
            </div>
        `;
        container.appendChild(previewDiv);
        container.scrollTop = container.scrollHeight;
    }

    showCustomerPreview(data) {
        const container = document.getElementById('ai-chat-messages');
        
        const previewDiv = document.createElement('div');
        previewDiv.className = 'ai-preview-card';
        previewDiv.innerHTML = `
            <div class="ai-preview-header">Customer Preview</div>
            <div class="ai-preview-items">
                <div class="ai-preview-item">
                    <span><strong>Name:</strong></span>
                    <span>${data.name || 'N/A'}</span>
                </div>
                <div class="ai-preview-item">
                    <span><strong>Email:</strong></span>
                    <span>${data.email || 'N/A'}</span>
                </div>
                ${data.phone ? `<div class="ai-preview-item"><span><strong>Phone:</strong></span><span>${data.phone}</span></div>` : ''}
                ${data.address ? `<div class="ai-preview-item"><span><strong>Address:</strong></span><span>${data.address}</span></div>` : ''}
            </div>
            <div class="ai-preview-actions">
                <button onclick="window.aiAssistant.confirmAddCustomer(${JSON.stringify(data).replace(/"/g, '&quot;')})" class="ai-confirm-btn">Confirm & Add</button>
                <button onclick="this.parentElement.parentElement.remove()" class="ai-cancel-btn">Cancel</button>
            </div>
        `;
        container.appendChild(previewDiv);
        container.scrollTop = container.scrollHeight;
    }

    async confirmAddProduct(data) {
        this.addMessage("Adding product...", 'ai');
        
        try {
            const response = await fetch('/api/products/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: data.name,
                    price: data.price || 0,
                    stock: data.stock || 0,
                    description: data.description || ''
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.addMessage("✅ Product added successfully! Redirecting to products page...", 'ai');
                this.speak("Product added successfully! Redirecting to products page...");
                setTimeout(() => {
                    window.location.href = '/seller/products';
                }, 1500);
            } else {
                this.addMessage("❌ Failed to add product: " + (result.error || 'Unknown error'), 'ai');
                this.speak("Failed to add product: " + (result.error || 'Unknown error'));
            }
        } catch (error) {
            this.addMessage("❌ Network error. Please try again.", 'ai');
            console.error(error);
        }
    }

    async confirmAddCustomer(data) {
        this.addMessage("Adding customer...", 'ai');
        
        try {
            // Use the AI process endpoint which handles customer addition
            const response = await fetch('/api/ai/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: `add customer name ${data.name} email ${data.email}${data.phone ? ' phone ' + data.phone : ''}${data.address ? ' address ' + data.address : ''}`,
                    history: []
                })
            });

            const result = await response.json();
            
            if (result.success && result.customer_id) {
                this.addMessage("✅ Customer added successfully! Redirecting to customers page...", 'ai');
                this.speak("Customer added successfully! Redirecting to customers page...");
                setTimeout(() => {
                    window.location.href = '/seller/customers';
                }, 1500);
            } else {
                this.addMessage("❌ " + (result.response_text || 'Failed to add customer'), 'ai');
                this.speak(result.response_text || 'Failed to add customer');
            }
        } catch (error) {
            this.addMessage("❌ Network error. Please try again.", 'ai');
            console.error(error);
        }
    }

    handleNavigation(data) {
        if (!data || !data.target) return;
        
        const targets = {
            'dashboard': '/seller',
            'products': '/seller/products',
            'invoices': '/seller/invoices',
            'customers': '/seller/customers',
            'analytics': '/seller/customer-analytics',
            'create_invoice': '/seller/invoices/create',
            'logout': '/logout'
        };
        
        const url = targets[data.target];
        if (url) {
            this.showTransitionOverlay(data.target);
            setTimeout(() => {
                window.location.href = url;
            }, 1500);
        }
    }

    showTransitionOverlay(target) {
        // Remove existing overlay if any
        const existing = document.querySelector('.ai-transition-overlay');
        if (existing) existing.remove();

        const overlay = document.createElement('div');
        overlay.className = 'ai-transition-overlay';
        
        const names = {
            'dashboard': 'Dashboard',
            'products': 'Products Inventory',
            'invoices': 'Invoices List',
            'customers': 'Customer Management',
            'analytics': 'Analytics Center',
            'create_invoice': 'Invoice Creator',
            'logout': 'Secure Logout'
        };
        
        overlay.innerHTML = `
            <div class="ai-transition-content">
                <div class="ai-transition-logo"><i class="fas fa-robot"></i></div>
                <div class="ai-transition-text">Navigating to ${names[target] || target}...</div>
                <div class="ai-transition-bar"><div class="ai-transition-progress"></div></div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        
        // Trigger fade-in
        setTimeout(() => {
            overlay.classList.add('active');
        }, 10);
    }

    showBusinessInsights(data) {
        const container = document.getElementById('ai-chat-messages');
        const card = document.createElement('div');
        card.className = 'ai-insights-card';
        
        const formatRevenue = (val) => {
            return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
        };
        
        const statsGridHtml = `
            <div class="ai-insights-grid">
                <div class="ai-insight-item">
                    <div class="ai-insight-icon"><i class="fas fa-wallet" style="color: #10b981;"></i></div>
                    <div class="ai-insight-info">
                        <div class="ai-insight-val">${formatRevenue(data.revenue || 0)}</div>
                        <div class="ai-insight-lbl">Revenue</div>
                    </div>
                </div>
                <div class="ai-insight-item">
                    <div class="ai-insight-icon"><i class="fas fa-file-invoice" style="color: #3b82f6;"></i></div>
                    <div class="ai-insight-info">
                        <div class="ai-insight-val">${data.invoices_count || 0}</div>
                        <div class="ai-insight-lbl">Invoices</div>
                    </div>
                </div>
                <div class="ai-insight-item">
                    <div class="ai-insight-icon"><i class="fas fa-users" style="color: #8b5cf6;"></i></div>
                    <div class="ai-insight-info">
                        <div class="ai-insight-val">${data.customers_count || 0}</div>
                        <div class="ai-insight-lbl">Customers</div>
                    </div>
                </div>
                <div class="ai-insight-item">
                    <div class="ai-insight-icon"><i class="fas fa-exclamation-triangle" style="color: ${data.low_stock && data.low_stock.length > 0 ? '#f59e0b' : '#10b981'};"></i></div>
                    <div class="ai-insight-info">
                        <div class="ai-insight-val">${data.low_stock ? data.low_stock.length : 0}</div>
                        <div class="ai-insight-lbl">Low Stock</div>
                    </div>
                </div>
            </div>
        `;
        
        let topSellingHtml = '';
        if (data.top_selling && data.top_selling.length > 0) {
            const maxQty = Math.max(...data.top_selling.map(p => p.quantity), 1);
            
            const barsHtml = data.top_selling.map(p => {
                const pct = Math.round((p.quantity / maxQty) * 100);
                return `
                    <div class="ai-insights-chart-row">
                        <div class="ai-insights-chart-lbl">${p.name}</div>
                        <div class="ai-insights-chart-bar-container">
                            <div class="ai-insights-chart-bar" style="width: ${pct}%"></div>
                        </div>
                        <div class="ai-insights-chart-val">${p.quantity} sold</div>
                    </div>
                `;
            }).join('');
            
            topSellingHtml = `
                <div class="ai-insights-section">
                    <div class="ai-insights-section-title"><i class="fas fa-fire"></i> Top Selling Products</div>
                    <div class="ai-insights-chart-container">
                        ${barsHtml}
                    </div>
                </div>
            `;
        }
        
        let lowStockHtml = '';
        if (data.low_stock && data.low_stock.length > 0) {
            const alertsHtml = data.low_stock.map(p => `
                <div class="ai-insights-alert-row alert-warning">
                    <span class="ai-insights-alert-name"><i class="fas fa-exclamation-circle text-warning"></i> ${p.name}</span>
                    <span class="ai-insights-alert-stock badge-danger">${p.stock} left</span>
                </div>
            `).join('');
            
            lowStockHtml = `
                <div class="ai-insights-section">
                    <div class="ai-insights-section-title"><i class="fas fa-warehouse"></i> Low Stock Alerts</div>
                    <div class="ai-insights-alerts-list">
                        ${alertsHtml}
                    </div>
                </div>
            `;
        } else {
            lowStockHtml = `
                <div class="ai-insights-section">
                    <div class="ai-insights-section-title"><i class="fas fa-warehouse"></i> Stock Health</div>
                    <div class="ai-insights-alert-row alert-success">
                        <span class="ai-insights-alert-name"><i class="fas fa-check-circle text-success"></i> All items healthy</span>
                        <span class="ai-insights-alert-stock badge-success">Good</span>
                    </div>
                </div>
            `;
        }
        
        card.innerHTML = `
            <div class="ai-insights-header">
                <i class="fas fa-chart-line"></i> Real-time Business Insights
            </div>
            ${statsGridHtml}
            ${topSellingHtml}
            ${lowStockHtml}
        `;
        
        container.appendChild(card);
        container.scrollTop = container.scrollHeight;
    }

    sendQuickCommand(text) {
        this.handleUserInput(text);
    }

    populateInvoiceForm(data) {
        // 1. Set Customer
        if (data.customer_id) {
            const customerSelect = document.querySelector('select[name="customer_id"]');
            if (customerSelect) {
                customerSelect.value = data.customer_id;
            }
        } else if (data.customer_name) {
            // New customer or unmatched name - might need to create temp customer or alert user
            // For now, let's try to find by text if ID wasn't passed but name matches
            const customerSelect = document.querySelector('select[name="customer_id"]');
            for (let i = 0; i < customerSelect.options.length; i++) {
                if (customerSelect.options[i].text.toLowerCase().includes(data.customer_name.toLowerCase())) {
                    customerSelect.selectedIndex = i;
                    break;
                }
            }
        }

        // 2. Add Items
        if (data.items && data.items.length > 0) {
            // Clear existing empty items if any (handled by addItem)

            data.items.forEach((item, index) => {
                // Call the global addItem function from create_invoice.html
                if (typeof window.addItem === 'function') {
                    window.addItem();

                    // The new item will be at index + 1 (since 1-based usually, but let's check logic)
                    // addItem increments itemCount. We can access the last added item.
                    // Actually, create_invoice.html uses a global itemCount.
                    // We need to find the inputs for the current itemCount.

                    // Since we are running this sequentially, the itemCount will be incremented.
                    // We can assume the inputs are named product_{itemCount}_id

                    const currentCount = window.itemCount; // Access global variable

                    const productSelect = document.querySelector(`select[name="product_${currentCount}_id"]`);
                    const quantityInput = document.querySelector(`input[name="quantity_${currentCount}"]`);

                    if (item.product_id && productSelect) {
                        productSelect.value = item.product_id;
                        // Trigger change to update price
                        productSelect.dispatchEvent(new Event('change'));
                    } else if (item.product_name && productSelect) {
                        // Try to match by name
                        for (let i = 0; i < productSelect.options.length; i++) {
                            if (productSelect.options[i].text.toLowerCase().includes(item.product_name.toLowerCase())) {
                                productSelect.selectedIndex = i;
                                productSelect.dispatchEvent(new Event('change'));
                                break;
                            }
                        }
                    }

                    if (quantityInput) {
                        quantityInput.value = item.quantity;
                        quantityInput.dispatchEvent(new Event('change'));
                    }
                }
            });
        }
    }
}

// Initialize
window.addEventListener('load', () => {
    window.aiAssistant = new AIAssistant();
});

