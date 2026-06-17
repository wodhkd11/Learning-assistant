class OllamaUnavailableError(Exception):
    """Ollama 미가동 또는 타임아웃 시 발생. worker_1_loop가 캐치하여 영속 큐에 저장."""


class LLMRateLimitError(Exception):
    """상용 LLM 429 에러. LLMFactory fallback 트리거."""


class LLMAllProvidersFailedError(Exception):
    """Claude, Gemini 모두 실패 시 발생."""
