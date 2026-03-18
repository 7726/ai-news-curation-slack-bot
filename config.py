from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Slack
    slack_bot_token: str = ""
    slack_signing_secret: str = ""

    # Tavily
    tavily_api_key: str = ""

    # Gemini
    gemini_api_key: str = ""

    # AWS
    aws_default_region: str = "ap-northeast-2"
    dynamodb_table_name: str = "ai-news-curation"


settings = Settings()
