# TODO.md — 코더 간 소통 채널

> 블로커, 인터페이스 변경 요청, 진행 상황을 여기에 기록한다.
> 오케스트레이터가 매 PR 전 확인한다.

---

## 형식

```
[BLOCKER] 코더X: 질문 또는 블로커 내용
[REQUEST] 코더X: 인터페이스 변경 요청 내용
[DONE] 코더X: 완료한 작업 요약
[NOTE] 코더X: 참고사항
```

---

## 현재 항목

[DONE] 코더A: feat/module-A-B 브랜치에 모듈 A(extension/)와 모듈 B(backend core) 구현 완료.
  - extension/: manifest.json(MV3), background.js(Service Worker + 오프라인 큐), content.js(Readability 추출), readability.js(최소 구현체 — 프로덕션 배포 전 Mozilla 원본으로 교체), blacklist.json
  - backend/config.py, exceptions.py, schemas/ (document/llm/search), storage/repository.py (BaseRepository ABC)
  - backend/routers/collect.py: POST /api/v1/collect (블랙리스트·중복 체크 → asyncio.Queue.put → 즉시 200 OK)
  - backend/workers/queue_manager.py: worker_1_loop, worker_2_loop 골격 + check_ollama_connection
  - backend/temp/queue_db.py: aiosqlite 기반 failed_tasks.db CRUD + reload_failed_tasks
  - backend/main.py: FastAPI lifespan 7단계 startup 순서 준수
  - .env.example: 전체 환경변수 명세
  - tests/test_collect.py: 10개 단위 테스트 (queued/blacklisted/duplicate/스키마 검증/worker 오류 처리)

[NOTE] 코더A: extension/readability.js는 최소 호환 구현체임. 프로덕션 배포 전 https://github.com/mozilla/readability/blob/main/Readability.js 로 교체 필요.
[NOTE] 코더A: backend/storage/{obsidian,chroma,composite}.py는 각 담당 코더(B, D) 구현을 위한 인터페이스 스텁으로 생성됨. 실제 로직은 해당 코더가 채워 넣는다.

[DONE] 코더C: feat/module-C-D-llm 브랜치에 모듈 C(Ollama 분류기) + 모듈 D(상용 LLM 분석기) 구현 완료.
  - backend/llm/factory.py: BaseLLMClient ABC + LLMFactory.create('claude'|'gemini')
  - backend/llm/claude_client.py: Claude claude-sonnet-4-6 분석 클라이언트, LLMRateLimitError 처리
  - backend/llm/gemini_client.py: Gemini 1.5 Pro 분석 클라이언트, LLMRateLimitError 처리
  - backend/workers/classifier.py: Ollama API 이진 분류, OllamaUnavailableError 전파
  - backend/workers/analyzer.py: repo.search() → LLMFactory → DocumentRecord 조립, 저장은 호출자 책임
  - tests/test_llm.py: 18개 단위 테스트 (classifier 5 / LLMFactory 3 / ClaudeClient 3 / GeminiClient 2 / analyzer 5)

[DONE] 코더D: feat/module-F-G 브랜치에 모듈 F(하이브리드 검색) + 모듈 G(MCP 서버) 구현 완료.
  - backend/storage/chroma.py: ChromaRepository (PersistentClient, all-MiniLM-L6-v2, 하이브리드 스코어링, tags 콤마 문자열 저장)
  - backend/routers/search.py: GET /search, /document/{title}, /documents, /search/stats, POST /index/rebuild
  - mcp_server/server.py: stdio transport MCP 서버 (search_vault, get_document, list_documents, get_related, get_stats)
  - scripts/index_vault.py: 볼트 일괄 색인 CLI
  - tests/test_search.py, tests/test_mcp.py: 단위 테스트

[DONE] 코더D (추가): search.py _chroma 직접 접근 제거 및 CompositeRepository 위임 완료 (feat/module-F-G 머지).
  - composite.py에 list_documents(), get_stats() 구현 추가
  - search.py: _chroma 헬퍼 제거, composite.search/list_documents/get_stats 위임
  - main.py search 라우터 등록은 오케스트레이터가 처리 완료
