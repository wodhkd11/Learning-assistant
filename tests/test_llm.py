"""
단위 테스트 — 모듈 C/D (classifier, analyzer, LLM clients)
외부 API(Ollama, Claude, Gemini)는 unittest.mock으로 모킹.
"""
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.exceptions import LLMAllProvidersFailedError, LLMRateLimitError, OllamaUnavailableError
from backend.schemas.document import CollectRequest, RelatedDoc
from backend.schemas.llm import AnalysisResult, ClassificationResult


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def sample_request() -> CollectRequest:
    return CollectRequest(
        url="https://example.com/fastapi-tutorial",
        title="FastAPI 튜토리얼",
        content="FastAPI는 Python 3.7+ 기반의 현대적인 웹 프레임워크입니다. " * 20,
        timestamp=datetime(2026, 6, 13, 0, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_analysis_result() -> AnalysisResult:
    return AnalysisResult(
        summary="FastAPI에 관한 상세 튜토리얼 문서입니다.",
        tags=["fastapi", "python", "webframework"],
        category="AI/Software Engineering",
        related_docs=[
            RelatedDoc(title="Starlette 가이드", reason="FastAPI의 기반 프레임워크")
        ],
        refined_content="정제된 FastAPI 본문 전문입니다.",
    )


@pytest.fixture
def vault_context() -> list[dict]:
    return [
        {
            "title": "Starlette 가이드",
            "summary": "Starlette 프레임워크 개요",
            "category": "AI/Software Engineering",
            "tags": ["starlette", "python"],
        }
    ]


# ──────────────────────────────────────────────
# classifier.py 테스트
# ──────────────────────────────────────────────

class TestClassifier:
    @pytest.mark.asyncio
    async def test_classify_knowledge_document(self, sample_request):
        ollama_response_body = {
            "response": json.dumps(
                {"is_knowledge": True, "confidence": 0.95, "reason": "기술 튜토리얼"}
            )
        }

        mock_response = MagicMock()
        mock_response.json.return_value = ollama_response_body
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            from backend.workers.classifier import classify
            result = await classify(sample_request)

        assert isinstance(result, ClassificationResult)
        assert result.is_knowledge is True
        assert result.confidence == pytest.approx(0.95)
        assert result.reason == "기술 튜토리얼"
        assert result.model_used.startswith("ollama/")
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_classify_non_knowledge_document(self, sample_request):
        ollama_response_body = {
            "response": json.dumps(
                {"is_knowledge": False, "confidence": 0.88, "reason": "SNS 게시물"}
            )
        }
        mock_response = MagicMock()
        mock_response.json.return_value = ollama_response_body
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            from backend.workers.classifier import classify
            result = await classify(sample_request)

        assert result.is_knowledge is False

    @pytest.mark.asyncio
    async def test_classify_ollama_timeout_raises(self, sample_request):
        import httpx

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client_cls.return_value = mock_client

            from backend.workers.classifier import classify
            with pytest.raises(OllamaUnavailableError):
                await classify(sample_request)

    @pytest.mark.asyncio
    async def test_classify_ollama_connect_error_raises(self, sample_request):
        import httpx

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mock_client_cls.return_value = mock_client

            from backend.workers.classifier import classify
            with pytest.raises(OllamaUnavailableError):
                await classify(sample_request)

    @pytest.mark.asyncio
    async def test_classify_json_extraction_fallback(self, sample_request):
        # Ollama가 JSON 주변에 추가 텍스트를 반환하는 경우
        raw_with_noise = 'Some preamble {"is_knowledge": true, "confidence": 0.7, "reason": "ok"} end'
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": raw_with_noise}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            from backend.workers.classifier import classify
            result = await classify(sample_request)

        assert result.is_knowledge is True
        assert result.confidence == pytest.approx(0.7)


# ──────────────────────────────────────────────
# LLMFactory 테스트
# ──────────────────────────────────────────────

class TestLLMFactory:
    def test_create_claude_returns_claude_client(self):
        from backend.llm.factory import LLMFactory
        from backend.llm.claude_client import ClaudeClient

        with patch("backend.llm.claude_client.anthropic.AsyncAnthropic"):
            client = LLMFactory.create("claude")
        assert isinstance(client, ClaudeClient)

    def test_create_gemini_returns_gemini_client(self):
        from backend.llm.factory import LLMFactory
        from backend.llm.gemini_client import GeminiClient

        with patch("backend.llm.gemini_client.genai.Client"):
            client = LLMFactory.create("gemini")
        assert isinstance(client, GeminiClient)

    def test_create_groq_returns_groq_client(self):
        from backend.llm.factory import LLMFactory
        from backend.llm.groq_client import GroqClient

        with patch("backend.llm.groq_client.AsyncGroq"):
            client = LLMFactory.create("groq")
        assert isinstance(client, GroqClient)

    def test_create_xai_returns_xai_client(self):
        from backend.llm.factory import LLMFactory
        from backend.llm.xai_client import XAIClient

        with patch("backend.llm.xai_client.AsyncOpenAI"):
            client = LLMFactory.create("xai")
        assert isinstance(client, XAIClient)

    def test_get_priority_list_parses_setting(self):
        from backend.llm.factory import LLMFactory

        with patch("backend.llm.factory.settings") as mock_settings:
            mock_settings.LLM_PRIORITY = "groq,gemini,claude"
            providers = LLMFactory.get_priority_list()
        assert providers == ["groq", "gemini", "claude"]

    def test_get_priority_list_strips_spaces(self):
        from backend.llm.factory import LLMFactory

        with patch("backend.llm.factory.settings") as mock_settings:
            mock_settings.LLM_PRIORITY = "groq, gemini , claude"
            providers = LLMFactory.get_priority_list()
        assert providers == ["groq", "gemini", "claude"]

    def test_create_unknown_provider_raises(self):
        from backend.llm.factory import LLMFactory

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            LLMFactory.create("openai")


# ──────────────────────────────────────────────
# ClaudeClient 테스트
# ──────────────────────────────────────────────

class TestClaudeClient:
    def _make_client(self):
        with patch("backend.llm.claude_client.anthropic.AsyncAnthropic"):
            from backend.llm.claude_client import ClaudeClient
            return ClaudeClient()

    @pytest.mark.asyncio
    async def test_analyze_returns_analysis_result(self, vault_context, sample_analysis_result):
        client = self._make_client()

        fake_json = json.dumps({
            "summary": sample_analysis_result.summary,
            "tags": sample_analysis_result.tags,
            "category": sample_analysis_result.category,
            "related_docs": [
                {"title": r.title, "reason": r.reason}
                for r in sample_analysis_result.related_docs
            ],
            "refined_content": sample_analysis_result.refined_content,
        })

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=fake_json)]
        client._client.messages.create = AsyncMock(return_value=mock_message)

        result = await client.analyze(
            content="FastAPI 본문",
            title="FastAPI 튜토리얼",
            vault_context=vault_context,
        )

        assert isinstance(result, AnalysisResult)
        assert result.summary == sample_analysis_result.summary
        assert result.tags == sample_analysis_result.tags
        assert result.category == sample_analysis_result.category
        assert len(result.related_docs) == 1

    @pytest.mark.asyncio
    async def test_analyze_rate_limit_raises(self, vault_context):
        import anthropic as _anthropic

        client = self._make_client()

        rate_limit_exc = _anthropic.RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429, headers={}),
            body={},
        )
        client._client.messages.create = AsyncMock(side_effect=rate_limit_exc)

        with pytest.raises(LLMRateLimitError):
            await client.analyze("content", "title", vault_context)

    @pytest.mark.asyncio
    async def test_analyze_json_with_noise_extracted(self, vault_context):
        client = self._make_client()

        inner_json = json.dumps({
            "summary": "요약",
            "tags": ["a"],
            "category": "Dev",
            "related_docs": [],
            "refined_content": "본문",
        })
        noisy_response = f"```json\n{inner_json}\n```"

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=noisy_response)]
        client._client.messages.create = AsyncMock(return_value=mock_message)

        result = await client.analyze("c", "t", vault_context)
        assert result.summary == "요약"

    @pytest.mark.asyncio
    async def test_analyze_series_fields_populated(self, vault_context):
        """LLM 응답의 series 필드가 AnalysisResult에 그대로 반영되어야 한다."""
        client = self._make_client()

        fake_json = json.dumps({
            "summary": "요약",
            "tags": ["python"],
            "category": "Dev",
            "related_docs": [],
            "refined_content": "본문",
            "series": "cpp-beginner-wikidocs",
            "series_title": "C++ 입문",
            "series_order": 3,
        })
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=fake_json)]
        client._client.messages.create = AsyncMock(return_value=mock_message)

        result = await client.analyze(
            "본문", "C++ 3챕터", vault_context,
            url="https://wikidocs.net/12345/3",
        )

        assert result.series == "cpp-beginner-wikidocs"
        assert result.series_title == "C++ 입문"
        assert result.series_order == 3

    @pytest.mark.asyncio
    async def test_analyze_series_null_when_independent(self, vault_context):
        """독립 문서인 경우 series 필드는 None이어야 한다."""
        client = self._make_client()

        fake_json = json.dumps({
            "summary": "요약",
            "tags": ["misc"],
            "category": "General",
            "related_docs": [],
            "refined_content": "본문",
            "series": None,
            "series_title": None,
            "series_order": None,
        })
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=fake_json)]
        client._client.messages.create = AsyncMock(return_value=mock_message)

        result = await client.analyze("본문", "독립 문서", vault_context)

        assert result.series is None
        assert result.series_title is None
        assert result.series_order is None


# ──────────────────────────────────────────────
# XAIClient 테스트
# ──────────────────────────────────────────────

class TestXAIClient:
    def _make_client(self):
        with patch("backend.llm.xai_client.AsyncOpenAI"):
            from backend.llm.xai_client import XAIClient
            return XAIClient()

    @pytest.mark.asyncio
    async def test_analyze_returns_analysis_result(self, vault_context, sample_analysis_result):
        client = self._make_client()

        fake_json = json.dumps({
            "summary": sample_analysis_result.summary,
            "tags": sample_analysis_result.tags,
            "category": sample_analysis_result.category,
            "related_docs": [
                {"title": r.title, "reason": r.reason}
                for r in sample_analysis_result.related_docs
            ],
            "refined_content": sample_analysis_result.refined_content,
        })

        mock_message = MagicMock()
        mock_message.content = fake_json
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        client._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await client.analyze(
            content="FastAPI 본문",
            title="FastAPI 튜토리얼",
            vault_context=vault_context,
        )

        assert isinstance(result, AnalysisResult)
        assert result.tags == sample_analysis_result.tags

    @pytest.mark.asyncio
    async def test_analyze_rate_limit_raises(self, vault_context):
        from openai import RateLimitError as OpenAIRateLimitError

        client = self._make_client()

        mock_response = MagicMock(status_code=429, headers={})
        rate_limit_exc = OpenAIRateLimitError(
            message="Rate limit exceeded",
            response=mock_response,
            body={},
        )
        client._client.chat.completions.create = AsyncMock(side_effect=rate_limit_exc)

        with pytest.raises(LLMRateLimitError):
            await client.analyze("content", "title", vault_context)


# ──────────────────────────────────────────────
# GroqClient 테스트
# ──────────────────────────────────────────────

class TestGroqClient:
    def _make_client(self):
        with patch("backend.llm.groq_client.AsyncGroq"):
            from backend.llm.groq_client import GroqClient
            return GroqClient()

    @pytest.mark.asyncio
    async def test_analyze_returns_analysis_result(self, vault_context, sample_analysis_result):
        client = self._make_client()

        fake_json = json.dumps({
            "summary": sample_analysis_result.summary,
            "tags": sample_analysis_result.tags,
            "category": sample_analysis_result.category,
            "related_docs": [
                {"title": r.title, "reason": r.reason}
                for r in sample_analysis_result.related_docs
            ],
            "refined_content": sample_analysis_result.refined_content,
        })

        mock_message = MagicMock()
        mock_message.content = fake_json
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        client._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await client.analyze(
            content="FastAPI 본문",
            title="FastAPI 튜토리얼",
            vault_context=vault_context,
        )

        assert isinstance(result, AnalysisResult)
        assert result.tags == sample_analysis_result.tags

    @pytest.mark.asyncio
    async def test_analyze_rate_limit_raises(self, vault_context):
        from groq import RateLimitError as GroqRateLimitError

        client = self._make_client()

        mock_response = MagicMock(status_code=429, headers={})
        rate_limit_exc = GroqRateLimitError(
            message="Rate limit exceeded",
            response=mock_response,
            body={},
        )
        client._client.chat.completions.create = AsyncMock(side_effect=rate_limit_exc)

        with pytest.raises(LLMRateLimitError):
            await client.analyze("content", "title", vault_context)


# ──────────────────────────────────────────────
# GeminiClient 테스트
# ──────────────────────────────────────────────

class TestGeminiClient:
    def _make_client(self):
        with patch("backend.llm.gemini_client.genai.Client"):
            from backend.llm.gemini_client import GeminiClient
            return GeminiClient()

    @pytest.mark.asyncio
    async def test_analyze_returns_analysis_result(self, vault_context, sample_analysis_result):
        client = self._make_client()

        fake_json = json.dumps({
            "summary": sample_analysis_result.summary,
            "tags": sample_analysis_result.tags,
            "category": sample_analysis_result.category,
            "related_docs": [
                {"title": r.title, "reason": r.reason}
                for r in sample_analysis_result.related_docs
            ],
            "refined_content": sample_analysis_result.refined_content,
        })

        mock_response = MagicMock(text=fake_json)
        client._client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await client.analyze(
            content="FastAPI 본문",
            title="FastAPI 튜토리얼",
            vault_context=vault_context,
        )

        assert isinstance(result, AnalysisResult)
        assert result.tags == sample_analysis_result.tags

    @pytest.mark.asyncio
    async def test_analyze_rate_limit_raises(self, vault_context):
        from google.genai import errors as genai_errors

        client = self._make_client()
        rate_limit_exc = genai_errors.ClientError(429, "quota exceeded")
        client._client.aio.models.generate_content = AsyncMock(
            side_effect=rate_limit_exc
        )

        with pytest.raises(LLMRateLimitError):
            await client.analyze("content", "title", vault_context)


# ──────────────────────────────────────────────
# analyzer.py 테스트
# ──────────────────────────────────────────────

class TestAnalyzer:
    def _make_mock_repo(self, vault_context: list[dict]) -> MagicMock:
        repo = MagicMock()
        repo.search = AsyncMock(return_value=vault_context)
        return repo

    @pytest.mark.asyncio
    async def test_analyze_returns_document_record(
        self, sample_request, sample_analysis_result, vault_context
    ):
        repo = self._make_mock_repo(vault_context)
        mock_client = AsyncMock()
        mock_client.analyze = AsyncMock(return_value=sample_analysis_result)

        with patch("backend.workers.analyzer.LLMFactory.create", return_value=mock_client), \
             patch("backend.workers.analyzer.LLMFactory.get_priority_list", return_value=["groq"]):
            from backend.workers.analyzer import analyze
            doc = await analyze(sample_request, repo)

        assert doc.url == sample_request.url
        assert doc.source_title == sample_request.title
        assert doc.summary == sample_analysis_result.summary
        assert doc.tags == sample_analysis_result.tags
        assert doc.category == sample_analysis_result.category
        assert len(doc.related_docs) == 1
        assert doc.collected_at == sample_request.timestamp

    @pytest.mark.asyncio
    async def test_analyze_switches_to_fallback_on_rate_limit(
        self, sample_request, sample_analysis_result, vault_context
    ):
        repo = self._make_mock_repo(vault_context)

        primary_client = AsyncMock()
        primary_client.analyze = AsyncMock(side_effect=LLMRateLimitError("429"))

        fallback_client = AsyncMock()
        fallback_client.analyze = AsyncMock(return_value=sample_analysis_result)

        call_count = 0

        def factory_side_effect(provider: str):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return primary_client
            return fallback_client

        with patch("backend.workers.analyzer.LLMFactory.create", side_effect=factory_side_effect), \
             patch("backend.workers.analyzer.LLMFactory.get_priority_list", return_value=["groq", "gemini"]):
            from backend.workers.analyzer import analyze
            doc = await analyze(sample_request, repo)

        assert doc.summary == sample_analysis_result.summary
        assert call_count == 2  # primary + fallback 생성

    @pytest.mark.asyncio
    async def test_analyze_raises_when_all_providers_fail(
        self, sample_request, vault_context
    ):
        repo = self._make_mock_repo(vault_context)

        mock_client = AsyncMock()
        mock_client.analyze = AsyncMock(side_effect=LLMRateLimitError("429"))

        with patch("backend.workers.analyzer.LLMFactory.create", return_value=mock_client), \
             patch("backend.workers.analyzer.LLMFactory.get_priority_list", return_value=["groq", "gemini", "claude"]):
            from backend.workers.analyzer import analyze
            with pytest.raises(LLMAllProvidersFailedError):
                await analyze(sample_request, repo)

    @pytest.mark.asyncio
    async def test_analyze_calls_repo_search_for_vault_context(
        self, sample_request, sample_analysis_result, vault_context
    ):
        repo = self._make_mock_repo(vault_context)
        mock_client = AsyncMock()
        mock_client.analyze = AsyncMock(return_value=sample_analysis_result)

        with patch("backend.workers.analyzer.LLMFactory.create", return_value=mock_client), \
             patch("backend.workers.analyzer.LLMFactory.get_priority_list", return_value=["groq"]):
            from backend.workers.analyzer import analyze
            await analyze(sample_request, repo)

        repo.search.assert_called_once_with(sample_request.title, limit=5)

    @pytest.mark.asyncio
    async def test_analyze_does_not_call_repo_save(
        self, sample_request, sample_analysis_result, vault_context
    ):
        repo = self._make_mock_repo(vault_context)
        repo.save = AsyncMock()
        mock_client = AsyncMock()
        mock_client.analyze = AsyncMock(return_value=sample_analysis_result)

        with patch("backend.workers.analyzer.LLMFactory.create", return_value=mock_client), \
             patch("backend.workers.analyzer.LLMFactory.get_priority_list", return_value=["groq"]):
            from backend.workers.analyzer import analyze
            await analyze(sample_request, repo)

        repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_analyze_series_from_llm_in_document_record(
        self, sample_request, vault_context
    ):
        """LLM이 반환한 series 필드가 DocumentRecord에 그대로 반영되어야 한다."""
        repo = self._make_mock_repo(vault_context)

        llm_result = AnalysisResult(
            summary="요약",
            tags=["python"],
            category="Dev",
            related_docs=[],
            refined_content="본문",
            series="fastapi-tutorial-wikidocs",
            series_title="FastAPI 튜토리얼",
            series_order=2,
        )
        mock_client = AsyncMock()
        mock_client.analyze = AsyncMock(return_value=llm_result)

        with patch("backend.workers.analyzer.LLMFactory.create", return_value=mock_client), \
             patch("backend.workers.analyzer.LLMFactory.get_priority_list", return_value=["groq"]):
            from backend.workers.analyzer import analyze
            doc = await analyze(sample_request, repo)

        assert doc.series == "fastapi-tutorial-wikidocs"
        assert doc.series_title == "FastAPI 튜토리얼"
        assert doc.series_order == 2

        # url이 analyze()에 전달되었는지 확인
        mock_client.analyze.assert_called_once()
        call_kwargs = mock_client.analyze.call_args.kwargs
        assert call_kwargs.get("url") == sample_request.url
