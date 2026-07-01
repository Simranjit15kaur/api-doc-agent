/**
 * extractor.js — Content script injected programmatically into the active page.
 * 
 * This is a CLASSIC script (not an ES module). It runs in the page's DOM context.
 * Its only job: extract page content and send it back via sendResponse.
 * 
 * The 15,000 character cap prevents token blowout on massive API reference pages
 * (e.g., full OpenAI API reference can be 200k+ chars).
 */

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'EXTRACT') {
    try {
      const pageData = {
        text: document.body.innerText.slice(0, 15000),
        url: window.location.href,
        title: document.title
      };
      sendResponse({ type: 'PAGE_DATA', data: pageData });
    } catch (err) {
      sendResponse({ type: 'EXTRACT_ERROR', error: err.message });
    }
  }
  return true; // Keep message channel open for async response
});
