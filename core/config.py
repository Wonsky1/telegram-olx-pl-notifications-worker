"""Define configuration settings using Pydantic and manage environment variables."""

from logging import getLogger
from typing import Optional

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = getLogger(__name__)

load_dotenv("dev.env")


class Settings(BaseSettings):
    """Class defining configuration settings using Pydantic."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )

    URL: str

    DEFAULT_LAST_MINUTES_GETTING: int = 45
    CYCLE_FREQUENCY_SECONDS: int = 30

    OLX_DB_URL: str

    # Model Configuration
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL_NAME: Optional[str] = None

    GENERATIVE_MODEL: Optional[ChatGroq] = None

    @field_validator("GENERATIVE_MODEL")
    def generative_model(
        cls, value: Optional[ChatGroq], info: ValidationInfo
    ) -> Optional[ChatGroq]:
        env_data = info.data

        model_name = env_data.get("GROQ_MODEL_NAME")
        api_key = env_data.get("GROQ_API_KEY")

        if model_name:
            return ChatGroq(model_name=model_name, api_key=api_key)
        else:
            raise ValueError("GROQ_MODEL_NAME must be set")


settings = Settings()
