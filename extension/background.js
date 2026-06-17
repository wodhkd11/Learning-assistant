// Service Worker (MV3) — 이벤트 리스닝, 오프라인 큐 관리
"use strict";

const BACKEND_URL = "http://localhost:8000/api/v1/collect";
const TIMEOUT_MS = 2000;
const OFFLINE_QUEUE_KEY = "kalf_offline_queue";
const RETRY_ALARM_NAME = "kalf_retry";

let blacklistDomains = new Set();

// 블랙리스트 로드 (Service Worker 재기동 시마다 실행)
async function loadBlacklist() {
  try {
    const url = chrome.runtime.getURL("blacklist.json");
    const resp = await fetch(url);
    const data = await resp.json();
    blacklistDomains = new Set(data.domains || []);
  } catch {
    // 기본 블랙리스트 폴백
    blacklistDomains = new Set([
      "localhost", "127.0.0.1", "naver.com", "daum.net",
      "google.com", "youtube.com", "instagram.com",
      "twitter.com", "x.com", "facebook.com",
    ]);
  }
}

function extractDomain(url) {
  try {
    const hostname = new URL(url).hostname;
    return hostname.startsWith("www.") ? hostname.slice(4) : hostname;
  } catch {
    return "";
  }
}

function isBlacklisted(url) {
  const domain = extractDomain(url);
  if (!domain) return true;
  for (const blocked of blacklistDomains) {
    if (domain === blocked || domain.endsWith("." + blocked)) return true;
  }
  return false;
}

// 백엔드 POST 전송 (타임아웃 2000ms)
async function sendToBackend(payload) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const resp = await fetch(BACKEND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    clearTimeout(timer);
    return resp.ok;
  } catch {
    clearTimeout(timer);
    return false;
  }
}

// 오프라인 큐에 저장
async function enqueueOffline(payload) {
  const { kalf_offline_queue: queue = [] } =
    await chrome.storage.local.get(OFFLINE_QUEUE_KEY);
  queue.push(payload);
  // 최대 200개 유지
  const trimmed = queue.slice(-200);
  await chrome.storage.local.set({ [OFFLINE_QUEUE_KEY]: trimmed });
}

// 오프라인 큐 재시도
async function retryOfflineQueue() {
  const { kalf_offline_queue: queue = [] } =
    await chrome.storage.local.get(OFFLINE_QUEUE_KEY);
  if (!queue.length) return;

  const remaining = [];
  for (const payload of queue) {
    const ok = await sendToBackend(payload);
    if (!ok) remaining.push(payload);
  }
  await chrome.storage.local.set({ [OFFLINE_QUEUE_KEY]: remaining });
}

// content.js로부터 PAGE_CONTENT 메시지 수신
chrome.runtime.onMessage.addListener((message, _sender, _sendResponse) => {
  if (message.type !== "PAGE_CONTENT") return;

  const payload = message.payload;
  if (!payload?.url || isBlacklisted(payload.url)) return;

  // 비동기 전송 (addListener는 동기 반환이므로 Promise 직접 실행)
  sendToBackend(payload).then((ok) => {
    if (!ok) enqueueOffline(payload);
  });
});

// 주기적 재시도 알람 등록 (5분마다)
chrome.alarms.create(RETRY_ALARM_NAME, { periodInMinutes: 5 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === RETRY_ALARM_NAME) retryOfflineQueue();
});

// Service Worker 초기화
loadBlacklist();
