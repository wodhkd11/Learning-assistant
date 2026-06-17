from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    VAULT_PATH: str = str(Path(__file__).parent.parent / "obsidian_vault")
    CHROMA_DB_PATH: str = "./data/chroma"
    TEMP_DIR: str = "./.temp"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3:8b"
    OLLAMA_TIMEOUT: int = 10

    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    XAI_API_KEY: str = ""
    PRIMARY_LLM: str = "claude"
    LLM_PRIORITY: str = "xai,groq,gemini,claude"

    HYBRID_VECTOR_WEIGHT: float = 0.7

    LOG_LEVEL: str = "INFO"
    KALF_API_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"


settings = Settings()
