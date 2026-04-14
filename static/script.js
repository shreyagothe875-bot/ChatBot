(function () {
    "use strict";

    // --- Element Selectors (Now safely scoped inside this function) ---
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatBox = document.getElementById('chat-box');
    const flashcardBtn = document.getElementById('flashcard-btn');
    const historyBtn = document.getElementById('history-btn');
    const backBtn = document.getElementById('back-btn');

    // --- Core Functions ---
    async function loadHistory() {
        try {
            const response = await fetch('/history');
            const data = await response.json();
            chatBox.innerHTML = '';
            data.forEach(item => {
                appendMessage(item.user, 'user-msg');
                appendMessage(item.bot, 'bot-msg');
            });
            backBtn.style.display = 'inline-block';
            historyBtn.style.display = 'none';
        } catch (e) { console.error(e); }
    }

    function exitHistory() {
        backBtn.style.display = 'none';
        historyBtn.style.display = 'inline-block';
        chatBox.innerHTML = '<div class="bot-msg message">Protocol Initialized.</div>';
    }

    function appendMessage(text, className) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${className}`;
        msgDiv.innerText = text;
        chatBox.appendChild(msgDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // --- Event Listeners ---
    if (chatForm) {
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const message = userInput.value;
            appendMessage(message, 'user-msg');
            userInput.value = '';
            // Fetch /chat logic here...
        });
    }

    // --- Global Export ---
    // This part is CRITICAL: It allows onclick="" in HTML to find these functions
    window.loadHistory = loadHistory;
    window.exitHistory = exitHistory;

})();