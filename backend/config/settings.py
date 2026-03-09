from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    BACKEND_API_KEY: str
    GEMINI_API_KEY: str
    FRONTEND_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        return [
            "http://localhost:3000",
            self.FRONTEND_URL,
        ]


settings = Settings()
