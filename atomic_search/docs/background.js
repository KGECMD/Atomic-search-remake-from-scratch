// Atomic Search Browser Extension - Background Script

const DEFAULT_ENGINE = "https://your-atomic-search-instance.com";

// Handle extension icon click
chrome.action.onClicked.addListener(async (tab) => {
  // Open search in current tab
  await chrome.tabs.update(tab.id, {
    url: DEFAULT_ENGINE + "/search"
  });
});

// Handle search requests from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "search") {
    fetch(`${DEFAULT_ENGINE}/api/v1/search?q=${encodeURIComponent(request.query)}`)
      .then(res => res.json())
      .then(data => sendResponse(data))
      .catch(err => sendResponse({ error: err.message }));
    return true; // Keep channel open for async response
  }
  
  if (request.action === "openSearch") {
    chrome.tabs.create({
      url: `${DEFAULT_ENGINE}/search?q=${encodeURIComponent(request.query)}`
    });
  }
});

// Set default search engine
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({
    engineUrl: DEFAULT_ENGINE,
    theme: "dark"
  });
});

// Context menu for right-click search
chrome.contextMenus?.create({
  id: "atomic-search",
  title: "Search with Atomic Search",
  contexts: ["selection"]
});

chrome.contextMenus?.onClicked.addListener((info) => {
  if (info.menuItemId === "atomic-search" && info.selectionText) {
    chrome.tabs.create({
      url: `${DEFAULT_ENGINE}/search?q=${encodeURIComponent(info.selectionText)}`
    });
  }
});
