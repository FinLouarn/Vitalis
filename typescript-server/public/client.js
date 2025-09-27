document.addEventListener("DOMContentLoaded", () => {
    const transcriptArea = document.getElementById("transcript-area");
    const startVoiceBtn = document.getElementById("start-voice-btn");
    const sendTextBtn = document.getElementById("send-text-btn");
    const userInput = document.getElementById("user-input");

    // Conversation history to maintain context for the AI
    let conversationHistory = [];

    // Initialize Web Speech Recognition
    const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    let isListening = false;

    // Check if we're in a secure context (HTTPS or localhost)
    const isSecureContext = window.isSecureContext || location.protocol === 'https:' || location.hostname === 'localhost';
    
    if (SpeechRecognition && isSecureContext) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.lang = "en-US";
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
            isListening = true;
            startVoiceBtn.textContent = "🛑 Listening...";
            startVoiceBtn.style.backgroundColor = "#dc3545";
            console.log("Voice recognition started.");
            appendTranscript("System", "Listening for your voice... Speak now.", "default");
        };

        recognition.onresult = (event) => {
            const last = event.results.length - 1;
            const transcript = event.results[last][0].transcript;
            console.log("User said:", transcript);
            userInput.value = transcript;
            sendMessage(transcript);
        };

        recognition.onerror = (event) => {
            console.error("Recognition error:", event.error);
            stopListening();
            
            let errorMessage = "Voice recognition error. ";
            switch(event.error) {
                case 'not-allowed':
                    errorMessage += "Microphone access denied. Please allow microphone access and try again.";
                    break;
                case 'no-speech':
                    errorMessage += "No speech detected. Please try again.";
                    break;
                case 'audio-capture':
                    errorMessage += "No microphone found or audio capture failed.";
                    break;
                case 'network':
                    errorMessage += "Network error occurred. Check your connection.";
                    break;
                case 'service-not-allowed':
                    errorMessage += "Speech recognition service not allowed.";
                    break;
                default:
                    errorMessage += `Error: ${event.error}. Please try again or use text input.`;
            }
            
            appendTranscript("System", errorMessage, "error");
        };

        recognition.onend = () => {
            stopListening();
        };
    } else {
        let message = "Voice input not available. ";
        if (!SpeechRecognition) {
            message += "Your browser does not support speech recognition.";
        } else if (!isSecureContext) {
            message += "Voice input requires a secure connection (HTTPS).";
        }
        
        startVoiceBtn.textContent = "Voice Unavailable";
        startVoiceBtn.disabled = true;
        appendTranscript("System", message, "error");
    }

    function stopListening() {
        if (isListening) {
            recognition.stop();
        }
        isListening = false;
        startVoiceBtn.textContent = "🎙️ Start Voice";
        startVoiceBtn.style.backgroundColor = "#007bff"; // Blue
    }

    startVoiceBtn.addEventListener("click", async () => {
        if (isListening) {
            stopListening();
        } else {
            // Check microphone permissions first
            try {
                if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    // Permission granted, stop the stream (we don't need it for speech recognition)
                    stream.getTracks().forEach(track => track.stop());
                }
                
                // Now try to start speech recognition
                recognition.start();
            } catch (permissionError) {
                console.error("Microphone permission error:", permissionError);
                appendTranscript(
                    "System", 
                    "Microphone access denied. Please allow microphone access in your browser settings and refresh the page.", 
                    "error"
                );
            }
        }
    });

    sendTextBtn.addEventListener("click", () => {
        const text = userInput.value.trim();
        if (text) {
            sendMessage(text);
        }
    });

    userInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            sendTextBtn.click();
        }
    });

    /**
     * Appends a message to the transcript area.
     * @param {string} sender - 'User' or 'AI' or 'System'.
     * @param {string} message - The message content.
     * @param {string} [type='default'] - Optional type for styling (e.g., 'error').
     */
    function appendTranscript(sender, message, type = "default") {
        const p = document.createElement("p");
        p.style.margin = "5px 0";
        p.style.wordWrap = "break-word";

        if (sender === "User") {
            p.innerHTML = `<strong style="color: #007bff;">You:</strong> ${message}`;
            p.style.textAlign = "right";
        } else if (sender === "AI") {
            p.innerHTML = `<strong style="color: #28a745;">AI:</strong> ${message}`;
            p.style.textAlign = "left";
        } else {
            // System or Error
            p.innerHTML = `<strong style="color: #6c757d;">System:</strong> ${message}`;
            if (type === "error") p.style.color = "red";
        }

        transcriptArea.appendChild(p);
        // Scroll to the bottom
        transcriptArea.scrollTop = transcriptArea.scrollHeight;
    }

    /**
     * Converts text to speech.
     * @param {string} text - The text to speak.
     */
    function speakText(text) {
        if ("speechSynthesis" in window) {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = "en-US";
            // Optional: Choose a voice if needed (e.g., utterance.voice = voices[0])
            window.speechSynthesis.speak(utterance);
        } else {
            console.warn("Text-to-Speech not supported in this browser.");
        }
    }

    /**
     * Sends the user's message to the server for AI processing.
     * @param {string} userText - The message from the user.
     */
    async function sendMessage(userText) {
        userInput.value = ""; // Clear input field

        // 1. Add user message to transcript and history
        appendTranscript("User", userText);
        conversationHistory.push({ role: "user", content: userText });

        // Disable input while waiting for response
        userInput.disabled = true;
        sendTextBtn.disabled = true;
        startVoiceBtn.disabled = true;

        // 2. Call the backend API
        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ messages: conversationHistory }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const aiMessage = await response.json();
            const aiText = aiMessage.content;

            // 3. Add AI message to transcript and history
            appendTranscript("AI", aiText);
            speakText(aiText);
            conversationHistory.push({ role: "assistant", content: aiText });
        } catch (error) {
            console.error("Error sending message:", error);
            appendTranscript(
                "System",
                "Could not connect to the AI service. Please check the server console.",
                "error",
            );
        } finally {
            // Re-enable input
            userInput.disabled = false;
            sendTextBtn.disabled = false;
            startVoiceBtn.disabled = false;
            userInput.focus();
        }
    }

    // Initiate the conversation (AI's first message)
    sendMessage(
        "Hello, I am a medical intake specialist. To begin, could you please tell me your gender?",
    );
});
