# 모듈 C — 로컬 엣지 AI 분류기 (Local LLM Worker)

**담당 코더:** 코더 C
**브랜치:** `feat/module-C-D-llm`
**담당 파일:** `backend/workers/classifier.py`

---

## 목표

Ollama 로컬 LLM으로 문서 지식 가치를 고속 이진 분류하여 상용 API 호출 비용을 최소화한다.

---

## 세부 요구사항

- Ollama HTTP API(`/api/generate`)와 통신. `async httpx.AsyncClient` 사용 필수.
- 초기 권장 모델: `llama3:8b` (4GB VRAM), 저사양 fallback: `phi3:mini`
- Ollama 설치: `curl https://ollama.ai/install.sh | sh` → `ollama pull llama3:8b`
- 구조적 출력 강제: `{is_knowledge: bool, confidence: float, reason: string}` JSON 반환
- 분류 기준:
  - **True**: 기술 블로그, 학술 논문, 튜토리얼, 위키, 공식 문서
  - **False**: 뉴스, SNS, 쇼핑, 광고, 커뮤니티 잡담
- 타임아웃 10초. 장애 시 `OllamaUnavailableError` raise → 호출자(worker_1_loop)가 `.temp/failed_tasks.db`에 저장
- `confidence < 0.6` 시 상용 LLM 재분류 위임 (`settings`로 on/off 가능)

---

## 프롬프트 템플릿

```
SYSTEM: 당신은 웹 콘텐츠 분류기입니다. 반드시 JSON만 반환하세요.
USER: 다음 웹 페이지가 지식/학습 가치가 있는 문서인지 판단하세요.
      제목: {title}
      본문 요약 (500자): {content[:500]}
      응답 형식: {"is_knowledge": bool, "confidence": 0.0~1.0, "reason": "한 줄 이유"}
```

---

## 함수 시그니처

`docs/interfaces.md` 섹션 3 참고.

```python
async def classify(request: CollectRequest) -> ClassificationResult:
    ...
```

---

## Fallback 전략

```
Ollama 타임아웃/미가동
    → OllamaUnavailableError raise
    → worker_1_loop가 .temp/failed_tasks.db에 저장 (status=pending)
    → 30초 간격 최대 3회 재시도
    → 3회 실패 시 analysis_queue에 직접 적재 (상용 LLM이 분류도 담당)
```
