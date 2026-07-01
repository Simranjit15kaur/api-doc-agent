/**
 * storage.js — Promise wrappers for chrome.storage.local
 * Used by background.js (ES module import)
 */

export const storage = {
  get: (keys) => new Promise(resolve => chrome.storage.local.get(keys, resolve)),
  set: (items) => new Promise(resolve => chrome.storage.local.set(items, resolve)),
  remove: (keys) => new Promise(resolve => chrome.storage.local.remove(keys, resolve))
};

/**
 * Generate a consistent cache key from a URL using djb2 hash.
 * No crypto needed — just needs to be deterministic and fast.
 */
export function urlHash(url) {
  let hash = 5381;
  for (let i = 0; i < url.length; i++) {
    hash = ((hash << 5) + hash) + url.charCodeAt(i);
    hash = hash & hash; // Convert to 32-bit integer
  }
  return 'cache_' + Math.abs(hash).toString(16);
}

/**
 * Generate a chat history key from a URL hash.
 */
export function chatKey(url) {
  return 'chat_' + urlHash(url).replace('cache_', '');
}
