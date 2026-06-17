/*
 * Mozilla Readability.js — PLACEHOLDER
 *
 * 프로덕션 배포 전 아래 URL에서 최신 버전을 다운로드하여 이 파일을 교체한다:
 *   https://github.com/mozilla/readability/blob/main/Readability.js
 *
 * 아래는 개발/테스트용 최소 구현체다. 실제 Readability가 수행하는
 * 광고·스크립트·내비게이션 제거, 점수 기반 본문 추출 등은 포함하지 않는다.
 */

(function (global) {
  "use strict";

  /**
   * @param {Document} doc - 파싱할 Document (cloneNode 결과물 권장)
   * @param {object} [options]
   */
  function Readability(doc, options) {
    this._doc = doc;
    this._options = options || {};
  }

  Readability.prototype.parse = function () {
    var doc = this._doc;

    // 스크립트·스타일·내비게이션 제거
    ["script", "style", "nav", "header", "footer", "aside", "form"].forEach(function (tag) {
      var els = doc.querySelectorAll(tag);
      for (var i = els.length - 1; i >= 0; i--) {
        els[i].parentNode && els[i].parentNode.removeChild(els[i]);
      }
    });

    // 본문 후보 탐색: article > main > body 순서
    var candidates = ["article", "main", "[role='main']", "body"];
    var contentEl = null;
    for (var c = 0; c < candidates.length; c++) {
      contentEl = doc.querySelector(candidates[c]);
      if (contentEl) break;
    }

    var textContent = contentEl ? (contentEl.innerText || contentEl.textContent || "") : "";
    var title = (doc.querySelector("title") || {}).textContent || "";

    // og:title 우선
    var ogTitle = doc.querySelector("meta[property='og:title']");
    if (ogTitle && ogTitle.getAttribute("content")) {
      title = ogTitle.getAttribute("content");
    }

    if (!textContent.trim()) return null;

    return {
      title: title.trim(),
      textContent: textContent.trim(),
      content: contentEl ? contentEl.innerHTML : "",
      length: textContent.length,
      excerpt: textContent.trim().slice(0, 200),
    };
  };

  global.Readability = Readability;
})(typeof globalThis !== "undefined" ? globalThis : typeof window !== "undefined" ? window : this);
