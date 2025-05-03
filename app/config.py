from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama2"  # or any other model you have in Ollama
    
    class Config:
        env_file = ".env"

settings = Settings() 