// script.js
// Sends requests to the CodeMentor AI backend and displays responses.

const submitButton = document.getElementById('submitButton');
const languageLabel = document.getElementById('languageLabel');
const languageSelect = document.getElementById('languageSelect');
const modeSelect = document.getElementById('modeSelect');
const inputText = document.getElementById('inputText');
const outputText = document.getElementById('outputText');

const API_URL = '/mentor';

const REPO_MODE = 'repo_report';

marked.setOptions({
    breaks: true,
    gfm: true,
});

function updateModeUI() {
    const isRepoMode = modeSelect.value === REPO_MODE;
    languageLabel.style.display = isRepoMode ? 'none' : '';
    inputText.placeholder = isRepoMode
        ? 'Enter the absolute path of a repository folder on this machine (e.g. C:\\Users\\you\\my-project)'
        : 'Paste code or type your request here...';
}

modeSelect.addEventListener('change', updateModeUI);
updateModeUI();

function setPlainMessage(message) {
    outputText.className = 'response-content plain-text';
    outputText.textContent = message;
}

function setMarkdownResponse(markdown) {
    outputText.className = 'response-content markdown-body';
    outputText.innerHTML = marked.parse(markdown);
}

async function submitRequest() {
    const payload = {
        mode: modeSelect.value,
        language: languageSelect.value,
        input_text: inputText.value,
    };

    setPlainMessage('Processing...');

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
        });

        let data = {};
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            data = await response.json();
        } else {
            const text = await response.text();
            data = { detail: text || response.statusText };
        }

        if (!response.ok) {
            setPlainMessage(`Error (${response.status}): ${data.detail || 'Unable to get a response.'}`);
            return;
        }

        setMarkdownResponse(data.result || data.response || 'No response returned.');
    } catch (error) {
        setPlainMessage(`Error: ${error.message}`);
    }
}

submitButton.addEventListener('click', submitRequest);
