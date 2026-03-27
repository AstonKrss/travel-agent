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
    
    document.getElementById('welcomeMessage').style.display = 'none';
    
    addMessage(message, 'user');
    inputEl.value = '';
    inputEl.style.height = 'auto';
    
    // 不要立即设置状态，会被后续的 status 消息覆盖
    
    // 创建流式请求
    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
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
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let messageContainer = null;
    
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                try {
                    const data = JSON.parse(line.slice(6));
                    
                    if (data.type === 'start') {
                        currentThreadId = data.thread_id || currentThreadId;
                        setStatus('正在思考...');
                        // 清除之前的推荐卡片
                        document.getElementById('recommendations').style.display = 'none';
                        document.getElementById('recommendations-list').innerHTML = '';
                    } else if (data.type === 'status') {
                        // 显示状态消息，不创建消息容器
                        setStatus(data.message);
                    } else if (data.type === 'message') {
                        // 跳过重复的空消息
                        if (!data.content || data.content.trim() === '') {
                            continue;
                        }
                        
                        // 检查是否与最后一条消息相同，避免重复
                        const messages = document.querySelectorAll('.message.assistant');
                        const lastMsg = messages[messages.length - 1];
                        if (lastMsg && lastMsg.textContent === data.content) {
                            continue;
                        }
                        
                        // 如果还没有消息容器，创建并添加到界面
                        if (!messageContainer) {
                            const messagesContainer = document.getElementById('messages');
                            messageContainer = document.createElement('div');
                            messageContainer.className = 'message assistant';
                            messageContainer.textContent = '';
                            messagesContainer.appendChild(messageContainer);
                        }
                        // 追加内容
                        messageContainer.textContent += data.content;
                        setStatus('正在输入...');
                    } else if (data.type === 'clear') {
                        // 清除占位消息
                        if (messageContainer) {
                            messageContainer.remove();
                            messageContainer = null;
                        }
                    } else if (data.type === 'recommendation_category') {
                        // 显示推荐分类标题
                        document.getElementById('recommendations').style.display = 'block';
                        displayRecommendationCategory(data.category, data.title);
                    } else if (data.type === 'recommendation') {
                        // 流式显示单个推荐卡片
                        document.getElementById('recommendations').style.display = 'block';
                        displaySingleRecommendation(data.data, userId, currentThreadId);
                    } else if (data.type === 'recommendations_done') {
                        // 推荐显示完成
                        setStatus('请选择出行方案');
                    } else if (data.type === 'done') {
                        setStatus('完成');
                        messageContainer = null;
                    } else if (data.type === 'error') {
                        addMessage('抱歉，出了点问题: ' + data.message, 'assistant');
                    }
                } catch (e) {}
            }
        }
    }
    
    scrollToBottom();
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

function displayRecommendationCategory(category, title) {
    const container = document.getElementById('recommendations-list');
    const categoryEl = document.createElement('div');
    categoryEl.className = 'recommendation-category';
    categoryEl.textContent = title;
    container.appendChild(categoryEl);
    scrollToBottom();
}

function displaySingleRecommendation(rec, userId, threadId) {
    const container = document.getElementById('recommendations-list');
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
    card.style.animation = 'slideIn 0.3s ease-out';
    container.appendChild(card);
    scrollToBottom();
}

function createRecommendationCard(rec, userId, threadId) {
    const card = document.createElement('div');
    card.className = 'recommendation-card-inline';
    
    let content = `
        <span class="type-badge ${rec.type}">${rec.type.toUpperCase()}</span>
        <span class="rec-name">${rec.name}</span>
    `;
    
    if (rec.departure_time && rec.arrival_time) {
        content += `
            <span class="rec-time">${rec.departure_time} → ${rec.arrival_time}</span>
        `;
    }
    
    if (rec.duration) {
        content += `<span class="rec-duration">${rec.duration}</span>`;
    }
    
    content += `<span class="rec-price">¥${rec.price.toFixed(2)}</span>`;
    
    card.innerHTML = content;
    return card;
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

function hideRecommendations() {
    document.getElementById('recommendations').style.display = 'none';
    document.getElementById('recommendations-list').innerHTML = '';
}

function scrollToBottom() {
    const container = document.getElementById('chatContainer');
    container.scrollTop = container.scrollHeight;
}
