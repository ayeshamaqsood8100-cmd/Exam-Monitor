from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Supabase connection variables
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    
    # API Security
    API_KEY: str

    # CORS settings
    FRONTEND_URL: str

    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        return [
            "http://localhost:3000",
            self.FRONTEND_URL
        ]

    class Config:
        env_file = ".env"
        extra = "ignore"

# Create a global instance of the settings to be imported by other files
settings = Settings()
