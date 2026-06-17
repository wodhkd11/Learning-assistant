from abc import ABC, abstractmethod

import structlog

from backend.config import settings
from backend.schemas.llm import AnalysisResult

log = structlog.get_logger()


class BaseLLMClient(ABC):
    @abstractmethod
    async def analyze(
        self,
        content: str,
        title: str,
        vault_context: list[dict],
        url: str = "",
    ) -> AnalysisResult:
        """
        문서를 분석하여 AnalysisResult를 반환한다.
        저장 로직은 포함하지 않는다.
        vault_context는 연관 후보 문서 목록 (최대 5개).
        url은 series 판단에 활용된다.
        """
        ...


class LLMFactory:
    @staticmethod
    def get_priority_list() -> list[str]:
        """settings.LLM_PRIORITY 콤마 구분 문자열을 순서 있는 리스트로 반환."""
        return [p.strip() for p in settings.LLM_PRIORITY.split(",") if p.strip()]

    @staticmethod
    def create(provider: str) -> BaseLLMClient:
        """
        provider: 'groq' | 'gemini' | 'claude'
        settings.LLM_PRIORITY 순서로 순회하며 호출.
        """
        if provider == "xai":
            from backend.llm.xai_client import XAIClient
            log.info("llm_factory_create", provider="xai")
            return XAIClient()
        elif provider == "groq":
            from backend.llm.groq_client import GroqClient
            log.info("llm_factory_create", provider="groq")
            return GroqClient()
        elif provider == "gemini":
            from backend.llm.gemini_client import GeminiClient
            log.info("llm_factory_create", provider="gemini")
            return GeminiClient()
        elif provider == "claude":
            from backend.llm.claude_client import ClaudeClient
            log.info("llm_factory_create", provider="claude")
            return ClaudeClient()
        else:
            raise ValueError(
                f"Unknown LLM provider: {provider!r}. Use 'xai', 'groq', 'gemini', or 'claude'."
            )
