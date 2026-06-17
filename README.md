# Learning System

웹 페이지를 자동 수집하여 로컬 Obsidian 볼트에 저장하는 지식 관리 시스템.

## 구성 요소

| 구성 | 설명 |
|------|------|
| Chrome Extension | 방문 페이지 본문 자동 수집 (Readability 기반) |
| FastAPI Backend | 수집 요청 처리, LLM 분석, 저장 |
| Ollama | 로컬 LLM 분류기 (llama3:8b) |
| LLM 분석 | xAI / Gemini / Groq / Claude 멀티 프로바이더 |
| ChromaDB | 벡터 검색 및 중복 감지 |
| Obsidian Vault | Markdown 형태로 로컬 저장 |
| MCP Server | Claude Desktop 연동 |
| Tray App | Windows 시스템 트레이 서버 관리 |

## 빠른 시작

```
1. Ollama 설치: https://ollama.com/download
2. python scripts/setup.py
3. .env 파일에 API 키 입력
4. dist/Learning.exe 실행
4-1. uvicorn backend.main:app --reload(터미널)
```

## 상세 설치

### 1. 사전 요구사항

- Python 3.11 이상
- Ollama ([다운로드](https://ollama.com/download))
- Chrome 브라우저

### 2. 환경 초기화

```bash
python scripts/setup.py
```

초기화 스크립트가 자동으로 수행하는 작업:

- `requirements.txt` 패키지 설치
- Ollama 설치 확인
- `llama3:8b` 모델 자동 다운로드
- `.env` 파일 생성 (`.env.example` 복사)
- 필수 디렉토리 생성 (`obsidian_vault/`, `.temp/`, `data/chroma/`)

### 3. API 키 설정

`.env` 파일을 열어 사용할 LLM 키를 입력한다.

```env
ANTHROPIC_API_KEY=sk-ant-...
XAI_API_KEY=xai-...
GEMINI_API_KEY=AIza...
GROQ_API_KEY=gsk_...
LLM_PRIORITY=xai,gemini,groq,claude
```

### 4. 서버 실행

```bash
uvicorn backend.main:app --reload
# 또는 트레이 앱: dist\Learning.exe 실행 후 트래이 우클릭 후 서버 실행
```

### 5. Chrome Extension 설치

1. `chrome://extensions/` → 개발자 모드 ON
2. "압축해제된 확장 프로그램 로드" → `extension/` 폴더 선택

## 디렉토리 구조

```
KALF/
├── backend/          # FastAPI 애플리케이션
│   ├── llm/          # LLM 클라이언트 (xai/groq/gemini/claude)
│   ├── routers/      # API 엔드포인트
│   ├── storage/      # ChromaDB + Obsidian 저장소
│   ├── utils/        # series_detector 등 유틸리티
│   └── workers/      # classifier, analyzer 워커
├── extension/        # Chrome Extension MV3
├── mcp_server/       # Claude Desktop MCP 서버
├── scripts/          # 관리 스크립트
│   ├── setup.py      # 초기화 스크립트
│   ├── migrate_series.py
│   └── index_vault.py
├── tests/            # pytest 테스트
├── tray/             # Windows 시스템 트레이 앱
└── obsidian_vault/   # 저장된 Markdown 파일
```

## 기존 볼트 색인

이미 Obsidian 볼트가 있다면 ChromaDB에 색인한다.

```bash
python scripts/index_vault.py
```

## 시리즈 마이그레이션

기존 파일을 시리즈별 디렉토리로 재구성한다.

```bash
python scripts/migrate_series.py
```

## 테스트

```bash
pytest tests/ -v
```

## 트레이 앱 빌드

```bash
tray\build.bat
# → dist\KALF.exe 생성
```
