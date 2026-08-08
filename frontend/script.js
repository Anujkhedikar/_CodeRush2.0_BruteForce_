// script.js
// CodeMentor AI web app: chat-style UI with session history.
// Shows each query together with its token usage, context size, model,
// duration, and timestamp, so the user can inspect memory usage per turn.

const submitButton = document.getElementById('submitButton');
const newSessionBtn = document.getElementById('newSessionBtn');
const languageLabel = document.getElementById('languageLabel');
const languageSelect = document.getElementById('languageSelect');
const modeSelect = document.getElementById('modeSelect');
const inputText = document.getElementById('inputText');
const chat = document.getElementById('chat');
const emptyState = document.getElementById('emptyState');
const sessionList = document.getElementById('sessionList');

const API_URL = '/mentor';
const REPO_MODE = 'repo_report';
const MENTOR_URLS = {
    mentor: '/mentor',
    sessions: '/sessions',
    stats: '/stats',
};

let currentSessionId = '';
let busy = false;

marked.setOptions({
    breaks: true,
    gfm: true,
});

// ---------- rendering helpers ----------

function formatNumber(value) {
    if (value === null || value === undefined) return '?';
    return Number(value).toLocaleString('en-US');
}

function formatTime(timestamp) {
    if (!timestamp) return '';
    return new Date(timestamp * 1000).toLocaleString();
}

function formatCost(cost) {
    if (cost === null || cost === undefined) return '?';
    return cost >= 0.01 ? `$${Number(cost).toFixed(3)}` : `$${Number(cost).toFixed(4)}`;
}

function appendInputCheck(wrapper, issues) {
    if (!wrapper || !issues || !issues.length) return;
    const meta = wrapper.querySelector('.msg-meta');
    if (!meta) return;
    const note = ` \u00B7 \u26A0 syntax: ${issues.length} issue(s) found in input`;
    meta.textContent += meta.textContent ? note : note.trim();
}

function addUserMessage(content, mode, language, timestamp, inputCheck) {
    const wrapper = document.createElement('div');
    wrapper.className = 'msg msg-user';

    const chip = document.createElement('div');
    chip.className = 'msg-chip';
    const label = mode ? mode.replace('_', ' ').toUpperCase() : '';
    const lang = language && mode !== REPO_MODE ? language : '';
    chip.textContent = [label, lang].filter(Boolean).join(' \u00B7 ');

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble user-bubble';
    bubble.textContent = content;

    const meta = document.createElement('div');
    meta.className = 'msg-meta';
    meta.textContent = formatTime(timestamp);

    wrapper.appendChild(chip);
    wrapper.appendChild(bubble);
    wrapper.appendChild(meta);
    appendInputCheck(wrapper, inputCheck);
    chat.appendChild(wrapper);
    return wrapper;
}

function addAssistantMessage(content, stats, timestamp) {
    const wrapper = document.createElement('div');
    wrapper.className = 'msg msg-assistant';

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble assistant-bubble markdown-body';
    bubble.innerHTML = marked.parse(content);

    const meta = document.createElement('div');
    meta.className = 'msg-meta';
    if (stats) {
        const usage = stats.usage || {};
        const contextTurns = stats.context_turns !== undefined
            ? `${formatNumber(stats.context_turns)} turn(s) context`
            : '';
        const trimmed = stats.context && stats.context.trimmed_turns
            ? `${stats.context.trimmed_turns} trimmed from context`
            : '';
        const memory = stats.context && stats.context.memory_turns
            ? `memory: ${formatNumber(stats.context.memory_turns)} turn(s) summarized`
            : '';
        const tokens = usage.total_tokens !== undefined
            ? `tokens: ${formatNumber(usage.prompt_tokens)} in / ${formatNumber(usage.completion_tokens)} out (${formatNumber(usage.total_tokens)} total)`
            : 'tokens: n/a';
        const model = stats.model ? `\u00B7 ${stats.model}` : '';
        const cost = stats.cost !== undefined
            ? `\u00B7 est. ${formatCost(stats.cost)}`
            : '';
        const duration = stats.duration_ms
            ? `\u00B7 ${(stats.duration_ms / 1000).toFixed(1)}s`
            : '';
        meta.textContent = [contextTurns, trimmed, memory, tokens, model, cost, duration]
            .filter(Boolean)
            .join(' \u00B7 ');
    }
    if (stats && stats.verification && stats.verification.blocks) {
        const issues = stats.verification.blocks.reduce(
            (sum, block) => sum + (block.issues ? block.issues.length : 0), 0);
        const verdict = stats.verification.status === 'ok'
            ? `\u2713 verified (${stats.verification.blocks.length} block(s))`
            : `\u26A0 verify: ${issues} issue(s) in ${stats.verification.blocks.length} block(s)`;
        meta.textContent += meta.textContent ? ` \u00B7 ${verdict}` : verdict;
    }
    if (timestamp) {
        meta.textContent += meta.textContent ? ` \u00B7 ${formatTime(timestamp)}` : formatTime(timestamp);
    }

    wrapper.appendChild(bubble);
    wrapper.appendChild(meta);
    chat.appendChild(wrapper);
}

function addErrorMessage(detail) {
    const wrapper = document.createElement('div');
    wrapper.className = 'msg msg-error';
    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble error-bubble';
    bubble.textContent = detail;
    wrapper.appendChild(bubble);
    chat.appendChild(wrapper);
}

function scrollToBottom() {
    chat.scrollTop = chat.scrollHeight;
}

function renderTurns(turns) {
    chat.innerHTML = '';
    emptyState.style.display = 'none';
    for (const turn of turns) {
        if (turn.role === 'user') {
            addUserMessage(turn.content, turn.mode, turn.language, turn.timestamp, turn.input_check);
        } else if (turn.role === 'assistant') {
            addAssistantMessage(turn.content, turn, turn.timestamp);
        }
    }
    scrollToBottom();
}

function setLoading() {
    emptyState.style.display = 'none';
    const wrapper = document.createElement('div');
    wrapper.className = 'msg msg-assistant';
    wrapper.id = 'loadingMsg';
    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble assistant-bubble';
    bubble.textContent = 'Processing...';
    wrapper.appendChild(bubble);
    chat.appendChild(wrapper);
    scrollToBottom();
}

function removeLoading() {
    const loading = document.getElementById('loadingMsg');
    if (loading) loading.remove();
}

// ---------- session history sidebar ----------

async function loadSessions() {
    try {
        const response = await fetch(MENTOR_URLS.sessions);
        const data = await response.json();
        sessionList.innerHTML = '';
        for (const session of data.sessions || []) {
            const item = document.createElement('div');
            item.className = 'session-item' + (session.id === currentSessionId ? ' active' : '');
            item.dataset.id = session.id;

            const preview = document.createElement('div');
            preview.className = 'session-preview';
            preview.textContent = session.preview || '(empty session)';

            const detail = document.createElement('div');
            detail.className = 'session-detail';
            detail.textContent = `${formatTime(session.updated_at)} \u00B7 ${session.turn_count} turn(s) \u00B7 ${formatNumber(session.total_tokens)} tokens`;

            const remove = document.createElement('button');
            remove.className = 'session-remove';
            remove.type = 'button';
            remove.title = 'Delete session';
            remove.textContent = '\u00D7';
            remove.addEventListener('click', async (event) => {
                event.stopPropagation();
                await deleteSession(session.id);
            });

            item.appendChild(preview);
            item.appendChild(detail);
            item.appendChild(remove);
            item.addEventListener('click', () => openSession(session.id));
            sessionList.appendChild(item);
        }
    } catch (error) {
        // history list is optional; keep the chat working
    }
}

async function openSession(sessionId) {
    try {
        const response = await fetch(`${MENTOR_URLS.sessions}/${sessionId}`);
        if (!response.ok) return;
        const session = await response.json();
        currentSessionId = session.id;
        renderTurns(session.turns || []);
        inputText.value = '';
        loadSessions();
    } catch (error) {
        addErrorMessage(`Could not load session: ${error.message}`);
    }
}

async function deleteSession(sessionId) {
    if (!confirm(`Delete session ${sessionId}?`)) return;
    try {
        await fetch(`${MENTOR_URLS.sessions}/${sessionId}`, { method: 'DELETE' });
        if (currentSessionId === sessionId) {
            currentSessionId = '';
            chat.innerHTML = '';
            emptyState.style.display = '';
        }
        loadSessions();
        loadStats();
    } catch (error) {
        addErrorMessage(`Could not delete session: ${error.message}`);
    }
}

function newSession() {
    currentSessionId = '';
    chat.innerHTML = '';
    emptyState.style.display = '';
    inputText.value = '';
    loadSessions();
}

// ---------- usage analytics ----------

function renderUsageBars(container, rows, barFor) {
    container.innerHTML = '';
    const max = Math.max(...rows.map((row) => barFor(row)), 1);
    for (const row of rows) {
        const line = document.createElement('div');
        line.className = 'usage-row';

        const name = document.createElement('div');
        name.className = 'usage-name';
        name.textContent = row.name;

        const track = document.createElement('div');
        track.className = 'usage-track';
        const fill = document.createElement('div');
        fill.className = 'usage-fill';
        fill.style.width = `${Math.max(2, (barFor(row) / max) * 100)}%`;
        track.appendChild(fill);

        const value = document.createElement('div');
        value.className = 'usage-value';
        value.textContent = formatNumber(barFor(row));

        line.appendChild(name);
        line.appendChild(track);
        line.appendChild(value);
        container.appendChild(line);
    }
}

async function loadStats() {
    try {
        const response = await fetch(MENTOR_URLS.stats);
        const data = await response.json();
        const totals = data.totals || {};
        const empty = document.getElementById('usageEmpty');
        const totalsBox = document.getElementById('usageTotals');
        if (!totals.sessions) {
            empty.style.display = '';
            totalsBox.hidden = true;
            return;
        }
        empty.style.display = 'none';
        totalsBox.hidden = false;
        totalsBox.textContent =
            `${formatNumber(totals.sessions)} session(s) \u00B7 ${formatNumber(totals.turns)} turn(s) ` +
            `\u00B7 ${formatNumber(totals.total_tokens)} tokens \u00B7 est. ${formatCost(totals.cost)}`;
        renderUsageBars(document.getElementById('usageModes'), data.by_mode || [], (row) => row.tokens);

        const days = document.getElementById('usageDays');
        days.innerHTML = '';
        const maxDay = Math.max(...(data.by_day || []).map((day) => day.tokens), 1);
        for (const day of data.by_day || []) {
            const cell = document.createElement('div');
            cell.className = 'usage-day';
            cell.title = `${day.day} \u00B7 ${formatNumber(day.tokens)} tokens`;
            const bar = document.createElement('div');
            bar.className = 'day-bar';
            bar.style.height = day.tokens ? `${Math.max(6, (day.tokens / maxDay) * 100)}%` : '2px';
            cell.appendChild(bar);
            days.appendChild(cell);
        }
    } catch (error) {
        // analytics panel is optional; keep the chat working
    }
}

// ---------- mode switching ----------

function updateModeUI() {
    const isRepoMode = modeSelect.value === REPO_MODE;
    languageLabel.style.display = isRepoMode ? 'none' : '';
    inputText.placeholder = isRepoMode
        ? 'Enter the absolute path of a repository folder on this machine (e.g. C:\\Users\\you\\my-project)'
        : 'Paste code or type your request here...';
}

// ---------- submit ----------

async function submitRequest() {
    if (busy) return;
    const content = inputText.value.trim();
    if (!content) return;

    const payload = {
        mode: modeSelect.value,
        language: languageSelect.value,
        input_text: content,
        session_id: currentSessionId,
    };

    busy = true;
    submitButton.disabled = true;
    inputText.value = '';
    emptyState.style.display = 'none';
    const userMsgEl = addUserMessage(content, payload.mode, payload.language);
    setLoading();

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        let data = {};
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            data = await response.json();
        } else {
            data = { detail: await response.text() || response.statusText };
        }

        removeLoading();

        if (!response.ok) {
            addErrorMessage(`Error (${response.status}): ${data.detail || 'Unable to get a response.'}`);
            return;
        }

        currentSessionId = data.session_id || currentSessionId;
        addAssistantMessage(data.result || 'No response returned.', data);
        appendInputCheck(userMsgEl, data.input_check);
        loadSessions();
        loadStats();
    } catch (error) {
        removeLoading();
        addErrorMessage(`Error: ${error.message}`);
    } finally {
        busy = false;
        submitButton.disabled = false;
        scrollToBottom();
    }
}

// ---------- wire up ----------

modeSelect.addEventListener('change', updateModeUI);
updateModeUI();

submitButton.addEventListener('click', submitRequest);
inputText.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        submitRequest();
    }
});
newSessionBtn.addEventListener('click', newSession);

loadSessions();
loadStats();
