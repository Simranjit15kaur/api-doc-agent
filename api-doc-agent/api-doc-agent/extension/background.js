/**
 * background.js — The always-running orchestrator (Service Worker)
 * 
 * This is an ES module (declared in manifest.json as "type": "module").
 * It handles:
 * 1. Opening the side panel on action click
 * 2. Injecting the content script and extracting page data
 * 3. Calling the FastAPI backend for analysis
 * 4. Forwarding results to the side panel
 * 5. Handling chat messages
 * 6. Error tracing
 * 
 * IMPORTANT: Chrome can terminate this service worker at any time.
 * Never store state in global variables — always use chrome.storage.local.
 */

import { analyzeDoc, sendChat } from './services/api.js';
import { storage, urlHash } from './services/storage.js';

// ── Open side panel when the extension icon is clicked ───────
chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch(console.error);

// ── Message Router ───────────────────────────────────────────
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case 'ANALYZE_PAGE':
      handleAnalysis(message.tabId, message.tabUrl, message.forceRefresh);
      break;

    case 'SEND_CHAT':
      handleChat(message.payload);
      break;

    case 'TRACE_ERROR':
      handleErrorTrace(message.payload);
      break;
  }
});

// ── Analysis Handler ─────────────────────────────────────────
async function handleAnalysis(tabId, tabUrl, forceRefresh = false) {
  try {
    // 1. Notify side panel: loading
    broadcastToSidePanel({ type: 'ANALYSIS_LOADING' });

    // 2. Get user settings
    const settings = await storage.get(['geminiKey', 'language', 'backendUrl']);

    if (!settings.geminiKey) {
      broadcastToSidePanel({
        type: 'ANALYSIS_ERROR',
        error: 'No API key set. Please configure your Gemini API key in Settings.'
      });
      return;
    }

    const language = settings.language || 'python';

    // 3. Inject content script and extract page data
    let pageData;
    try {
      await chrome.scripting.executeScript({
        target: { tabId: tabId },
        files: ['content/extractor.js']
      });

      // Small delay to ensure content script is ready
      await new Promise(resolve => setTimeout(resolve, 100));

      const response = await chrome.tabs.sendMessage(tabId, { type: 'EXTRACT' });

      if (!response || response.type === 'EXTRACT_ERROR') {
        broadcastToSidePanel({
          type: 'ANALYSIS_ERROR',
          error: response?.error || 'Could not read this page. Try scrolling it to load all content first.'
        });
        return;
      }

      pageData = response.data;
    } catch (err) {
      broadcastToSidePanel({
        type: 'ANALYSIS_ERROR',
        error: 'Could not read this page. Make sure you\'re on a web page (not chrome:// or extension pages).'
      });
      return;
    }

    if (!pageData.text || pageData.text.trim().length < 50) {
      broadcastToSidePanel({
        type: 'ANALYSIS_ERROR',
        error: 'Could not read this page. Try scrolling it to load all content first.'
      });
      return;
    }

    // 4. Call FastAPI backend
    try {
      const result = await analyzeDoc({
        pageText: pageData.text,
        pageUrl: pageData.url,
        pageTitle: pageData.title,
        language: language,
        geminiKey: settings.geminiKey
      });

      // 5. Forward results to side panel
      broadcastToSidePanel({
        type: 'ANALYSIS_RESULT',
        data: result
      });

    } catch (apiErr) {
      const errorMsg = apiErr.message || 'Unknown error';

      if (errorMsg.includes('401')) {
        broadcastToSidePanel({
          type: 'ANALYSIS_ERROR',
          error: 'Invalid Gemini API key. Please check your key in Settings.'
        });
      } else if (errorMsg.includes('429')) {
        broadcastToSidePanel({
          type: 'ANALYSIS_ERROR',
          error: 'Gemini API rate limit exceeded. Please wait a moment and try again.'
        });
      } else if (errorMsg.includes('Failed to fetch') || errorMsg.includes('NetworkError')) {
        broadcastToSidePanel({
          type: 'ANALYSIS_ERROR',
          error: 'Could not reach the server. Is the backend running?'
        });
      } else {
        broadcastToSidePanel({
          type: 'ANALYSIS_ERROR',
          error: errorMsg
        });
      }
    }

  } catch (err) {
    console.error('[background.js] Analysis error:', err);
    broadcastToSidePanel({
      type: 'ANALYSIS_ERROR',
      error: 'Unexpected error: ' + err.message
    });
  }
}

// ── Chat Handler ─────────────────────────────────────────────
async function handleChat(payload) {
  try {
    const settings = await storage.get(['geminiKey']);

    if (!settings.geminiKey) {
      broadcastToSidePanel({
        type: 'CHAT_ERROR',
        error: 'No API key set.'
      });
      return;
    }

    const result = await sendChat({
      sessionId: payload.sessionId,
      question: payload.question,
      history: payload.history,
      geminiKey: settings.geminiKey
    });

    broadcastToSidePanel({
      type: 'CHAT_REPLY',
      data: result
    });

  } catch (err) {
    console.error('[background.js] Chat error:', err);
    broadcastToSidePanel({
      type: 'CHAT_ERROR',
      error: err.message || 'Failed to send chat message.'
    });
  }
}

// ── Error Trace Handler ──────────────────────────────────────
async function handleErrorTrace(payload) {
  try {
    const settings = await storage.get(['geminiKey', 'language']);

    if (!settings.geminiKey) {
      broadcastToSidePanel({
        type: 'ERROR_TRACE_ERROR',
        error: 'No API key set.'
      });
      return;
    }

    // Get the active tab to re-extract page content
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
      broadcastToSidePanel({
        type: 'ERROR_TRACE_ERROR',
        error: 'No active tab found.'
      });
      return;
    }

    // Inject and extract page content again
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ['content/extractor.js']
    });
    await new Promise(resolve => setTimeout(resolve, 100));
    const response = await chrome.tabs.sendMessage(tab.id, { type: 'EXTRACT' });

    if (!response || !response.data) {
      broadcastToSidePanel({
        type: 'ERROR_TRACE_ERROR',
        error: 'Could not read the page for error tracing.'
      });
      return;
    }

    // Call analyze with error_message included
    const result = await analyzeDoc({
      pageText: response.data.text,
      pageUrl: response.data.url,
      pageTitle: response.data.title,
      language: settings.language || 'python',
      geminiKey: settings.geminiKey,
      errorMessage: payload.errorMessage
    });

    broadcastToSidePanel({
      type: 'ERROR_TRACE_RESULT',
      data: result
    });

  } catch (err) {
    console.error('[background.js] Error trace error:', err);
    broadcastToSidePanel({
      type: 'ERROR_TRACE_ERROR',
      error: err.message || 'Failed to trace error.'
    });
  }
}

// ── Broadcast helper ─────────────────────────────────────────
function broadcastToSidePanel(message) {
  chrome.runtime.sendMessage(message).catch(() => {
    // Side panel might not be open — safe to ignore
  });
}
