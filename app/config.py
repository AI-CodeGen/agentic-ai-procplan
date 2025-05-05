from pydantic_settings import BaseSettings
from functools import lru_cache
from langchain_community.llms import Ollama

class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama2"  # or any other model you have in Ollama
    ALPHA_VANTAGE_API_KEY: str = "NHCUM4XM9S5RIMQT"  # Replace with your API key
    CACHE_EXPIRY: int = 3600  # Cache expiry in seconds (1 hour)
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()

# Initialize LLM
llm = Ollama(
    base_url=settings.OLLAMA_BASE_URL,
    model=settings.OLLAMA_MODEL
) 