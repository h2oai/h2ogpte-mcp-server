from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    h2ogpte_server_url: str = Field("https://h2ogpte.genai.h2o.ai")
    api_key: str = Field()
    all_endpoints_as_tools: bool = Field(True)


settings = Settings()
