# 모듈 A — 데이터 수집기 (Browser Extension)

**담당 코더:** 코더 A
**브랜치:** `feat/module-A-B`
**담당 파일:** `extension/`

---

## 목표

사용자 브라우징 흐름을 방해하지 않고 정제된 웹 페이지 데이터를 추출하여 백엔드로 전송한다.

---

## 세부 요구사항

- Chrome Manifest V3 규격 준수 (`manifest_version: 3`)
- `chrome.webNavigation.onCompleted` 이벤트 리스닝으로 페이지 로드 완료 시점 포착
- Content Script에서 Mozilla Readability.js를 활용해 광고·스크립트·내비게이션 제외 순수 본문 추출
- 클라이언트 단 블랙리스트 필터링: 포털 메인, localhost, 특정 금융 사이트 등 수집 불필요 도메인 제외
- 백엔드 미응답 시 `chrome.storage.local`에 임시 저장 후 재시도하는 오프라인 큐 내장

---

## 인터페이스 정의

| 항목 | 명세 |
|------|------|
| 엔드포인트 | `POST http://localhost:8000/api/v1/collect` |
| Content-Type | `application/json` |
| 요청 페이로드 | `{"url": string, "title": string, "content": string, "timestamp": ISO8601}` |
| 성공 응답 | `{"status": "queued", "id": uuid}` |
| 타임아웃 | 2000ms — 초과 시 `chrome.storage.local`에 저장 |

---

## 블랙리스트 예시 (초기값)

```javascript
const BLACKLIST_DOMAINS = [
  "localhost",
  "127.0.0.1",
  "naver.com",       // 포털 메인
  "daum.net",
  "google.com",
  "youtube.com",
  "instagram.com",
  "twitter.com",
  "x.com",
  "facebook.com",
];
```

환경에 따라 `extension/blacklist.json`으로 분리하여 관리.

---

## 파일 구조

```
extension/
├── manifest.json
├── background.js      # Service Worker — 이벤트 리스닝, 큐 관리
├── content.js         # Content Script — Readability 본문 추출
├── readability.js     # Mozilla Readability.js (번들)
└── blacklist.json     # 블랙리스트 도메인 목록
```

---

## 주의사항

- Manifest V3에서는 `background.js`가 Service Worker로 동작한다. 지속적인 상태 유지가 불가능하므로 `chrome.storage.local`을 적극 활용한다.
- `chrome.webNavigation` 권한이 `manifest.json`의 `permissions`에 선언되어야 한다.
- Content Script는 `document_idle` 시점에 실행한다.
- Readability.js는 외부 CDN이 아닌 번들로 포함한다 (CSP 제약).
