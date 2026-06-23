class AIAssistant {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.isSpeaking = false;
        this.synth = window.speechSynthesis;
        this.chatHistory = []; // Memory
        this.selectedLang = localStorage.getItem('ai_assistant_lang') || 'en-IN';
        
        // Listen to voice loading
        if (this.synth) {
            const onVoicesChanged = () => {
                console.log("SpeechSynthesis voices loaded/updated:", this.synth.getVoices().length);
            };
            if (typeof this.synth.addEventListener === 'function') {
                this.synth.addEventListener('voiceschanged', onVoicesChanged);
            } else {
                this.synth.onvoiceschanged = onVoicesChanged;
            }
        }

        this.initSpeechRecognition();
        this.createUI();
        this.loadChatHistory();
        this.checkAndPopulateInvoice(); // Check if we need to fill the form
        
        // Auto-apply saved theme on load
        const savedTheme = localStorage.getItem('ai_custom_theme');
        if (savedTheme) {
            this.applyAITheme(savedTheme);
        }
    }


    async loadChatHistory() {
        try {
            const response = await fetch('/api/ai/history');
            const data = await response.json();
            if (data.success && data.history && data.history.length > 0) {
                this.chatHistory = [];
                data.history.forEach(msg => {
                    const role = msg.role === 'user' ? 'user' : 'ai';
                    this.addHistoricMessage(msg.content, role);
                    this.chatHistory.push({ role: msg.role, content: msg.content });
                });
            }
        } catch (e) {
            console.error("Failed to load chat history:", e);
        }
    }

    addHistoricMessage(text, sender) {
        const container = document.getElementById('ai-chat-messages');
        if (!container) return;
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

    initSpeechRecognition() {
        if ('webkitSpeechRecognition' in window) {
            this.recognition = new webkitSpeechRecognition();
            this.recognition.continuous = true; // Keep listening through pauses
            this.recognition.interimResults = true; // Transcribe live word-by-word
            this.recognition.lang = this.selectedLang;
            this.silenceTimer = null;

            this.recognition.onstart = () => {
                this.isListening = true;
                this.updateUIState('listening');
                if (this.silenceTimer) clearTimeout(this.silenceTimer);
            };



            this.recognition.onend = () => {
                if (this.isListening) {
                    this.isListening = false;
                    this.updateUIState('idle');
                    
                    // Auto-submit text when recognition times out or ends automatically
                    const input = document.getElementById('ai-text-input');
                    const finalVal = input ? input.value.trim() : '';
                    if (finalVal) {
                        this.handleUserInput(finalVal);
                        if (input) input.value = '';
                    }
                }
                if (this.silenceTimer) clearTimeout(this.silenceTimer);
            };

            this.recognition.onresult = (event) => {
                let finalTranscript = '';
                let interimTranscript = '';

                for (let i = 0; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        finalTranscript += event.results[i][0].transcript;
                    } else {
                        interimTranscript += event.results[i][0].transcript;
                    }
                }

                // Show live transcribing text in the input box word-by-word
                const liveText = finalTranscript + interimTranscript;
                const input = document.getElementById('ai-text-input');
                if (input) {
                    input.value = liveText;
                }

                // Silence detection: reset timer every time speech is detected
                if (this.silenceTimer) {
                    clearTimeout(this.silenceTimer);
                }

                // If user stops speaking for 2.5 seconds, auto-submit the sentence
                this.silenceTimer = setTimeout(() => {
                    if (this.isListening) {
                        this.isListening = false;
                        this.updateUIState('idle');
                        this.recognition.stop(); // Stop recording
                        
                        const finalVal = input ? input.value.trim() : '';
                        if (finalVal) {
                            this.handleUserInput(finalVal);
                            if (input) input.value = '';
                        }
                    }
                }, 2500);
            };

            this.recognition.onerror = (event) => {
                console.error('Speech recognition error', event.error);
                this.isListening = false;
                this.updateUIState('idle');
                if (this.silenceTimer) clearTimeout(this.silenceTimer);
                if (event.error !== 'no-speech' && event.error !== 'aborted') {
                    this.speak("Sorry, there was a speech recognition error.");
                }
            };
        } else {
            console.warn('Speech recognition not supported');
        }
    }

    handleLanguageChange(newLang) {
        this.selectedLang = newLang;
        localStorage.setItem('ai_assistant_lang', newLang);
        
        let globalCode = 'en';
        if (newLang === 'hi-IN') globalCode = 'hi';
        else if (newLang === 'fr-FR') globalCode = 'fr';
        else if (newLang === 'es-ES') globalCode = 'es';
        else if (newLang === 'de-DE') globalCode = 'de';
        else if (newLang === 'ja-JP') globalCode = 'ja';

        if (typeof window.setGlobalLanguage === 'function') {
            window.setGlobalLanguage(globalCode);
        } else {
            window.location.reload();
        }
    }

    getWelcomeMessage(lang) {
        const welcomeTexts = {
            'en-IN': `Hi! I can help you:<br>
                      • <strong>Database Insights:</strong> "Show business insights" or "How is business?"<br>
                      • <strong>Voice Navigation:</strong> "Go to products", "Show analytics", "Create invoice"<br>
                      • <strong>Add products:</strong> "Add product Milk price 50 stock 100"<br>
                      • <strong>Add customers:</strong> "Add customer John email john@example.com"<br>
                      • <strong>Create invoices:</strong> "Bill for Riya: 2 milks and 1 bread"<br><br>
                      Try saying a command or click one of the quick commands below!`,
            'en-US': `Hi! I can help you:<br>
                      • <strong>Database Insights:</strong> "Show business insights" or "How is business?"<br>
                      • <strong>Voice Navigation:</strong> "Go to products", "Show analytics", "Create invoice"<br>
                      • <strong>Add products:</strong> "Add product Milk price 50 stock 100"<br>
                      • <strong>Add customers:</strong> "Add customer John email john@example.com"<br>
                      • <strong>Create invoices:</strong> "Bill for Riya: 2 milks and 1 bread"<br><br>
                      Try saying a command or click one of the quick commands below!`,
            'hi-IN': `नमस्ते! मैं आपकी मदद कर सकता हूँ:<br>
                      • <strong>बिज़नेस इनसाइट्स:</strong> "बिजनेस कैसा चल रहा है" या "व्यापार रिपोर्ट दिखाएं"<br>
                      • <strong>नेविगेशन:</strong> "प्रोडक्ट्स पर जाएं", "एनालिटिक्स दिखाएं", "इनवॉइस बनाएं"<br>
                      • <strong>उत्पाद जोड़ें:</strong> "add product Milk price 50 stock 100"<br>
                      • <strong>ग्राहक जोड़ें:</strong> "add customer John email john@example.com"<br>
                      • <strong>इनवॉइस बनाएं:</strong> "Bill for Riya: 2 milks and 1 bread"<br><br>
                      नीचे दिए गए कमांड्स पर क्लिक करें या माइक बटन दबाकर बोलें!`,
            'fr-FR': `Bonjour! Je peux vous aider à:<br>
                      • <strong>Statistiques:</strong> "Afficher les perspectives commerciales" ou "Comment vont les affaires?"<br>
                      • <strong>Navigation:</strong> "Aller aux produits", "Afficher les analyses", "Créer une facture"<br>
                      • <strong>Ajouter un produit:</strong> "add product Lait price 50 stock 100"<br>
                      • <strong>Ajouter un client:</strong> "add customer Jean email jean@example.com"<br>
                      • <strong>Facturer:</strong> "Bill for Riya: 2 milks and 1 bread"<br><br>
                      Essayez de dire une commande ou cliquez sur l'un des boutons ci-dessous!`,
            'es-ES': `¡Hola! Puedo ayudarte a:<br>
                      • <strong>Estadísticas:</strong> "Mostrar información comercial" o "¿Cómo va el negocio?"<br>
                      • <strong>Navegación:</strong> "Ir a productos", "Mostrar análisis", "Crear factura"<br>
                      • <strong>Añadir producto:</strong> "add product Leche price 50 stock 100"<br>
                      • <strong>Añadir cliente:</strong> "add customer Juan email juan@example.com"<br>
                      • <strong>Facturar:</strong> "Bill for Riya: 2 milks and 1 bread"<br><br>
                      ¡Intenta decir un comando o haz clic en uno de los accesos directos!`,
            'de-DE': `Hallo! Ich kann Ihnen helfen:<br>
                      • <strong>Geschäftseinblicke:</strong> "Geschäftszahlen anzeigen" oder "Wie läuft das Geschäft?"<br>
                      • <strong>Navigation:</strong> "Gehe zu Produkten", "Analysen anzeigen", "Rechnung erstellen"<br>
                      • <strong>Produkt hinzufügen:</strong> "add product Milch price 50 stock 100"<br>
                      • <strong>Kunde hinzufügen:</strong> "add customer Johann email johann@example.com"<br>
                      • <strong>Abrechnen:</strong> "Bill for Riya: 2 milks and 1 bread"<br><br>
                      Sprechen Sie einen Befehl oder klicken Sie auf eine der Kurzwahltasten!`,
            'ja-JP': `こんにちは！どのようなご用件でしょうか：<br>
                      • <strong>ビジネス分析:</strong> 「ビジネスレポートを見せて」または「業績はどう？」<br>
                      • <strong>音声ナビゲーション:</strong> 「商品一覧へ移動」、「分析を見せて」、「請求書作成」<br>
                      • <strong>商品追加:</strong> 「add product 牛乳 price 50 stock 100」<br>
                      • <strong>顧客追加:</strong> 「add customer 鈴木 email suzuki@example.com」<br>
                      • <strong>請求書作成:</strong> 「Bill for Riya: 2 milks and 1 bread」<br><br>
                      コマンドを話しかけるか、下のクイックボタンをクリックしてください！`
        };
        return welcomeTexts[lang] || welcomeTexts['en-IN'];
    }

    getPillButtonsHtml(lang) {
        const pills = {
            'en-IN': [
                { text: 'Insights', cmd: 'Show business insights', icon: 'fa-chart-line' },
                { text: 'Products', cmd: 'Go to products', icon: 'fa-box' },
                { text: 'Analytics', cmd: 'Show analytics', icon: 'fa-chart-bar' },
                { text: 'Create Invoice', cmd: 'Create invoice', icon: 'fa-plus' }
            ],
            'en-US': [
                { text: 'Insights', cmd: 'Show business insights', icon: 'fa-chart-line' },
                { text: 'Products', cmd: 'Go to products', icon: 'fa-box' },
                { text: 'Analytics', cmd: 'Show analytics', icon: 'fa-chart-bar' },
                { text: 'Create Invoice', cmd: 'Create invoice', icon: 'fa-plus' }
            ],
            'hi-IN': [
                { text: 'इनसाइट्स', cmd: 'व्यापार रिपोर्ट दिखाएं', icon: 'fa-chart-line' },
                { text: 'उत्पाद', cmd: 'प्रोडक्ट्स पर जाएं', icon: 'fa-box' },
                { text: 'एनालिटिक्स', cmd: 'एनालिटिक्स दिखाएं', icon: 'fa-chart-bar' },
                { text: 'इनवॉइस बनाएं', cmd: 'इनवॉइस बनाएं', icon: 'fa-plus' }
            ],
            'fr-FR': [
                { text: 'Statistiques', cmd: 'Afficher les perspectives commerciales', icon: 'fa-chart-line' },
                { text: 'Produits', cmd: 'Aller aux produits', icon: 'fa-box' },
                { text: 'Analyses', cmd: 'Afficher les analyses', icon: 'fa-chart-bar' },
                { text: 'Créer Facture', cmd: 'Créer une facture', icon: 'fa-plus' }
            ],
            'es-ES': [
                { text: 'Estadísticas', cmd: 'Mostrar información comercial', icon: 'fa-chart-line' },
                { text: 'Productos', cmd: 'Ir a productos', icon: 'fa-box' },
                { text: 'Análisis', cmd: 'Mostrar análisis', icon: 'fa-chart-bar' },
                { text: 'Crear Factura', cmd: 'Crear factura', icon: 'fa-plus' }
            ],
            'de-DE': [
                { text: 'Geschäftszahlen', cmd: 'Geschäftszahlen anzeigen', icon: 'fa-chart-line' },
                { text: 'Produkte', cmd: 'Gehe zu Produkten', icon: 'fa-box' },
                { text: 'Analysen', cmd: 'Analysen anzeigen', icon: 'fa-chart-bar' },
                { text: 'Rechnung Erstellen', cmd: 'Rechnung erstellen', icon: 'fa-plus' }
            ],
            'ja-JP': [
                { text: 'ビジネス分析', cmd: 'ビジネスレポートを見せて', icon: 'fa-chart-line' },
                { text: '商品一覧', cmd: '商品一覧へ移動', icon: 'fa-box' },
                { text: '分析センター', cmd: '分析を見せて', icon: 'fa-chart-bar' },
                { text: '請求書作成', cmd: '請求書作成', icon: 'fa-plus' }
            ]
        };
        const langPills = pills[lang] || pills['en-IN'];
        return langPills.map(p => `
            <button class="ai-pill-btn" onclick="window.aiAssistant.sendQuickCommand('${p.cmd}')">
                <i class="fas ${p.icon}"></i> ${p.text}
            </button>
        `).join('');
    }

    getUIPlaceholder(state, lang) {
        const placeholders = {
            'en-IN': { idle: 'Type or click mic to speak...', listening: 'Listening... Speak now...' },
            'en-US': { idle: 'Type or click mic to speak...', listening: 'Listening... Speak now...' },
            'hi-IN': { idle: 'टाइप करें या बोलने के लिए माइक दबाएं...', listening: 'सुन रहा हूँ... बोलिए...' },
            'fr-FR': { idle: 'Écrivez ou cliquez sur le micro pour parler...', listening: 'Écoute en cours... Parlez maintenant...' },
            'es-ES': { idle: 'Escribe o presiona el micro para hablar...', listening: 'Escuchando... Hable ahora...' },
            'de-DE': { idle: 'Tippen oder Mikrofon drücken...', listening: 'Hören... Sprechen Sie jetzt...' },
            'ja-JP': { idle: '入力するか、マイクをクリックして話す...', listening: '聞き取り中... お話しください...' }
        };
        const langPack = placeholders[lang] || placeholders['en-IN'];
        return langPack[state] || langPack['idle'];
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

        // Welcome entry animation sequence & hover effects with GSAP
        const mainBtn = container.querySelector('#ai-assistant-btn');
        if (mainBtn && typeof gsap !== 'undefined') {
            // Set starting hidden state
            gsap.set(mainBtn, { scale: 0, opacity: 0 });

            let entryPlayed = false;
            const playEntry = () => {
                if (entryPlayed) return;
                entryPlayed = true;
                
                gsap.fromTo(mainBtn, 
                    { scale: 0, opacity: 0 }, 
                    { 
                        scale: 1, 
                        opacity: 1, 
                        duration: 0.8, 
                        ease: 'back.out(2)', 
                        clearProps: 'opacity',
                        delay: 0.45 // Pop up shortly after dashboard elements reveal
                    }
                );
            };

            // Coordinate with page intro animations
            if (window.navbarIntroActive) {
                window.addEventListener('navbar-intro-complete', playEntry, { once: true });
                setTimeout(playEntry, 3000); // Safety fallback
            } else {
                const loader = document.getElementById('page-loader');
                const isLoaderActive = loader && !loader.classList.contains('fade-out');

                if (isLoaderActive) {
                    window.addEventListener('page-loader-hidden', playEntry, { once: true });
                    setTimeout(playEntry, 1800); // Safety fallback
                } else {
                    playEntry();
                }
            }

            mainBtn.addEventListener('mouseenter', () => {
                const icon = mainBtn.querySelector('.ai-btn-content i');
                gsap.to(mainBtn, {
                    y: -3,
                    x: -3,
                    scale: 1.05,
                    boxShadow: '7px 7px 0px #000000',
                    duration: 0.25,
                    ease: 'power2.out'
                });
                if (icon) {
                    gsap.to(icon, {
                        rotate: 15,
                        scale: 1.05,
                        duration: 0.35,
                        ease: 'power2.out'
                    });
                }
            });
            mainBtn.addEventListener('mouseleave', () => {
                const icon = mainBtn.querySelector('.ai-btn-content i');
                gsap.to(mainBtn, {
                    y: 0,
                    x: 0,
                    scale: 1,
                    boxShadow: '4px 4px 0px #000000',
                    duration: 0.45,
                    ease: 'back.out(1.8)'
                });
                if (icon) {
                    gsap.to(icon, {
                        rotate: 0,
                        scale: 1,
                        duration: 0.45,
                        ease: 'back.out(1.8)'
                    });
                }
            });
        }

        // Create Chat Modal (hidden by default)
        const modal = document.createElement('div');
        modal.id = 'ai-chat-modal';
        modal.className = 'ai-chat-modal';
        
        const welcomeHtml = this.getWelcomeMessage(this.selectedLang);
        const pillsHtml = this.getPillButtonsHtml(this.selectedLang);
        
        modal.innerHTML = `
            <div class="ai-modal-header">
                <h3 class="ai-modal-title"><i class="fas fa-robot"></i> Billing Assistant</h3>
                <div class="ai-lang-container">
                    <select id="ai-lang-select" class="ai-lang-select" title="Change Assistant Language">
                        <option value="en-IN" ${this.selectedLang === 'en-IN' ? 'selected' : ''}>🇬🇧 English</option>
                        <option value="hi-IN" ${this.selectedLang === 'hi-IN' ? 'selected' : ''}>🇮🇳 हिन्दी</option>
                        <option value="fr-FR" ${this.selectedLang === 'fr-FR' ? 'selected' : ''}>🇫🇷 Français</option>
                        <option value="es-ES" ${this.selectedLang === 'es-ES' ? 'selected' : ''}>🇪🇸 Español</option>
                        <option value="de-DE" ${this.selectedLang === 'de-DE' ? 'selected' : ''}>🇩🇪 Deutsch</option>
                        <option value="ja-JP" ${this.selectedLang === 'ja-JP' ? 'selected' : ''}>🇯🇵 日本語</option>
                    </select>
                </div>
                <button id="ai-close-btn" class="ai-close-btn" title="Close">×</button>
            </div>
            <div id="ai-chat-messages" class="ai-messages">
                <div class="ai-message ai">
                    <div class="ai-avatar"><i class="fas fa-robot"></i></div>
                    <div class="ai-text" id="ai-welcome-text">${welcomeHtml}</div>
                </div>
            </div>
            <div class="ai-quick-pills" id="ai-quick-pills">
                ${pillsHtml}
            </div>
            <div class="ai-input-area">
                <div class="ai-mic-wrapper">
                    <button id="ai-mic-btn" class="ai-mic-btn" style="position: relative; z-index: 2;" title="Speak command"><i class="fas fa-microphone"></i></button>
                </div>
                <input type="text" id="ai-text-input" class="ai-input" placeholder="${this.getUIPlaceholder('idle', this.selectedLang)}">
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
        
        // Language selector change
        const langSelect = document.getElementById('ai-lang-select');
        if (langSelect) {
            langSelect.onchange = (e) => {
                this.handleLanguageChange(e.target.value);
            };
        }
        
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
            
            // GSAP elastic scale-expand opening animation from the bottom-right trigger button
            if (typeof gsap !== 'undefined') {
                gsap.fromTo(modal,
                    { opacity: 0, scale: 0.3, y: 50, x: 50 },
                    { opacity: 1, scale: 1, y: 0, x: 0, duration: 0.5, ease: 'back.out(1.4)' }
                );

                // Stagger reveal quick action command pills
                const pills = modal.querySelectorAll('.ai-pill-btn');
                if (pills.length > 0) {
                    gsap.fromTo(pills,
                        { opacity: 0, y: 15, scale: 0.9 },
                        { opacity: 1, y: 0, scale: 1, stagger: 0.06, duration: 0.45, ease: 'back.out(1.5)', delay: 0.2 }
                    );
                }
            }
            
            const input = document.getElementById('ai-text-input');
            if (input) input.focus();
        }
    }

    closeChatModal() {
        const modal = document.getElementById('ai-chat-modal');
        if (modal) {
            if (typeof gsap !== 'undefined') {
                gsap.to(modal, {
                    opacity: 0,
                    scale: 0.3,
                    y: 50,
                    x: 50,
                    duration: 0.35,
                    ease: 'power2.in',
                    onComplete: () => {
                        modal.classList.remove('active');
                    }
                });
            } else {
                modal.classList.remove('active');
            }
        }
        if (this.synth) {
            this.synth.cancel();
        }
        this.stopRippleEffect();
        this.updateUIState('idle');
    }

    toggleListening() {
        if (this.synth && (this.isSpeaking || this.synth.speaking)) {
            this.isSpeaking = false;
            this.synth.cancel();
            this.updateUIState('idle');
            return;
        }

        if (!this.recognition) {
            alert("Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.");
            return;
        }

        try {
            if (this.isListening) {
                this.isListening = false;
                this.updateUIState('idle');
                if (this.silenceTimer) clearTimeout(this.silenceTimer);
                this.recognition.stop();

                // Auto-submit text if present when stopped manually
                const input = document.getElementById('ai-text-input');
                const finalVal = input ? input.value.trim() : '';
                if (finalVal) {
                    this.handleUserInput(finalVal);
                    if (input) input.value = '';
                }
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
        const currentLang = this.selectedLang || 'en-IN';
        
        if (state === 'listening') {
            if (micBtn) {
                micBtn.innerHTML = '<i class="fas fa-stop" style="color: #ff3b30;"></i>';
                micBtn.classList.add('listening');
                micBtn.classList.remove('speaking');
                micBtn.title = "Stop listening";
            }
            if (mainBtn) {
                mainBtn.classList.add('listening');
            }
            if (textInput) {
                textInput.placeholder = this.getUIPlaceholder('listening', currentLang);
                textInput.value = '';
            }
            this.startRippleEffect('listening');
        } else if (state === 'speaking') {
            if (micBtn) {
                micBtn.innerHTML = '<i class="fas fa-stop" style="color: #ff3b30;"></i>';
                micBtn.classList.add('speaking');
                micBtn.classList.remove('listening');
                micBtn.title = "Stop Speaking";
            }
            if (mainBtn) {
                mainBtn.classList.remove('listening');
            }
            this.startRippleEffect('speaking');
        } else {
            if (micBtn) {
                micBtn.innerHTML = '<i class="fas fa-microphone"></i>';
                micBtn.classList.remove('listening');
                micBtn.classList.remove('speaking');
                micBtn.title = "Speak command";
            }
            if (mainBtn) {
                mainBtn.classList.remove('listening');
            }
            if (textInput) {
                textInput.placeholder = this.getUIPlaceholder('idle', currentLang);
            }
            this.stopRippleEffect();
        }
    }

    startRippleEffect(mode) {
        this.stopRippleEffect(); // Clear any existing ripples first

        const container = document.getElementById('ai-assistant-container');
        const micWrapper = document.querySelector('.ai-mic-wrapper');
        
        if (typeof gsap === 'undefined') return;

        this.rippleTimelines = [];

        // 1. Concentric ripples behind the main floating button
        if (container) {
            const btn = document.getElementById('ai-assistant-btn');
            for (let i = 0; i < 3; i++) {
                const ring = document.createElement('div');
                ring.className = `ai-pulse-ring ${mode}`;
                container.insertBefore(ring, btn); // Insert behind the button

                const tl = gsap.timeline({ repeat: -1 });
                tl.fromTo(ring,
                    { scale: 1, opacity: 0.6 },
                    { scale: 2.2, opacity: 0, duration: 1.5, ease: 'power1.out', delay: i * 0.5 }
                );
                this.rippleTimelines.push({ element: ring, tl: tl });
            }
        }

        // 2. Concentric ripples behind the inner mic button
        if (micWrapper) {
            const micBtn = document.getElementById('ai-mic-btn');
            for (let i = 0; i < 3; i++) {
                const ring = document.createElement('div');
                ring.className = `ai-mic-pulse-ring ${mode}`;
                micWrapper.insertBefore(ring, micBtn); // Insert behind the mic button

                const tl = gsap.timeline({ repeat: -1 });
                tl.fromTo(ring,
                    { scale: 1, opacity: 0.6 },
                    { scale: 2.2, opacity: 0, duration: 1.5, ease: 'power1.out', delay: i * 0.5 }
                );
                this.rippleTimelines.push({ element: ring, tl: tl });
            }
        }
    }

    stopRippleEffect() {
        if (this.rippleTimelines) {
            this.rippleTimelines.forEach(item => {
                try {
                    item.tl.kill();
                    item.element.remove();
                } catch (e) {}
            });
        }
        this.rippleTimelines = [];
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

        // GSAP Staggered message entry animation
        if (typeof gsap !== 'undefined') {
            const avatar = div.querySelector('.ai-avatar');
            const bubble = div.querySelector('.ai-text');
            
            if (avatar && bubble) {
                // Set initial hidden styles
                gsap.set(avatar, { scale: 0, rotation: -35 });
                gsap.set(bubble, { opacity: 0, scale: 0.85, x: sender === 'user' ? 35 : -35 });

                const tl = gsap.timeline();
                // 1. Pop avatar with bouncy rotation
                tl.to(avatar, {
                    scale: 1,
                    rotation: 0,
                    duration: 0.45,
                    ease: 'back.out(1.8)'
                });
                // 2. Bounce text bubble with dynamic slide-in
                tl.to(bubble, {
                    opacity: 1,
                    scale: 1,
                    x: 0,
                    duration: 0.5,
                    ease: 'back.out(1.4)'
                }, '-=0.35');
            }
        }
    }

    async handleUserInput(text) {
        this.addMessage(text, 'user');
        this.chatHistory.push({ role: 'user', content: text });

        const textLower = text.toLowerCase().trim();
        if (this.checkThemeCommand(textLower)) {
            return;
        }


        // Show loading
        const loadingId = 'ai-loading-' + Date.now();
        const container = document.getElementById('ai-chat-messages');
        const loadingDiv = document.createElement('div');
        loadingDiv.id = loadingId;
        loadingDiv.className = 'ai-message ai';
        loadingDiv.innerHTML = `
            <div class="ai-avatar"><i class="fas fa-robot"></i></div>
            <div class="ai-text" style="display: flex; align-items: center; justify-content: center; min-width: 180px; padding: 14px 20px;">
                <div class="loader" style="--main-size: 2.2em;">
                    <div class="text"><span>KHATA</span></div>
                    <div class="text"><span>KHATA</span></div>
                    <div class="text"><span>KHATA</span></div>
                    <div class="text"><span>KHATA</span></div>
                    <div class="text"><span>KHATA</span></div>
                    <div class="text"><span>KHATA</span></div>
                    <div class="text"><span>KHATA</span></div>
                    <div class="text"><span>KHATA</span></div>
                    <div class="text"><span>KHATA</span></div>
                    <div class="line"></div>
                </div>
            </div>
        `;
        container.appendChild(loadingDiv);
        container.scrollTop = container.scrollHeight;

        try {
            const response = await fetch('/api/ai/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    history: this.chatHistory,
                    language: this.selectedLang
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
            // If the intent is missing information, we do NOT execute the intent action yet.
            // We just let the conversational flow continue to gather info.
            if (data.missing_info) {
                console.log("Missing info for intent " + data.intent + ": " + data.missing_info);
                return;
            }

            if (data.intent === 'navigation') {
                this.handleNavigation(data.data);
            } else if (data.intent === 'business_insights') {
                this.showBusinessInsights(data.data);
            } else if (data.intent === 'create_invoice') {
                // Show invoice preview card for confirmation first, instead of redirecting immediately
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
            } else if (data.intent === 'db_operation') {
                if (data.success) {
                    setTimeout(() => {
                        window.location.reload();
                    }, 1800);
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
            
            // Strip emojis and markdown formatting but preserve accents, Devanagari, and CJK characters
            cleanText = cleanText.replace(/[\u2700-\u27BF]|[\uE000-\uF8FF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|[\u2011-\u26FF]|\uD83E[\uDD10-\uDDFF]/g, '');
            cleanText = cleanText.replace(/\*/g, '').replace(/\s+/g, ' ').trim();

            const currentLang = this.selectedLang || 'en-IN';
            // Pronunciation workaround for Hindi offline voices (e.g. Kalpana) where "है" and "हैं" are mispronounced as "हो"
            if (currentLang.startsWith('hi')) {
                // Standalone "हैं" is replaced with "हए"
                cleanText = cleanText.replace(/(\s|^)हैं(\s|$|[.,!?;:।])/g, '$1हए$2');
                // Standalone "है" is replaced with "हए" which bypasses the Kalpana pronunciation bug
                cleanText = cleanText.replace(/(\s|^)है(\s|$|[.,!?;:।])/g, '$1हए$2');
            }

            if (cleanText) {
                const utterance = new SpeechSynthesisUtterance(cleanText);
                
                this.isSpeaking = true;
                this.updateUIState('speaking');

                utterance.onend = () => {
                    if (this.isSpeaking) {
                        this.isSpeaking = false;
                        this.updateUIState('idle');
                    }
                };
                
                // Add error handling to resume/cancel if it gets stuck
                utterance.onerror = (event) => {
                    console.error('SpeechSynthesisUtterance error:', event.error);
                    if (this.isSpeaking) {
                        this.isSpeaking = false;
                        this.synth.cancel();
                        this.updateUIState('idle');
                    }
                };

                // Find voice corresponding to the selected language
                const voices = this.synth.getVoices();
                let selectedVoice = null;

                // Priority filters for high-quality natural voices per language
                const voicePreferences = {
                    'en-IN': ['google in english', 'google us english', 'microsoft ravina', 'microsoft heera', 'en-in'],
                    'en-US': ['google us english', 'google uk english', 'samantha', 'microsoft david', 'microsoft zira', 'en-us'],
                    'hi-IN': ['google हिन्दी', 'google hindi', 'microsoft ananya', 'microsoft swara', 'microsoft kalpana', 'microsoft hemant', 'hi-in'],
                    'fr-FR': ['google français', 'google french', 'microsoft hortense', 'microsoft julie', 'fr-fr'],
                    'es-ES': ['google español', 'google spanish', 'microsoft helena', 'microsoft laura', 'es-es'],
                    'de-DE': ['google deutsch', 'google german', 'microsoft hedda', 'microsoft stefan', 'de-de'],
                    'ja-JP': ['google 日本語', 'google japanese', 'microsoft haruka', 'microsoft ichiro', 'ja-jp']
                };

                const currentLang = this.selectedLang || 'en-IN';
                const prefs = voicePreferences[currentLang] || [];

                // 1. Try to match preferred natural voice substrings
                for (const pref of prefs) {
                    selectedVoice = voices.find(v => {
                        const nameLower = v.name.toLowerCase();
                        const langLower = v.lang.toLowerCase().replace('_', '-');
                        return nameLower.includes(pref) || langLower === pref;
                    });
                    if (selectedVoice) break;
                }

                // 2. Fallback: match lang code prefix
                if (!selectedVoice) {
                    const langPrefix = currentLang.split('-')[0].toLowerCase();
                    selectedVoice = voices.find(v => v.lang.toLowerCase().startsWith(langPrefix));
                }

                if (selectedVoice) {
                    utterance.voice = selectedVoice;
                }
                
                utterance.lang = currentLang;

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
        
        if (typeof gsap !== 'undefined') {
            gsap.fromTo(previewDiv,
                { opacity: 0, scale: 0.7, y: 30 },
                { opacity: 1, scale: 1, y: 0, duration: 0.5, ease: 'back.out(1.6)' }
            );
        }
        
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
        
        if (typeof gsap !== 'undefined') {
            gsap.fromTo(previewDiv,
                { opacity: 0, scale: 0.7, y: 30 },
                { opacity: 1, scale: 1, y: 0, duration: 0.5, ease: 'back.out(1.6)' }
            );
        }
        
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
        
        if (typeof gsap !== 'undefined') {
            gsap.fromTo(previewDiv,
                { opacity: 0, scale: 0.7, y: 30 },
                { opacity: 1, scale: 1, y: 0, duration: 0.5, ease: 'back.out(1.6)' }
            );
        }
        
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
                if (typeof window.navigateToPage === 'function' && data.target !== 'logout') {
                    window.navigateToPage(url).then(() => {
                        // Remove transition overlay smoothly after load completes
                        const overlay = document.querySelector('.ai-transition-overlay');
                        if (overlay) {
                            overlay.classList.remove('active');
                            setTimeout(() => overlay.remove(), 300);
                        }
                    });
                } else {
                    window.location.href = url;
                }
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
                <div class="loader" style="--main-size: 5em; margin-bottom: 24px;">
                    <div class="text"><span>KHATA</span></div>
                    <div class="text"><span>KHATA</span></div>
                    <div class="text"><span>KHATA</span></div>
                    <div class="text"><span>KHATA</span></div>
                    <div class="text"><span>KHATA</span></div>
                    <div class="text"><span>KHATA</span></div>
                    <div class="text"><span>KHATA</span></div>
                    <div class="text"><span>KHATA</span></div>
                    <div class="text"><span>KHATA</span></div>
                    <div class="line"></div>
                </div>
                <div class="ai-transition-text" style="font-family: 'Montserrat', 'Inter', sans-serif; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; font-size: 14px;">Navigating to ${names[target] || target}...</div>
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
        const customerSelect = document.querySelector('select[name="customer_id"]');
        let customerMatched = false;
        
        if (data.customer_id && customerSelect) {
            customerSelect.value = data.customer_id;
            if (customerSelect.value === data.customer_id) {
                customerMatched = true;
            }
        }
        
        if (!customerMatched && data.customer_name && customerSelect) {
            // Try to find matching customer in the dropdown options
            for (let i = 0; i < customerSelect.options.length; i++) {
                if (customerSelect.options[i].text.toLowerCase().includes(data.customer_name.toLowerCase())) {
                    customerSelect.selectedIndex = i;
                    customerSelect.dispatchEvent(new Event('change'));
                    customerMatched = true;
                    break;
                }
            }
        }
        
        // If it's a new customer and not matched, create a temporary customer inline
        if (!customerMatched && data.customer_name) {
            const tempNameInput = document.querySelector('input[name="new_customer_name"]');
            const tempEmailInput = document.querySelector('input[name="new_customer_email"]');
            const tempPhoneInput = document.querySelector('input[name="new_customer_phone"]');
            const tempAddrInput = document.querySelector('textarea[name="new_customer_address"]');
            
            if (tempNameInput && tempEmailInput && tempPhoneInput && tempAddrInput) {
                tempNameInput.value = data.customer_name;
                tempEmailInput.value = data.customer_email || `${data.customer_name.toLowerCase().replace(/\s+/g, '')}@example.com`;
                tempPhoneInput.value = data.customer_phone || '9999999999';
                tempAddrInput.value = data.customer_address || 'New Customer Address';
                
                if (typeof window.addNewCustomer === 'function') {
                    window.addNewCustomer();
                }
            }
        }

        let allProductsMatched = true;

        // 2. Add Items
        if (data.items && data.items.length > 0) {
            data.items.forEach((item, index) => {
                // Call the global addItem function from create_invoice.html
                if (typeof window.addItem === 'function') {
                    window.addItem();

                    const productSelects = document.querySelectorAll('#items-container select.product-select');
                    const productSelect = productSelects[productSelects.length - 1];

                    const quantityInputs = document.querySelectorAll('#items-container input.quantity-input');
                    const quantityInput = quantityInputs[quantityInputs.length - 1];

                    const discountInputs = document.querySelectorAll('#items-container input.discount-input');
                    const discountInput = discountInputs[discountInputs.length - 1];

                    let matched = false;
                    if (item.product_id && productSelect) {
                        productSelect.value = item.product_id;
                        if (productSelect.value === item.product_id) {
                            productSelect.dispatchEvent(new Event('change'));
                            matched = true;
                        }
                    } 
                    
                    if (!matched && item.product_name && productSelect) {
                        // Try robust name matching
                        const cleanQuery = item.product_name.toLowerCase().replace(/[^a-z0-9]/g, '');
                        let bestMatchIndex = -1;
                        let bestMatchScore = 0;
                        
                        for (let i = 0; i < productSelect.options.length; i++) {
                            const optionText = productSelect.options[i].text;
                            const cleanOption = optionText.toLowerCase().replace(/[^a-z0-9]/g, '');
                            
                            // Check if option contains the clean query
                            if (cleanOption.includes(cleanQuery)) {
                                bestMatchIndex = i;
                                break;
                            }
                            
                            // Fallback: word-overlap matching
                            const queryWords = item.product_name.toLowerCase().split(/\s+/).filter(w => w.length > 1);
                            let matchCount = 0;
                            queryWords.forEach(word => {
                                if (optionText.toLowerCase().includes(word)) {
                                    matchCount++;
                                }
                            });
                            
                            if (matchCount > bestMatchScore) {
                                bestMatchScore = matchCount;
                                bestMatchIndex = i;
                            }
                        }
                        
                        if (bestMatchIndex !== -1) {
                            productSelect.selectedIndex = bestMatchIndex;
                            productSelect.dispatchEvent(new Event('change'));
                            matched = true;
                        }
                    }

                    if (!matched) {
                        allProductsMatched = false;
                    }

                    if (quantityInput) {
                        quantityInput.value = item.quantity;
                        quantityInput.dispatchEvent(new Event('change'));
                    }

                    if (item.discount !== undefined && discountInput) {
                        discountInput.value = item.discount;
                        discountInput.dispatchEvent(new Event('change'));
                    }
                }
            });
        }

        // 3. Set Tax and Due Date
        if (data.tax !== undefined && data.tax !== null) {
            const taxInput = document.getElementById('tax-input');
            if (taxInput) {
                taxInput.value = data.tax;
                taxInput.dispatchEvent(new Event('input'));
            }
        }

        if (data.due_date) {
            const dueDateInput = document.querySelector('input[name="due_date"]');
            if (dueDateInput) {
                dueDateInput.value = data.due_date;
            }
        }

        // 4. Automatically submit the form to create the invoice instantly if all products matched
        if (allProductsMatched) {
            setTimeout(() => {
                const form = document.querySelector('form.invoice-form');
                if (form) {
                    form.submit();
                }
            }, 1000); // 1-second delay to show the user the filled form briefly before creation
        } else {
            this.addMessage("⚠️ Some products could not be matched automatically. Please select them manually below.", 'ai');
        }
    }

    checkThemeCommand(text) {
        const themeMap = {
            'cyberpunk': ['cyberpunk', 'cyber', 'neon', 'futuristic'],
            'glassmorphism': ['glassmorphic', 'glassmorphism', 'glass', 'glassy', 'emerald'],
            'sunset': ['sunset', 'gold', 'amber', 'orange', 'warm'],
            'retro': ['retro', 'terminal', 'matrix', 'classic green'],
            'indigo': ['indigo', 'space', 'galaxy', 'dark blue', 'violet'],
            'default': ['default', 'reset', 'standard', 'original', 'khata']
        };

        let matchedTheme = null;
        for (const [themeName, keywords] of Object.entries(themeMap)) {
            if (keywords.some(kw => text.includes(kw))) {
                matchedTheme = themeName;
                break;
            }
        }

        if (matchedTheme) {
            this.applyAITheme(matchedTheme);
            return true;
        }
        return false;
    }

    applyAITheme(themeName) {
        const existingStyle = document.getElementById('ai-custom-theme-style');
        if (existingStyle) {
            existingStyle.remove();
        }
        
        const scanlines = document.getElementById('ai-retro-scanlines');
        if (scanlines) {
            scanlines.remove();
        }

        if (themeName === 'default') {
            localStorage.removeItem('ai_custom_theme');
            this.addMessage("Reverted to default Khata theme.", 'ai');
            this.speak("Reverted to default theme.");
            return;
        }

        localStorage.setItem('ai_custom_theme', themeName);

        let css = '';
        let themeDisplayName = '';
        let welcomeVoice = '';

        if (themeName === 'cyberpunk') {
            themeDisplayName = 'Cyberpunk Neon';
            welcomeVoice = "Cyberpunk theme activated. Systems operational in neon mode.";
            css = `
                body {
                    background-color: #0b0c10 !important;
                    background-image: radial-gradient(circle at 50% 50%, #1f2833 0%, #0b0c10 100%) !important;
                    color: #00f0ff !important;
                    font-family: 'Montserrat', sans-serif !important;
                }
                .card, .header, .table, .dashboard-card, .ai-chat-modal, .seller-sidebar, .card-body, .modal-content {
                    background: rgba(20, 21, 33, 0.85) !important;
                    border: 1px solid #ff007f !important;
                    box-shadow: 0 0 15px rgba(255, 0, 127, 0.25) !important;
                    backdrop-filter: blur(12px) !important;
                    -webkit-backdrop-filter: blur(12px) !important;
                }
                .btn-primary, .btn-submit, button[type="submit"], .ai-assistant-btn {
                    background: linear-gradient(135deg, #ff007f, #00f0ff) !important;
                    color: #ffffff !important;
                    border: none !important;
                    box-shadow: 0 0 10px rgba(255, 0, 127, 0.5) !important;
                    text-transform: uppercase !important;
                    letter-spacing: 1px !important;
                }
                .btn-outline {
                    border: 1px solid #00f0ff !important;
                    color: #00f0ff !important;
                    background: transparent !important;
                }
                .btn-outline:hover {
                    background: #00f0ff !important;
                    color: #000000 !important;
                }
                h1, h2, h3, h4, h5, h6, th, strong, .section-title, .ai-modal-title {
                    color: #ff007f !important;
                    text-shadow: 0 0 5px rgba(255, 0, 127, 0.5) !important;
                }
                td, span, p, label, div {
                    color: #e2e8f0 !important;
                }
                input, select, textarea, .form-input {
                    background-color: #1f2833 !important;
                    border: 1px solid #00f0ff !important;
                    color: #00f0ff !important;
                }
                .ai-insights-alert-row.alert-warning {
                    background: rgba(245, 158, 11, 0.1) !important;
                    border: 1px solid #f59e0b !important;
                }
                div[class*="bg-surface"], div[class*="bg-background"], main, section {
                    background-color: #0b0c10 !important;
                }
                div[class*="bg-surface-container"] {
                    background-color: rgba(20, 21, 33, 0.85) !important;
                    border: 1px solid #ff007f !important;
                    box-shadow: 0 0 15px rgba(255, 0, 127, 0.25) !important;
                }
                div[class*="text-on-surface"], p[class*="text-on-surface"], span[class*="text-on-surface"] {
                    color: #e2e8f0 !important;
                }
                span[class*="text-primary"], div[class*="text-primary"] {
                    color: #00f0ff !important;
                }
            `;
        } else if (themeName === 'glassmorphism') {
            themeDisplayName = 'Glassmorphic Emerald';
            welcomeVoice = "Glassmorphic Emerald theme applied. Ambient transparency established.";
            css = `
                body {
                    background: linear-gradient(135deg, #0d2b1d 0%, #153e2a 50%, #0d2b1d 100%) !important;
                    color: #d1fae5 !important;
                }
                .card, .header, .table, .dashboard-card, .ai-chat-modal, .seller-sidebar, .card-body, .modal-content {
                    background: rgba(255, 255, 255, 0.05) !important;
                    border: 1px solid rgba(255, 255, 255, 0.12) !important;
                    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3) !important;
                    backdrop-filter: blur(18px) !important;
                    -webkit-backdrop-filter: blur(18px) !important;
                    border-radius: 16px !important;
                }
                .btn-primary, .btn-submit, button[type="submit"], .ai-assistant-btn {
                    background: linear-gradient(135deg, #10b981, #059669) !important;
                    color: #ffffff !important;
                    border: 1px solid rgba(255, 255, 255, 0.2) !important;
                    box-shadow: 0 8px 20px rgba(16, 185, 129, 0.2) !important;
                    border-radius: 8px !important;
                }
                .btn-outline {
                    border: 1px solid rgba(255, 255, 255, 0.3) !important;
                    color: #ffffff !important;
                    background: rgba(255, 255, 255, 0.05) !important;
                }
                .btn-outline:hover {
                    background: #10b981 !important;
                    color: #ffffff !important;
                }
                h1, h2, h3, h4, h5, h6, th, strong, .section-title, .ai-modal-title {
                    color: #34d399 !important;
                }
                td, span, p, label, div {
                    color: #ecfdf5 !important;
                }
                input, select, textarea, .form-input {
                    background: rgba(255, 255, 255, 0.08) !important;
                    border: 1px solid rgba(255, 255, 255, 0.2) !important;
                    color: #ffffff !important;
                    backdrop-filter: blur(10px) !important;
                }
                div[class*="bg-surface"], div[class*="bg-background"], main, section {
                    background-color: transparent !important;
                }
                div[class*="bg-surface-container"] {
                    background: rgba(255, 255, 255, 0.05) !important;
                    border: 1px solid rgba(255, 255, 255, 0.12) !important;
                    backdrop-filter: blur(18px) !important;
                }
            `;
        } else if (themeName === 'sunset') {
            themeDisplayName = 'Sunset Gold';
            welcomeVoice = "Sunset gold theme activated. Bask in the warm twilight.";
            css = `
                body {
                    background: linear-gradient(135deg, #1a1625 0%, #2a2233 100%) !important;
                    color: #f7fafc !important;
                }
                .card, .header, .table, .dashboard-card, .ai-chat-modal, .seller-sidebar, .card-body, .modal-content {
                    background: rgba(30, 27, 40, 0.85) !important;
                    border: 1px solid #f5af19 !important;
                    box-shadow: 0 0 15px rgba(245, 175, 25, 0.15) !important;
                    border-radius: 12px !important;
                }
                .btn-primary, .btn-submit, button[type="submit"], .ai-assistant-btn {
                    background: linear-gradient(135deg, #f12711, #f5af19) !important;
                    color: #ffffff !important;
                    border: none !important;
                    box-shadow: 0 4px 15px rgba(245, 175, 25, 0.3) !important;
                }
                .btn-outline {
                    border: 1px solid #f5af19 !important;
                    color: #f5af19 !important;
                    background: transparent !important;
                }
                .btn-outline:hover {
                    background: #f5af19 !important;
                    color: #000000 !important;
                }
                h1, h2, h3, h4, h5, h6, th, strong, .section-title, .ai-modal-title {
                    color: #f5af19 !important;
                }
                td, span, p, label, div {
                    color: #f7fafc !important;
                }
                input, select, textarea, .form-input {
                    background-color: #2a2233 !important;
                    border: 1px solid #f5af19 !important;
                    color: #ffffff !important;
                }
                div[class*="bg-surface"], div[class*="bg-background"], main, section {
                    background-color: #1a1625 !important;
                }
                div[class*="bg-surface-container"] {
                    background-color: rgba(30, 27, 40, 0.85) !important;
                    border: 1px solid #f5af19 !important;
                }
            `;
        } else if (themeName === 'retro') {
            themeDisplayName = 'Retro Matrix Terminal';
            welcomeVoice = "Access granted. Retro terminal mode activated.";
            css = `
                body {
                    background-color: #000000 !important;
                    color: #39ff14 !important;
                    font-family: 'Courier New', Courier, monospace !important;
                }
                .card, .header, .table, .dashboard-card, .ai-chat-modal, .seller-sidebar, .card-body, .modal-content {
                    background: #000000 !important;
                    border: 2px solid #39ff14 !important;
                    border-radius: 0px !important;
                    box-shadow: 0 0 10px rgba(57, 255, 20, 0.2) !important;
                }
                .btn-primary, .btn-submit, button[type="submit"], .ai-assistant-btn {
                    background: #39ff14 !important;
                    color: #000000 !important;
                    border: 2px solid #39ff14 !important;
                    font-weight: bold !important;
                    border-radius: 0px !important;
                    box-shadow: 0 0 8px rgba(57, 255, 20, 0.4) !important;
                    text-transform: uppercase !important;
                }
                .btn-outline {
                    border: 1px solid #39ff14 !important;
                    color: #39ff14 !important;
                    background: transparent !important;
                    border-radius: 0px !important;
                }
                .btn-outline:hover {
                    background: #39ff14 !important;
                    color: #000000 !important;
                }
                h1, h2, h3, h4, h5, h6, th, strong, .section-title, .ai-modal-title {
                    color: #39ff14 !important;
                    text-shadow: 0 0 5px rgba(57, 255, 20, 0.5) !important;
                }
                td, span, p, label, div {
                    color: #39ff14 !important;
                    font-family: 'Courier New', Courier, monospace !important;
                }
                input, select, textarea, .form-input {
                    background-color: #000000 !important;
                    border: 1px solid #39ff14 !important;
                    color: #39ff14 !important;
                    border-radius: 0px !important;
                }
                div[class*="bg-surface"], div[class*="bg-background"], main, section {
                    background-color: #000000 !important;
                }
                div[class*="bg-surface-container"] {
                    background-color: #000000 !important;
                    border: 2px solid #39ff14 !important;
                }
                div[class*="text-on-surface"], p[class*="text-on-surface"], span[class*="text-on-surface"] {
                    color: #39ff14 !important;
                }
            `;
            
            const scanlineOverlay = document.createElement('div');
            scanlineOverlay.id = 'ai-retro-scanlines';
            scanlineOverlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
                background-size: 100% 4px, 6px 100%;
                z-index: 999999;
                pointer-events: none;
                opacity: 0.85;
            `;
            document.body.appendChild(scanlineOverlay);
        } else if (themeName === 'indigo') {
            themeDisplayName = 'Deep Space Indigo';
            welcomeVoice = "Quantum space coordinate lock. Indigo mode enabled.";
            css = `
                body {
                    background: linear-gradient(135deg, #0b091a 0%, #17153a 50%, #0b091a 100%) !important;
                    color: #e0e7ff !important;
                }
                .card, .header, .table, .dashboard-card, .ai-chat-modal, .seller-sidebar, .card-body, .modal-content {
                    background: rgba(15, 12, 38, 0.8) !important;
                    border: 1px solid #6366f1 !important;
                    box-shadow: 0 0 20px rgba(99, 102, 241, 0.2) !important;
                    border-radius: 20px !important;
                }
                .btn-primary, .btn-submit, button[type="submit"], .ai-assistant-btn {
                    background: linear-gradient(135deg, #4f46e5, #818cf8) !important;
                    color: #ffffff !important;
                    border: none !important;
                    box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4) !important;
                    border-radius: 10px !important;
                }
                .btn-outline {
                    border: 1px solid #818cf8 !important;
                    color: #818cf8 !important;
                    background: transparent !important;
                }
                .btn-outline:hover {
                    background: #818cf8 !important;
                    color: #000000 !important;
                }
                h1, h2, h3, h4, h5, h6, th, strong, .section-title, .ai-modal-title {
                    color: #c7d2fe !important;
                    text-shadow: 0 0 8px rgba(99, 102, 241, 0.6) !important;
                }
                td, span, p, label, div {
                    color: #e0e7ff !important;
                }
                input, select, textarea, .form-input {
                    background-color: #17153a !important;
                    border: 1px solid #6366f1 !important;
                    color: #ffffff !important;
                }
                div[class*="bg-surface"], div[class*="bg-background"], main, section {
                    background-color: transparent !important;
                }
                div[class*="bg-surface-container"] {
                    background-color: rgba(15, 12, 38, 0.8) !important;
                    border: 1px solid #6366f1 !important;
                }
            `;
        }

        const style = document.createElement('style');
        style.id = 'ai-custom-theme-style';
        style.textContent = css;
        document.head.appendChild(style);

        this.addMessage(`🎨 Activated the <strong>${themeDisplayName}</strong> theme!`, 'ai');
        this.speak(welcomeVoice);
    }
}


// Initialize
window.addEventListener('load', () => {
    window.aiAssistant = new AIAssistant();
});

