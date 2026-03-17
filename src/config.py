"""RedThread configuration management."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # FalkorDB
    falkordb_host: str = "localhost"
    falkordb_port: int = 6379
    falkordb_graph_name: str = "redthread"

    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = False
    app_log_level: str = "info"

    # SQLite
    sqlite_db_path: str = "./data/redthread.db"

    # Security
    secret_key: str = "change-me-in-production"

    # LLM (for natural language → Cypher)
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = "gpt-4o-mini"

    # Query limits
    max_path_depth: int = 8
    max_results: int = 100
    max_import_rows: int = 50_000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def sqlite_dir(self) -> Path:
        return Path(self.sqlite_db_path).parent


settings = Settings()
