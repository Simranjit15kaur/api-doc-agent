/**
 * sidepanel.js — Side panel logic
 * 
 * Handles three states: Empty, Loading, Results + Chat.
 * Listens for messages from background.js, renders analysis results,
 * manages chat, caches results, and handles tab switching.
 */

// ── DOM Elements ─────────────────────────────────────────────
const emptyState = document.getElementById('emptyState');
const loadingState = document.getElementById('loadingState');
const resultsState = document.getElementById('resultsState');
const chatSection = document.getElementById('chatSection');
const errorBanner = document.getElementById('errorBanner');
const cachedBadge = document.getElementById('cachedBadge');

// Results elements
const docTypeBadge = document.getElementById('docTypeBadge');
const methodBadge = document.getElementById('methodBadge');
const endpointUrl = document.getElementById('endpointUrl');
const authInfo = document.getElementById('authInfo');
const codeContent = document.getElementById('codeContent');
const postmanContent = document.getElementById('postmanContent');
const explanationText = document.getElementById('explanationText');
const errorAnalysisCard = document.getElementById('errorAnalysisCard');
const errorAnalysisText = document.getElementById('errorAnalysisText');

// Error trace elements
const errorTextarea = document.getElementById('errorTextarea');
const traceErrorBtn = document.getElementById('traceErrorBtn');
const reanalyzeBtn = document.getElementById('reanalyzeBtn');

// Chat elements
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const chatSendBtn = document.getElementById('chatSendBtn');

// Copy buttons
const copyCodeBtn = document.getElementById('copyCodeBtn');
const copyPostmanBtn = document.getElementById('copyPostmanBtn');

// ── State ────────────────────────────────────────────────────
let currentSessionId = null;
let currentTabUrl = null;
let chatHistory = [];

// ── Helper: djb2 hash (must match storage.js) ───────────────
function urlHash(url) {
  let hash = 5381;
  for (let i = 0; i < url.length; i++) {
    hash = ((hash << 5) + hash) + url.charCodeAt(i);
    hash = hash & hash;
  }
  return 'cache_' + Math.abs(hash).toString(16);
}

function chatKey(url) {
  return 'chat_' + Math.abs((() => {
    let hash = 5381;
    for (let i = 0; i < url.length; i++) {
      hash = ((hash << 5) + hash) + url.charCodeAt(i);
      hash = hash & hash;
    }
    return hash;
  })()).toString(16);
}

// ── State Management ─────────────────────────────────────────
function showEmpty() {
  emptyState.style.display = 'flex';
  loadingState.classList.remove('active');
  resultsState.classList.remove('active');
  chatSection.classList.remove('active');
  errorBanner.classList.remove('show');
  cachedBadge.classList.remove('show');
}

function showLoading() {
  emptyState.style.display = 'none';
  loadingState.classList.add('active');
  resultsState.classList.remove('active');
  chatSection.classList.remove('active');
  errorBanner.classList.remove('show');
  cachedBadge.classList.remove('show');
}

function showResults(data) {
  emptyState.style.display = 'none';
  loadingState.classList.remove('active');
  resultsState.classList.add('active');
  chatSection.classList.add('active');
  errorBanner.classList.remove('show');

  // Cache badge
  if (data.from_cache) {
    cachedBadge.classList.add('show');
  } else {
    cachedBadge.classList.remove('show');
  }

  // Session ID
  currentSessionId = data.session_id;

  // Doc type
  docTypeBadge.textContent = data.doc_type || 'Unknown';

  // Endpoint
  const method = data.endpoint?.method || 'GET';
  methodBadge.textContent = method;
  methodBadge.className = 'method-badge ' + method.toLowerCase();
  endpointUrl.textContent = data.endpoint?.url || 'N/A';

  // Auth
  if (data.endpoint?.auth) {
    authInfo.innerHTML = '🔒 Auth: <span>' + escapeHtml(data.endpoint.auth) + '</span>';
    authInfo.style.display = 'block';
  } else {
    authInfo.style.display = 'none';
  }

  // Code snippet
  if (data.code_snippet) {
    codeContent.textContent = data.code_snippet;
    // Apply syntax highlighting
    if (typeof hljs !== 'undefined') {
      hljs.highlightElement(codeContent);
    }
    document.getElementById('codeCard').style.display = 'block';
  } else {
    document.getElementById('codeCard').style.display = 'none';
  }

  // Postman payload
  if (data.postman_payload) {
    const formatted = typeof data.postman_payload === 'string'
      ? data.postman_payload
      : JSON.stringify(data.postman_payload, null, 2);
    postmanContent.textContent = formatted;
    document.getElementById('postmanCard').style.display = 'block';
  } else {
    document.getElementById('postmanCard').style.display = 'none';
  }

  // Plain English
  explanationText.textContent = data.plain_english || 'No explanation available.';

  // Error analysis
  if (data.error_analysis) {
    errorAnalysisText.textContent = data.error_analysis;
    errorAnalysisCard.style.display = 'block';
  } else {
    errorAnalysisCard.style.display = 'none';
  }
}

function showError(message) {
  emptyState.style.display = 'none';
  loadingState.classList.remove('active');
  errorBanner.textContent = '⚠ ' + message;
  errorBanner.classList.add('show');
}

// ── HTML escape helper ───────────────────────────────────────
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ── Message Listener (from background.js) ────────────────────
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case 'ANALYSIS_LOADING':
      showLoading();
      break;

    case 'ANALYSIS_RESULT':
      showResults(message.data);
      // Cache the result locally
      if (currentTabUrl) {
        const key = urlHash(currentTabUrl);
        const cacheData = {};
        cacheData[key] = message.data;
        chrome.storage.local.set(cacheData);
      }
      break;

    case 'ANALYSIS_ERROR':
      showError(message.error);
      break;

    case 'CHAT_REPLY':
      appendChatMessage('agent', message.data.reply);
      chatSendBtn.disabled = false;
      chatInput.disabled = false;
      chatInput.focus();
      break;

    case 'CHAT_ERROR':
      appendChatMessage('agent', '⚠ Error: ' + message.error);
      chatSendBtn.disabled = false;
      chatInput.disabled = false;
      break;

    case 'ERROR_TRACE_RESULT':
      if (message.data.error_analysis) {
        errorAnalysisText.textContent = message.data.error_analysis;
        errorAnalysisCard.style.display = 'block';
        errorAnalysisCard.scrollIntoView({ behavior: 'smooth' });
      }
      traceErrorBtn.disabled = false;
      traceErrorBtn.textContent = 'Trace Error';
      break;

    case 'ERROR_TRACE_ERROR':
      traceErrorBtn.disabled = false;
      traceErrorBtn.textContent = 'Trace Error';
      showError(message.error);
      break;
  }
  return true;
});

// ── Copy Buttons ─────────────────────────────────────────────
function setupCopyButton(btn) {
  btn.addEventListener('click', () => {
    const targetId = btn.dataset.target;
    const targetEl = document.getElementById(targetId);
    if (!targetEl) return;

    navigator.clipboard.writeText(targetEl.textContent).then(() => {
      btn.textContent = '✓ Copied!';
      btn.classList.add('copied');
      setTimeout(() => {
        btn.textContent = 'Copy';
        btn.classList.remove('copied');
      }, 2000);
    }).catch(() => {
      btn.textContent = 'Failed';
      setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
    });
  });
}

setupCopyButton(copyCodeBtn);
setupCopyButton(copyPostmanBtn);

// ── Error Trace ──────────────────────────────────────────────
traceErrorBtn.addEventListener('click', () => {
  const errorMsg = errorTextarea.value.trim();
  if (!errorMsg) return;

  traceErrorBtn.disabled = true;
  traceErrorBtn.textContent = 'Tracing...';

  chrome.runtime.sendMessage({
    type: 'TRACE_ERROR',
    payload: {
      sessionId: currentSessionId,
      errorMessage: errorMsg,
      tabUrl: currentTabUrl
    }
  });
});

// ── Re-analyse ───────────────────────────────────────────────
reanalyzeBtn.addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) {
    // Clear cache for this URL
    const key = urlHash(tab.url);
    chrome.storage.local.remove(key);

    chrome.runtime.sendMessage({
      type: 'ANALYZE_PAGE',
      tabId: tab.id,
      tabUrl: tab.url,
      forceRefresh: true
    });
  }
});

// ── Chat ─────────────────────────────────────────────────────
function appendChatMessage(role, content) {
  const msgEl = document.createElement('div');
  msgEl.className = 'chat-msg ' + role;
  msgEl.textContent = content;
  chatMessages.appendChild(msgEl);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  // Update chat history
  chatHistory.push({ role, content });

  // Keep only last 20 messages in local state
  if (chatHistory.length > 20) {
    chatHistory = chatHistory.slice(-20);
  }

  // Persist chat history
  if (currentTabUrl) {
    const ck = chatKey(currentTabUrl);
    const chatData = {};
    chatData[ck] = chatHistory;
    chrome.storage.local.set(chatData);
  }
}

function sendChatMessage() {
  const question = chatInput.value.trim();
  if (!question || !currentSessionId) return;

  appendChatMessage('user', question);
  chatInput.value = '';
  chatSendBtn.disabled = true;
  chatInput.disabled = true;

  // Send last 6 messages for context
  const recentHistory = chatHistory.slice(-6);

  chrome.runtime.sendMessage({
    type: 'SEND_CHAT',
    payload: {
      sessionId: currentSessionId,
      question: question,
      history: recentHistory
    }
  });
}

chatSendBtn.addEventListener('click', sendChatMessage);
chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendChatMessage();
  }
});

// ── Load cached state for the current tab ────────────────────
async function loadCachedState() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.url) {
    showEmpty();
    return;
  }

  currentTabUrl = tab.url;
  const cacheKeyVal = urlHash(tab.url);
  const ck = chatKey(tab.url);

  chrome.storage.local.get([cacheKeyVal, ck], (data) => {
    // Restore analysis results
    if (data[cacheKeyVal]) {
      showResults(data[cacheKeyVal]);
    } else {
      // Trigger analysis automatically if API key is set
      chrome.storage.local.get(['geminiKey'], (settings) => {
        if (!settings.geminiKey) {
          showEmpty();
          showError('Please configure your Gemini API Key in the extension options.');
        } else {
          chrome.runtime.sendMessage({
            type: 'ANALYZE_PAGE',
            tabId: tab.id,
            tabUrl: tab.url
          });
        }
      });
    }

    // Restore chat history
    if (data[ck]) {
      chatHistory = data[ck];
      chatMessages.innerHTML = '';
      chatHistory.forEach(msg => {
        const msgEl = document.createElement('div');
        msgEl.className = 'chat-msg ' + msg.role;
        msgEl.textContent = msg.content;
        chatMessages.appendChild(msgEl);
      });
      chatMessages.scrollTop = chatMessages.scrollHeight;
    } else {
      chatHistory = [];
      chatMessages.innerHTML = '';
    }
  });
}

// ── Tab switch detection ─────────────────────────────────────
chrome.tabs.onActivated.addListener(() => {
  loadCachedState();
});

// Also handle URL changes within the same tab
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.url) {
    chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
      if (tab && tab.id === tabId) {
        loadCachedState();
      }
    });
  }
});

// ── Initial load ─────────────────────────────────────────────
loadCachedState();
