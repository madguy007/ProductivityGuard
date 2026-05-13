const API_BASE = "http://127.0.0.1:5000";
const HEARTBEAT_SECONDS = 15;
const IDLE_SECONDS = 300;

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create("heartbeat", { periodInMinutes: 0.5 });
});

chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create("heartbeat", { periodInMinutes: 0.5 });
});

chrome.idle.setDetectionInterval(IDLE_SECONDS);

function normalizeDomain(url) {
  try {
    const parsed = new URL(url);
    return parsed.hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return "";
  }
}

function isTrackableUrl(url) {
  return Boolean(url && (url.startsWith("http://") || url.startsWith("https://")));
}

async function getActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0];
}

async function postHeartbeat(payload) {
  const response = await fetch(`${API_BASE}/api/heartbeat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return response.json();
}

function blockedUrl(originalUrl, state) {
  const url = new URL(chrome.runtime.getURL("blocked.html"));
  url.searchParams.set("site", normalizeDomain(originalUrl));
  url.searchParams.set("balance", state.balance_minutes ?? 0);
  return url.toString();
}

async function sendHeartbeat() {
  const tab = await getActiveTab();
  if (!tab || !isTrackableUrl(tab.url)) {
    return;
  }

  const idleState = await chrome.idle.queryState(IDLE_SECONDS);
  const payload = {
    url: tab.url,
    domain: normalizeDomain(tab.url),
    title: tab.title || "",
    idle: idleState !== "active",
    timestamp: new Date().toISOString(),
  };

  try {
    const result = await postHeartbeat(payload);
    if (result.blocked && tab.id && !tab.url.startsWith(chrome.runtime.getURL("blocked.html"))) {
      await chrome.tabs.update(tab.id, { url: blockedUrl(tab.url, result) });
    }
  } catch (error) {
    console.warn("ProductivityGuard local app is not reachable.", error);
  }
}

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "heartbeat") {
    sendHeartbeat();
  }
});

setInterval(sendHeartbeat, HEARTBEAT_SECONDS * 1000);
chrome.tabs.onActivated.addListener(sendHeartbeat);
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.active) {
    sendHeartbeat();
  }
});
chrome.windows.onFocusChanged.addListener((windowId) => {
  if (windowId !== chrome.windows.WINDOW_ID_NONE) {
    sendHeartbeat();
  }
});
