const API_BASE_URL = 'http://localhost:8000';

let currentThreadId = null;
let currentUserId = document.getElementById('userId').value;

document.getElementById('messageInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Auto-resize textarea
document.getElementById('messageInput').addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 200) + 'px';
});

document.getElementById('userId').addEventListener('change', function(e) {
    currentUserId = e.target.value;
});

function useQuickPrompt(text) {
    document.getElementById('messageInput').value = text;
    sendMessage();
}

async function sendMessage() {
    const inputEl = document.getElementById('messageInput');
    const message = inputEl.value.trim();
    const userId = document.getElementById('userId').value;
    
    if (!message) return;
    
    // Hide welcome message on first message
    document.getElementById('welcomeMessage').style.display = 'none';
    
    addMessage(message, 'user');
    inputEl.value = '';
    inputEl.style.height = 'auto';
    
    setStatus('Processing your request...');
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                user_id: userId,
                thread_id: currentThreadId
            }),
        });
        
        const data = await response.json();
        currentThreadId = data.thread_id;
        
        // Add assistant messages
        let hasAssistantMessage = false;
        data.messages.forEach(msg => {
            if (msg.role === 'assistant') {
                addMessage(msg.content, 'assistant');
                hasAssistantMessage = true;
            }
        });
        
        // Display recommendations if any
        if (data.recommendations && data.recommendations.length > 0) {
            displayRecommendations(data.recommendations, userId, currentThreadId);
        } else {
            document.getElementById('recommendations').innerHTML = '';
        }
        
        setStatus(`Ready`);
        
        // Scroll to bottom
        scrollToBottom();
    } catch (error) {
        console.error('Error:', error);
        setStatus('Error: Failed to send message');
        addMessage('Sorry, there was an error processing your request.', 'assistant');
    }
}

function addMessage(content, role) {
    const messagesContainer = document.getElementById('messages');
    const messageEl = document.createElement('div');
    messageEl.className = `message ${role}`;
    messageEl.textContent = content;
    messagesContainer.appendChild(messageEl);
    scrollToBottom();
}

function displayRecommendations(recommendations, userId, threadId) {
    const container = document.getElementById('recommendations');
    container.innerHTML = '';
    
    recommendations.forEach(rec => {
        const card = document.createElement('div');
        card.className = 'recommendation-card';
        
        let content = `
            <span class="type-badge ${rec.type}">${rec.type.toUpperCase()}</span>
            <h3>${rec.name}</h3>
        `;
        
        if (rec.departure && rec.destination) {
            content += `
                <div class="info-row">
                    <span>From</span>
                    <span>${rec.departure}</span>
                </div>
                <div class="info-row">
                    <span>To</span>
                    <span>${rec.destination}</span>
                </div>
            `;
        }
        
        if (rec.departure_time && rec.arrival_time) {
            content += `
                <div class="info-row">
                    <span>Departure</span>
                    <span>${rec.departure_time}</span>
                </div>
                <div class="info-row">
                    <span>Arrival</span>
                    <span>${rec.arrival_time}</span>
                </div>
                <div class="info-row">
                    <span>Duration</span>
                    <span>${rec.duration}</span>
                </div>
            `;
        }
        
        if (rec.details && rec.details.rating) {
            content += `
                <div class="info-row">
                    <span>Rating</span>
                    <span>${rec.details.rating} ⭐</span>
                </div>
            `;
        }
        
        content += `
            <div class="price">¥${rec.price.toFixed(2)}</div>
            <button class="book-btn" onclick="bookItem('${rec.type}', '${rec.id}', '${rec.departure || ''}', '${rec.destination || ''}', '${rec.date || ''}', '${userId}', '${threadId}')">
                Book Now
            </button>
        `;
        
        card.innerHTML = content;
        container.appendChild(card);
    });
    
    scrollToBottom();
}

async function bookItem(type, id, departure, destination, date, userId, threadId) {
    const requestData = {
        action: "book",
        type: type,
        user_id: userId,
        thread_id: threadId,
        departure: departure || null,
        destination: destination || null,
        date: date || null
    };
    
    if (type === 'train') {
        requestData.train_no = id;
    } else if (type === 'flight') {
        requestData.flight_no = id;
    } else if (type === 'hotel') {
        requestData.hotel_id = id;
    }
    
    setStatus('Processing booking...');
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/order/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData),
        });
        
        const result = await response.json();
        
        if (result.success) {
            addMessage(`✅ ${result.message}`, 'assistant');
            setStatus(`Booking completed. Order ID: ${result.order_id}`);
            document.getElementById('recommendations').innerHTML = '';
        } else {
            alert('Booking failed: ' + result.message);
            setStatus('Booking failed');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error processing booking');
        setStatus('Error: Booking failed');
    }
    
    scrollToBottom();
}

function setStatus(message) {
    document.getElementById('status').textContent = message;
}

function startVoiceInput() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('Speech recognition is not supported in your browser');
        return;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    recognition.lang = 'zh-CN';
    recognition.interimResults = false;
    
    const voiceBtn = document.getElementById('voiceBtn');
    voiceBtn.classList.add('recording');
    setStatus('Listening... speak now');
    
    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        document.getElementById('messageInput').value = transcript;
        setStatus('Voice captured');
    };
    
    recognition.onend = function() {
        voiceBtn.classList.remove('recording');
    };
    
    recognition.onerror = function(event) {
        console.error('Speech recognition error', event.error);
        setStatus('Error: ' + event.error);
        voiceBtn.classList.remove('recording');
    };
    
    recognition.start();
}

function scrollToBottom() {
    const container = document.getElementById('chatContainer');
    container.scrollTop = container.scrollHeight;
}
