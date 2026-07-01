/**
 * popup.js — Popup window logic
 * 
 * Checks for API key → sends ANALYZE_PAGE to background.js → closes popup.
 * The side panel will open automatically (via setPanelBehavior in background.js)
 * and display the results.
 */

const analyzeBtn = document.getElementById('analyzeBtn');
const settingsBtn = document.getElementById('settingsBtn');
const statusEl = document.getElementById('status');
const pageInfo = document.getElementById('pageInfo');

// ── Show current tab info ────────────────────────────────────
chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
  if (tab) {
    pageInfo.textContent = tab.title || tab.url;
  }
});

// ── Analyse button click ─────────────────────────────────────
analyzeBtn.addEventListener('click', async () => {
  // 1. Check if API key is set
  const data = await new Promise(resolve =>
    chrome.storage.local.get(['geminiKey'], resolve)
  );

  if (!data.geminiKey) {
    statusEl.textContent = '⚠ Set your API key first';
    statusEl.className = 'error';
    setTimeout(() => chrome.runtime.openOptionsPage(), 1200);
    return;
  }

  // 2. Get the active tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) {
    statusEl.textContent = 'No active tab found';
    statusEl.className = 'error';
    return;
  }

  // 3. Show loading state
  analyzeBtn.classList.add('loading');
  analyzeBtn.disabled = true;
  statusEl.textContent = 'Opening side panel...';
  statusEl.className = 'info';

  // 4. Open the side panel DIRECTLY from popup (preserves user gesture)
  try {
    await chrome.sidePanel.open({ windowId: tab.windowId });
  } catch (err) {
    console.warn('Could not open side panel:', err);
  }

  // 5. Small delay to let the side panel HTML load
  await new Promise(resolve => setTimeout(resolve, 400));

  // 6. Send analyze message to background
  chrome.runtime.sendMessage({
    type: 'ANALYZE_PAGE',
    tabId: tab.id,
    tabUrl: tab.url
  });

  // 7. Close popup (side panel takes over)
  setTimeout(() => window.close(), 300);
});

// ── Settings button ──────────────────────────────────────────
settingsBtn.addEventListener('click', () => {
  chrome.runtime.openOptionsPage();
});
