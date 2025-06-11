from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional
from enum import Enum

class EndpointSet(Enum):
    BASIC = "basic"
    ALL = "all"
    ALL_WITHOUT_ASYNC_INGEST = "all_without_async_ingest"
    CUSTOM = "custom"

class Settings(BaseSettings):
    server_url: str = Field("https://h2ogpte.genai.h2o.ai")
    api_key: str = Field()
    all_endpoints_as_tools: bool = Field(True)
    endpoint_set: EndpointSet = Field(EndpointSet.ALL_WITHOUT_ASYNC_INGEST, case_sensitive=False)
    custom_endpoint_set_file: Optional[str] = Field(None)

settings = Settings(_env_prefix="H2OGPTE_")
basic_endpoints = [
    "create_collection",
    "list_collections",
    "update_collection",
    "update_collection_prompt_template",
    "delete_collection_prompt_template",
    "reset_collection_prompt_settings",
    "get_collection_settings",
    "update_collection_settings",
    "get_collection_chat_settings",
    "update_collection_chat_settings",
    "list_documents_for_collection",
    "insert_document_into_collection",
    "delete_document_from_collection",
    "list_chat_sessions_for_collection",
    "list_documents",
    "update_document",
    "create_prompt_template",
    "list_prompt_templates",
    "get_default_prompt_template",
    "update_prompt_template",
    "upload_file",
    "ingest_upload",
    "ingest_from_plain_text",
    "ingest_from_website",
    "ingest_from_s3",
    "ingest_from_gcs",
    "ingest_from_azure_blob_storage",
    "create_chat_session",
    "list_chat_sessions",
    "update_chat_session",
    "update_chat_session_prompt_template",
    "delete_chat_session_prompt_template",
    "get_completion",
    "list_models",
    "list_embedding_models",
    "get_default_embedding_model",
]
