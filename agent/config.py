"""
Configuration module for the Markaz Exam Monitor agent.
Uses pydantic-settings to load environment variables from the project root .env file.
"""
import os
from pydantic_settings import BaseSettings

# Determine the absolute path to the project root directory.
# Since this file is at PROJECT_ROOT/agent/config.py, we go up two levels.
# This ensures it always finds the .env file regardless of current working directory.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE_PATH = os.path.join(ROOT_DIR, '.env')

class Settings(BaseSettings):
    """
    Agent settings loaded securely from the project root environment variables.
    """
    BACKEND_URL: str
    API_KEY: str
    EXAM_ID: str  # Validated manually in main.py to provide a clean error message

    class Config:
        env_file = ENV_FILE_PATH
        extra = "ignore"  # Ignore overlapping variables in .env intended for backend

settings = Settings()
