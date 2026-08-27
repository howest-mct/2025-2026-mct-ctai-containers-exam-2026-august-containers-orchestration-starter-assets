from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://colruyt:colruyt_password@db:5432/colruyt_db"

    model_config = {"env_file": ".env"}


settings = Settings()
