# 모듈 F — 하이브리드 검색 엔진 (Vector + Metadata Search)

**담당 코더:** 코더 D
**브랜치:** `feat/module-F-G`
**담당 파일:** `backend/storage/chroma.py`, `backend/routers/search.py`, `scripts/index_vault.py`

---

## 목표

ChromaDB 단일 쿼리로 벡터 유사도와 메타데이터 필터링을 결합한 하이브리드 검색을 제공한다.
**파일 시스템 직접 파싱 없음.**

---

## 핵심 원칙 (위반 금지)

- 키워드 검색(`tags`, `category`, `summary`)은 ChromaDB의 `where` 절 메타데이터 필터로 처리한다.
- 파일 시스템을 직접 파싱하는 코드는 이 모듈에 존재해서는 안 된다.
- 수천 개 문서 축적 시에도 검색 응답 시간 SLO(< 2초)를 유지해야 한다.

---

## 세부 요구사항

- **Vector 검색**: ChromaDB + `sentence-transformers/all-MiniLM-L6-v2` 로컬 임베딩. 외부 임베딩 API 불필요
- **Keyword 검색**: ChromaDB `where` 절 메타데이터 필터 (`tags`, `category`, `summary` 대상)
- **하이브리드 스코어** = Vector 유사도 × `HYBRID_VECTOR_WEIGHT` + Keyword 매칭 스코어 × `(1 - HYBRID_VECTOR_WEIGHT)`
- 검색 결과: `[SearchResult]` 상위 기본 5개
- 신규 문서 색인은 `CompositeRepository`가 처리. 모듈 F(ChromaRepository)는 색인 메서드를 제공하되 직접 호출하지 않음
- 볼트 초기화 CLI: `scripts/index_vault.py` — 기존 볼트 마크다운 전체를 ChromaDB에 일괄 색인

---

## ChromaDB 저장 스키마

`docs/interfaces.md` 섹션 4 참고.

```python
# tags는 반드시 콤마 구분 문자열로 저장
metadata = {
    "url": doc.url,
    "title": doc.title,
    "summary": doc.summary,
    "category": doc.category,
    "tags": ",".join(doc.tags),   # list 타입 금지
    "collected_at": doc.collected_at.isoformat(),
    "file_path": file_path,
}
```

---

## 검색 API 엔드포인트

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/v1/search?q={query}&limit={n}` | 하이브리드 검색 |
| `GET /api/v1/search?tag={tag}` | 태그 기반 메타데이터 필터 검색 |
| `GET /api/v1/document/{title}` | 특정 문서 전문 조회 |
| `GET /api/v1/documents?category=&tag=` | 전체 문서 목록 |
| `POST /api/v1/index/rebuild` | ChromaDB 전체 재색인 트리거 |

---

## index_vault.py 구현 가이드

```bash
# 사용법
python scripts/index_vault.py

# 동작
# 1. obsidian_vault/ 내 모든 .md 파일 탐색
# 2. YAML Front-matter 파싱
# 3. ChromaDB에 exists_by_url() 확인 후 미색인 파일만 색인
# 4. 진행률 표시
```

---

## 주의사항

- `chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)` 사용. 인메모리 클라이언트 금지.
- `get_or_create_collection()` 사용.
- `all-MiniLM-L6-v2` 초기 로드 시 약 80MB 다운로드. 최초 실행 지연 예상.
- `metadata` 값은 `str | int | float | bool`만 허용. `list` 타입 거부됨.
