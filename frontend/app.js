const API = 'http://localhost:8000';
let threadId = null;
let isLoading = false;

// ── Init ──────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    const textarea = document.getElementById('msgInput');
    const sendBtn = document.getElementById('sendBtn');

    // Enter to send (Shift+Enter for newline)
    textarea.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            send();
        }
    });

    // Auto-resize textarea
    textarea.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    });

    // Tab navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', e => {
            e.preventDefault();
            switchTab(item.dataset.tab);
        });
    });

    // Build node progress bar
    buildProgressBar();

    // Connection indicator
    updateConnectionStatus('idle');
});

// ── Tab Navigation ────────────────────────────────────────────────────────

function switchTab(tab) {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelector(`.nav-item[data-tab="${tab}"]`).classList.add('active');
    document.getElementById(tab + 'Tab').classList.add('active');
    if (tab === 'state') refreshState();
}

// ── Progress Bar ───────────────────────────────────────────────────────────

const NODE_STEPS = [
    { id: 'intent',     label: '🧠 意图',     icon: '🧠' },
    { id: 'extractor', label: '📋 提取',     icon: '📋' },
    { id: 'tmc_query', label: '🔍 查询',     icon: '🔍' },
    { id: 'recommend', label: '🎯 推荐',     icon: '🎯' },
    { id: 'booker',     label: '📦 预订',     icon: '📦' },
];

let activeStepIdx = -1;
let completedSteps = new Set();

function buildProgressBar() {
    const bar = document.getElementById('progressBar');
    bar.innerHTML = NODE_STEPS.map((step, i) => `
        <div class="progress-step" id="step-${step.id}">
            <div class="step-dot"></div>
            <span>${step.label}</span>
        </div>
        ${i < NODE_STEPS.length - 1 ? '<span class="step-arrow">›</span>' : ''}
    `).join('');
}

function activateStep(nodeId) {
    const idx = NODE_STEPS.findIndex(s => s.id === nodeId);
    if (idx < 0) return;

    // Mark previous steps done
    for (let i = 0; i < idx; i++) {
        const el = document.getElementById(`step-${NODE_STEPS[i].id}`);
        if (el) { el.classList.remove('active'); el.classList.add('done'); completedSteps.add(NODE_STEPS[i].id); }
    }
    // Deactivate all, then activate current
    document.querySelectorAll('.progress-step').forEach(el => el.classList.remove('active'));
    const cur = document.getElementById(`step-${nodeId}`);
    if (cur) cur.classList.add('active');
    activeStepIdx = idx;
}

function completeAllSteps() {
    NODE_STEPS.forEach(step => {
        const el = document.getElementById(`step-${step.id}`);
        if (el) { el.classList.remove('active'); el.classList.add('done'); }
    });
    completedSteps.add('complete');
}

function resetProgressBar() {
    document.querySelectorAll('.progress-step').forEach(el => {
        el.classList.remove('active', 'done');
    });
    activeStepIdx = -1;
    completedSteps.clear();
}

// ── Connection Status ─────────────────────────────────────────────────────

function updateConnectionStatus(status) {
    const dot = document.getElementById('connDot');
    if (!dot) return;
    dot.className = 'connection-dot ' + (status || 'idle');
}

// ── Messages ───────────────────────────────────────────────────────────────

function hideWelcome() {
    const wc = document.getElementById('welcomeCard');
    if (wc) wc.style.display = 'none';
}

function addMsg(content, role = 'assistant', extraClass = '') {
    hideWelcome();
    const area = document.getElementById('messages');
    const el = document.createElement('div');
    el.className = `msg ${role}${extraClass ? ' ' + extraClass : ''}`;
    el.textContent = content;
    area.appendChild(el);
    area.scrollTop = area.scrollHeight;
    return el;
}

function setNodeStatus(text, state = '') {
    const el = document.getElementById('nodeStatus');
    el.textContent = text;
    el.className = 'node-status ' + state;
}

// ── Typing Indicator ───────────────────────────────────────────────────────

let typingEl = null;

function showTyping() {
    if (typingEl) return;
    hideWelcome();
    typingEl = document.createElement('div');
    typingEl.className = 'typing-indicator';
    typingEl.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <span style="font-size:11px;color:var(--text-dim);margin-left:6px;">思考中...</span>
    `;
    document.getElementById('messages').appendChild(typingEl);
    scrollBottom();
}

function hideTyping() {
    if (typingEl) { typingEl.remove(); typingEl = null; }
}

function scrollBottom() {
    const area = document.getElementById('messages');
    area.scrollTop = area.scrollHeight;
}

// ── Quick Prompts ─────────────────────────────────────────────────────────

function usePrompt(text) {
    document.getElementById('msgInput').value = text;
    send();
}

// ── Send Message ────────────────────────────────────────────────────────────

async function send() {
    const input = document.getElementById('msgInput');
    const msg = input.value.trim();
    const userId = document.getElementById('userId').value;
    if (!msg || isLoading) return;

    isLoading = true;
    document.getElementById('sendBtn').disabled = true;
    hideRecPanel();
    resetProgressBar();
    setNodeStatus('正在连接...', 'active');
    updateConnectionStatus('connecting');

    addMsg(msg, 'user');
    input.value = '';
    input.style.height = 'auto';

    try {
        const resp = await fetch(`${API}/api/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg, user_id: userId, thread_id: threadId }),
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

        threadId = resp.headers.get('X-Thread-Id') || threadId;
        document.getElementById('threadId').value = threadId || '';
        updateConnectionStatus('connected');

        await processStream(resp);

        setNodeStatus('✓ 完成', 'done');
        completeAllSteps();
    } catch (err) {
        console.error(err);
        setNodeStatus('✕ 连接失败', 'error');
        addMsg('连接失败，请确认服务已启动（python main.py）', 'assistant', 'error-msg');
        updateConnectionStatus('error');
    } finally {
        isLoading = false;
        document.getElementById('sendBtn').disabled = false;
    }
}

// ── SSE Stream Processing ─────────────────────────────────────────────────

let assistantMsgEl = null;

async function processStream(resp) {
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            try {
                const data = JSON.parse(line.slice(6));
                await handleSSEEvent(data);
            } catch (_) { /* skip malformed */ }
        }
    }
}

async function handleSSEEvent(data) {
    const { type } = data;

    if (type === 'start') {
        threadId = data.thread_id || threadId;
        setNodeStatus('已连接', 'active');
        return;
    }

    if (type === 'node') {
        activateStep(data.node);
        const labels = {
            intent: '正在识别意图...',
            chat: '正在回复...',
            extractor: '正在提取信息...',
            tmc_query: '正在查询方案...',
            recommend: '正在智能推荐...',
            booker: '正在执行预订...',
        };
        setNodeStatus(labels[data.node] || `执行 ${data.node}...`, 'active');
        showTyping();
        return;
    }

    if (type === 'message') {
        hideTyping();
        if (!assistantMsgEl) {
            assistantMsgEl = addMsg('', 'assistant');
        }
        assistantMsgEl.textContent += data.content;
        scrollBottom();
        return;
    }

    if (type === 'recommendation_category') {
        hideTyping();
        assistantMsgEl = null;
        showRecPanel();
        const catEl = document.createElement('div');
        catEl.className = 'rec-cat-label';
        catEl.textContent = data.title;
        document.getElementById('recList').appendChild(catEl);
        return;
    }

    if (type === 'recommendation') {
        hideTyping();
        assistantMsgEl = null;
        showRecPanel();
        addRecCard(data.data);
        return;
    }

    if (type === 'recommendations_done') {
        setNodeStatus('请选择出行方案', '');
        return;
    }

    if (type === 'approval_request') {
        hideTyping();
        assistantMsgEl = null;
        const area = document.getElementById('messages');
        const el = document.createElement('div');
        el.className = 'msg';
        el.style.cssText = 'background:var(--orange-dim);border:1px solid rgba(255,183,77,0.3);color:var(--orange);border-radius:12px;';
        el.innerHTML = `
            <strong>⚠️ 需要审批</strong><br><br>${data.reason}
            <div style="display:flex;gap:8px;margin-top:10px;">
                <button onclick="handleApproval('approve')" style="
                    flex:1;padding:8px;border:none;border-radius:6px;
                    background:var(--green);color:#fff;font-size:12px;font-weight:600;cursor:pointer;
                ">✅ 批准</button>
                <button onclick="handleApproval('reject')" style="
                    flex:1;padding:8px;border:none;border-radius:6px;
                    background:var(--red);color:#fff;font-size:12px;font-weight:600;cursor:pointer;
                ">❌ 拒绝</button>
            </div>`;
        area.appendChild(el);
        scrollBottom();
        return;
    }

    if (type === 'done') {
        hideTyping();
        setNodeStatus('✓ 完成', 'done');
        assistantMsgEl = null;
        return;
    }

    if (type === 'error') {
        hideTyping();
        addMsg('错误: ' + data.message, 'assistant', 'error-msg');
        assistantMsgEl = null;
        setNodeStatus('✕ 错误', 'error');
        return;
    }

    if (type === 'clear') {
        hideTyping();
        assistantMsgEl = null;
        return;
    }
}

// ── Recommendations ────────────────────────────────────────────────────────

function showRecPanel() {
    const panel = document.getElementById('recPanel');
    panel.style.display = 'block';
}

function hideRecPanel() {
    document.getElementById('recPanel').style.display = 'none';
    document.getElementById('recList').innerHTML = '';
}

function addRecCard(rec) {
    const list = document.getElementById('recList');
    const userId = document.getElementById('userId').value;

    const card = document.createElement('div');
    card.className = 'rec-card';
    card.dataset.id = rec.id;
    card.dataset.type = rec.type;

    const score = rec.score || 0;
    const scorePct = Math.round(Math.min(score / 100, 1) * 100);

    const typeLabel = { train: '高铁', flight: '航班', hotel: '酒店' }[rec.type] || rec.type;

    let extras = '';
    if (rec.departure_time && rec.arrival_time) {
        extras += `<div class="rec-detail-row"><span class="icon">🕐</span>${rec.departure_time} → ${rec.arrival_time} ${rec.duration ? '· ' + rec.duration : ''}</div>`;
    }
    if (rec.details) {
        if (rec.details.seat_class) extras += `<div class="rec-detail-row"><span class="icon">💺</span>${rec.details.seat_class}</div>`;
        if (rec.details.rating) extras += `<div class="rec-detail-row"><span class="icon">⭐</span>评分 ${rec.details.rating}</div>`;
        if (rec.details.breakfast !== undefined) extras += `<div class="rec-detail-row"><span class="icon">🍳</span>${rec.details.breakfast ? '含早餐' : '不含早餐'}</div>`;
        if (rec.details.aircraft) extras += `<div class="rec-detail-row"><span class="icon">✈</span>${rec.details.aircraft}</div>`;
    }
    if (rec.reason) {
        extras += `<div class="rec-detail-row" style="color:var(--accent);font-size:11px;"><span class="icon">💡</span>${rec.reason}</div>`;
    }

    card.innerHTML = `
        <div class="rec-card-top">
            <span class="badge ${rec.type}">${typeLabel}</span>
            <div class="score-badge">
                <div class="score-bar"><div class="score-fill" style="width:${scorePct}%"></div></div>
                <span>${score.toFixed(1)}</span>
            </div>
        </div>
        <h4>${rec.name}</h4>
        ${rec.departure && rec.destination ? `<div class="rec-detail-row"><span class="icon">📍</span>${rec.departure} → ${rec.destination}</div>` : ''}
        ${extras}
        <div class="rec-price">
            <span class="yen">¥</span>
            <span class="amount">${Number(rec.price).toLocaleString()}</span>
            <span class="unit">${rec.type === 'hotel' ? '/晚' : ''}</span>
        </div>
        <button class="book-btn" onclick="bookItem('${rec.type}','${rec.id}','${userId}','${threadId}')">
            立即预订
        </button>
    `;

    card.addEventListener('click', e => {
        if (e.target.classList.contains('book-btn')) return;
        document.querySelectorAll('.rec-card').forEach(c => c.classList.remove('selected'));
        card.classList.toggle('selected');
    });

    list.appendChild(card);
}

// ── Booking ────────────────────────────────────────────────────────────────

async function bookItem(type, id, userId, tId) {
    setNodeStatus('正在预订...', 'active');
    try {
        const resp = await fetch(`${API}/api/book`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'book', rec_id: id, user_id: userId, thread_id: tId }),
        });
        const result = await resp.json();
        if (result.success) {
            addMsg(`✅ 预订成功！订单号: ${result.order?.order_id || 'N/A'}`, 'assistant', 'success');
            activateStep('booker');
            setNodeStatus('✓ 预订完成', 'done');
            completeAllSteps();
            hideRecPanel();
        } else {
            addMsg('预订失败: ' + (result.detail || '未知错误'), 'assistant', 'error-msg');
            setNodeStatus('✕ 预订失败', 'error');
        }
    } catch (err) {
        addMsg('预订请求失败: ' + err.message, 'assistant', 'error-msg');
        setNodeStatus('✕ 预订失败', 'error');
    }
}

// ── Approval ───────────────────────────────────────────────────────────────

async function handleApproval(action) {
    const userId = document.getElementById('userId').value;
    try {
        const resp = await fetch(`${API}/api/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, user_id: userId, thread_id: threadId }),
        });
        const result = await resp.json();
        addMsg(result.message, 'assistant');
    } catch (err) {
        addMsg('审批请求失败: ' + err.message, 'assistant', 'error-msg');
    }
}

// ── State View ─────────────────────────────────────────────────────────────

async function refreshState() {
    if (!threadId) {
        document.getElementById('stateDisplay').textContent = '// 暂无会话，请先发起一次对话';
        return;
    }
    try {
        const resp = await fetch(`${API}/api/state/${threadId}`);
        const data = await resp.json();
        document.getElementById('stateDisplay').textContent = JSON.stringify(data, null, 2);
    } catch (err) {
        document.getElementById('stateDisplay').textContent = '// 获取状态失败: ' + err.message;
    }
}

function clearState() {
    document.getElementById('stateDisplay').textContent = '// 暂无会话';
}
