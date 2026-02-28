from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    agent_base_url: str = "http://localhost:8080"
    cors_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
