from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    agent_base_url: str = "http://localhost:8080"
    cors_origins: str = "http://localhost:3000"
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    class Config:
        env_file = ".env"


settings = Settings()
