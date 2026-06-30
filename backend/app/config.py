import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./lmls.db"
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    PORT: int = 8000

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Ensure backend data directory exists for SQLite
if settings.DATABASE_URL.startswith("sqlite:////app/data/"):
    os.makedirs("/app/data", exist_ok=True)
elif settings.DATABASE_URL.startswith("sqlite:///./"):
    os.makedirs("./", exist_ok=True)
