from pydantic_settings import BaseSettings
from functools import lru_cache
from langchain_ollama import OllamaLLM

class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama2"  # or any other model you have in Ollama
    ALPHA_VANTAGE_API_KEY: str = ""  # Will be loaded from environment variable
    CACHE_EXPIRY: int = 3600  # Cache expiry in seconds (1 hour)
    No_OF_MANUFACTURERS: int = 3
    STREAMLIT_UI_TIMEOUT_SECONDS: int = 60
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()

# Initialize LLM
llm = OllamaLLM(
    base_url=settings.OLLAMA_BASE_URL,
    model=settings.OLLAMA_MODEL
) 