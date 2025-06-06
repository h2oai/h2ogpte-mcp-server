from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    h2ogpte_server_url: str = Field("http://localhost:8888")
    api_key: str = Field()


settings = Settings()
