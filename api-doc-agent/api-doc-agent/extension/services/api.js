/**
 * api.js — All fetch() calls to the FastAPI backend
 * Used by background.js (ES module import)
 * 
 * BASE_URL defaults to localhost for development.
 * Update to your Railway URL for production.
 */

const BASE_URL = 'http://localhost:8000';

/**
 * Send page content to the backend for analysis.
 * Returns the full AnalyzeResponse JSON.
 */
export async function analyzeDoc({ pageText, pageUrl, pageTitle, language, geminiKey, errorMessage }) {
  const body = {
    page_text: pageText,
    page_url: pageUrl,
    page_title: pageTitle,
    language: language
  };
  if (errorMessage) {
    body.error_message = errorMessage;
  }

  const response = await fetch(`${BASE_URL}/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Gemini-Key': geminiKey
    },
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    const errorBody = await response.text();
    let message;
    try {
      message = JSON.parse(errorBody).detail || errorBody;
    } catch {
      message = errorBody;
    }
    throw new Error(`API error (${response.status}): ${message}`);
  }

  return response.json();
}

/**
 * Send a follow-up chat message.
 * Returns { reply, session_id }.
 */
export async function sendChat({ sessionId, question, history, geminiKey }) {
  const response = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Gemini-Key': geminiKey
    },
    body: JSON.stringify({
      session_id: sessionId,
      question: question,
      history: history
    })
  });

  if (!response.ok) {
    const errorBody = await response.text();
    let message;
    try {
      message = JSON.parse(errorBody).detail || errorBody;
    } catch {
      message = errorBody;
    }
    throw new Error(`Chat error (${response.status}): ${message}`);
  }

  return response.json();
}
