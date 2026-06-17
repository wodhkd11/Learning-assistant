(function () {
  "use strict";
  try {
    const docClone = document.cloneNode(true);
    const article = new Readability(docClone).parse();

    if (!article || !article.textContent) return;

    const content = article.textContent.trim();
    if (content.length < 200) return;

    chrome.runtime.sendMessage({
      type: "PAGE_CONTENT",
      payload: {
        url: window.location.href,
        title: article.title || document.title,
        content: content,
        timestamp: new Date().toISOString(),
        document_title: document.title,
      },
    });
  } catch (err) {
    console.warn("[KALF] content.js 오류:", err);
  }
})();
