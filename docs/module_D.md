# 모듈 D — 지식 에이전트 오케스트레이터 (Advanced LLM Worker)

**담당 코더:** 코더 C
**브랜치:** `feat/module-C-D-llm`
**담당 파일:** `backend/workers/analyzer.py`, `backend/llm/factory.py`, `backend/llm/claude_client.py`, `backend/llm/gemini_client.py`

---

## 목표

상용 LLM API를 제어하여 문서 요약, 태깅, 연관 관계를 담은 `AnalysisResult`를 생성한다.
**저장 책임은 `CompositeRepository`에 위임한다. 모듈 D는 저장 로직을 포함하지 않는다.**

---

## 역할 경계 (중요)

```
모듈 D의 책임:  CollectRequest → AnalysisResult 생성
모듈 D의 비책임: 파일 저장, ChromaDB 색인 (CompositeRepository가 처리)
```

---

## 세부 요구사항

- **Factory Pattern 모델 라우터**: `PRIMARY_LLM` 환경변수 하나로 Claude 3.5 Sonnet ↔ Gemini 1.5 Pro 동적 스위칭
- **SLA 안전장치**: Rate Limit(429) 또는 할당량 초과 시 상대 모델 즉시 전환. Exponential Backoff Retry (1s→2s→4s→8s→16s, 최대 5회)
- **연관 후보 추출**: `ChromaRepository.search_hybrid()`로 tags/category 유사 문서 최대 5개 추출. **파일 시스템 직접 파싱 금지**
- **연관 분석 프롬프트**: 신규 문서와 후보 문서 간 관계 필연성 서술 유도. 관련 없으면 링크 생성 안 함
- 반환값: `AnalysisResult` 객체만 반환

---

## LLM 프롬프트 구조

```
SYSTEM: 당신은 지식 관리 전문가입니다. 다음 웹 문서를 분석하여 JSON으로 반환하세요.

USER:
[신규 문서]
제목: {title}
본문: {content}

[기존 연관 후보 문서 (최대 5개)]
{vault_context}  # [{title, summary, category, tags}, ...]

응답 형식:
{
  "summary": "3~5문장 요약",
  "tags": ["태그1", "태그2"],
  "category": "AI/Software Engineering",
  "related_docs": [
    {"title": "기존 문서 제목", "reason": "연관 이유 서술"}
  ],
  "refined_content": "정제된 본문 전문"
}

관련 없는 문서는 related_docs에 포함하지 마세요.
```

---

## Retry 전략

```python
# Exponential Backoff
delays = [1, 2, 4, 8, 16]  # seconds
for i, delay in enumerate(delays):
    try:
        result = await client.analyze(...)
        break
    except LLMRateLimitError:
        if i == 0:
            # 상대 모델로 즉시 전환
            client = LLMFactory.create(fallback_provider)
        else:
            await asyncio.sleep(delay)
```

---

## 파일 구조

```
backend/llm/
├── factory.py           # LLMFactory, BaseLLMClient (인터페이스)
├── claude_client.py     # Anthropic SDK 구현체
└── gemini_client.py     # Google GenerativeAI SDK 구현체
```
