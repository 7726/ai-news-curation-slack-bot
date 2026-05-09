from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore", # 정의되지 않은 환경변수가 있어도 에러 무시
    )

    # Slack
    slack_bot_token: str = ""
    slack_signing_secret: str = ""

    # Tavily
    tavily_api_key: str = ""

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = ""

    # AWS
    aws_access_key_id: str = ""      
    aws_secret_access_key: str = ""  
    aws_default_region: str = "ap-northeast-2"
    dynamodb_table_name: str = "ai-news-curation"


settings = Settings()
