// --- Element Selectors ---
const sendBtn = document.getElementById('send-btn');
const userInput = document.getElementById('user-input');
const chatBox = document.getElementById('chat-box');
const typingIndicator = document.getElementById('typing-indicator');
const greetingContainer = document.getElementById('greeting');

const historyBtn = document.getElementById('history-btn');
const closeHistoryBtn = document.getElementById('close-history-btn');
const historyModal = document.getElementById('history-modal');
const historyList = document.getElementById('history-list');

const micBtn = document.getElementById('mic-btn');
const audioToggleBtn = document.getElementById('audio-toggle-btn');
const uploadBtn = document.getElementById('upload-btn');
const fileUpload = document.getElementById('file-upload');

// Study Mode Selectors
const studyOverlay = document.getElementById('study-mode');
const closeStudyBtn = document.getElementById('close-study-btn');
const largeFlashcard = document.getElementById('large-flashcard');
const prevCardBtn = document.getElementById('prev-card-btn');
const nextCardBtn = document.getElementById('next-card-btn');
const cardCounter = document.getElementById('card-counter');
const flashcardBtn = document.getElementById('flashcard-btn');

// --- State Variables ---
let currentDeck = [];
let currentCardIndex = 0;
let audioEnabled = false;
let selectedFile = null;

// --- 1. Navigation & UI Logic ---

function appendMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender);
    const contentDiv = document.createElement('div');
    contentDiv.classList.add('msg-content');
    contentDiv.innerHTML = sender === 'bot' ? marked.parse(text) : text;

    messageDiv.appendChild(contentDiv);
    chatBox.insertBefore(messageDiv, typingIndicator);
    chatBox.scrollTop = chatBox.scrollHeight;

    if (sender === 'bot') {
        contentDiv.querySelectorAll('pre code').forEach((block) => hljs.highlightElement(block));
    }
}

// Function to ENTER Study Mode
function openStudyMode(data) {
    currentDeck = data;
    currentCardIndex = 0;
    updateCardDisplay();
    document.querySelector('.app-container').classList.add('hidden');
    studyOverlay.classList.remove('hidden');
}

// Function to EXIT Study Mode (The Back Button)
function exitStudyMode() {
    studyOverlay.classList.add('hidden');
    document.querySelector('.app-container').classList.remove('hidden');
}

function updateCardDisplay() {
    if (!currentDeck || currentDeck.length === 0) return;

    largeFlashcard.classList.remove('flipped');

    const card = currentDeck[currentCardIndex];
    document.getElementById('card-front-text').innerText = card.question || "No Question Provided";
    document.getElementById('card-back-text').innerText = card.answer || "No Answer Provided";

    cardCounter.innerText = `${currentCardIndex + 1} / ${currentDeck.length}`;
    prevCardBtn.disabled = (currentCardIndex === 0);
    nextCardBtn.disabled = (currentCardIndex === currentDeck.length - 1);
}

// --- 2. Event Listeners ---

// Flashcard Generation
flashcardBtn.addEventListener('click', async () => {
    if (greetingContainer) greetingContainer.classList.add('hidden');
    typingIndicator.classList.remove('hidden');

    try {
        const response = await fetch('/generate_flashcards', { method: 'POST' });
        const data = await response.json();
        typingIndicator.classList.add('hidden');

        if (data.error) {
            alert(data.error);
            return;
        }

        if (!Array.isArray(data) || data.length === 0) {
            alert("Please chat about a topic first so I can generate cards!");
            return;
        }

        openStudyMode(data);
    } catch (error) {
        typingIndicator.classList.add('hidden');

        // This prints the REAL reason it crashed to your browser console
        console.error("💥 ACTUAL JAVASCRIPT ERROR:", error);

        alert("UI Error: Press F12 and check the Console tab to see what crashed!");
    }
});

// Flashcard Controls
largeFlashcard.addEventListener('click', () => largeFlashcard.classList.toggle('flipped'));

prevCardBtn.addEventListener('click', () => {
    if (currentCardIndex > 0) {
        currentCardIndex--;
        updateCardDisplay();
    }
});

nextCardBtn.addEventListener('click', () => {
    if (currentCardIndex < currentDeck.length - 1) {
        currentCardIndex++;
        updateCardDisplay();
    }
});

// Use querySelector for the back button specifically
document.querySelector('.study-back-btn').addEventListener('click', exitStudyMode);

// --- 3. Audio & Voice (TTS & STT) ---
function speakText(text) {
    if (!audioEnabled) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.speak(utterance);
}

audioToggleBtn.addEventListener('click', () => {
    audioEnabled = !audioEnabled;
    audioToggleBtn.textContent = audioEnabled ? '🔊' : '🔇';
    if (!audioEnabled) window.speechSynthesis.cancel();
});

const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognitionAPI) {
    const recognition = new SpeechRecognitionAPI();
    micBtn.addEventListener('click', () => {
        recognition.start();
        micBtn.textContent = '🔴';
    });
    recognition.onresult = (event) => {
        userInput.value = event.results[0][0].transcript;
        sendMessage();
    };
    recognition.onend = () => micBtn.textContent = '🎤';
}

// --- 4. Chat Logic ---
async function sendMessage() {
    const messageText = userInput.value.trim();
    if (!messageText && !selectedFile) return;

    if (greetingContainer) greetingContainer.classList.add('hidden');
    appendMessage(messageText, 'user');
    userInput.value = '';
    typingIndicator.classList.remove('hidden');

    try {
        const formData = new FormData();
        formData.append('message', messageText);
        if (selectedFile) formData.append('file', selectedFile);

        const response = await fetch('/chat', { method: 'POST', body: formData });
        const data = await response.json();

        typingIndicator.classList.add('hidden');
        appendMessage(data.response, 'bot');
        speakText(data.response.replace(/[*#`_]/g, ''));

        selectedFile = null;
        fileUpload.value = '';
    } catch (error) {
        typingIndicator.classList.add('hidden');
        appendMessage("Connection lost. Please check your server.", 'bot');
    }
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });

// History Logic
historyBtn.addEventListener('click', async () => {
    historyModal.classList.remove('hidden');
    const response = await fetch('/history');
    const history = await response.json();
    historyList.innerHTML = history.map(chat => `
        <div class="history-item">
            <p><strong>You:</strong> ${chat.user}</p>
            <p><strong>P.A.C.E:</strong> ${chat.bot.substring(0, 50)}...</p>
        </div>
    `).join('');
});

closeHistoryBtn.addEventListener('click', () => historyModal.classList.add('hidden'));

window.onload = () => userInput.focus();