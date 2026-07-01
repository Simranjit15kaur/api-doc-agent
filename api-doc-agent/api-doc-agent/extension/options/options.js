/**
 * options.js — Settings page logic
 * Reads/writes API key, language preference, and backend URL to chrome.storage.local
 */

const keyInput = document.getElementById('apiKeyInput');
const toggleKey = document.getElementById('toggleKey');
const langSelect = document.getElementById('languageSelect');
const backendUrl = document.getElementById('backendUrl');
const saveBtn = document.getElementById('saveBtn');
const statusMsg = document.getElementById('statusMsg');

// ── Load saved settings ──────────────────────────────────────
chrome.storage.local.get(['geminiKey', 'language', 'backendUrl'], (data) => {
  if (data.geminiKey) keyInput.value = data.geminiKey;
  if (data.language) langSelect.value = data.language;
  if (data.backendUrl) backendUrl.value = data.backendUrl;
});

// ── Toggle API key visibility ────────────────────────────────
toggleKey.addEventListener('click', () => {
  const isPassword = keyInput.type === 'password';
  keyInput.type = isPassword ? 'text' : 'password';
  toggleKey.textContent = isPassword ? '🙈' : '👁';
});

// ── Save settings ────────────────────────────────────────────
saveBtn.addEventListener('click', () => {
  const key = keyInput.value.trim();
  const lang = langSelect.value;
  const url = backendUrl.value.trim();

  if (!key) {
    showStatus('Please enter your Gemini API key', 'error');
    keyInput.focus();
    return;
  }

  const settings = {
    geminiKey: key,
    language: lang
  };

  // Only save backend URL if user entered one
  if (url) {
    settings.backendUrl = url;
  }

  chrome.storage.local.set(settings, () => {
    if (chrome.runtime.lastError) {
      showStatus('Error saving: ' + chrome.runtime.lastError.message, 'error');
    } else {
      showStatus('✓ Settings saved successfully!', 'success');
    }
  });
});

// ── Allow save with Enter key ────────────────────────────────
keyInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') saveBtn.click();
});

// ── Status message display ───────────────────────────────────
function showStatus(text, type) {
  statusMsg.textContent = text;
  statusMsg.className = 'status-message ' + type;
  if (type === 'success') {
    setTimeout(() => {
      statusMsg.textContent = '';
      statusMsg.className = 'status-message';
    }, 3000);
  }
}
