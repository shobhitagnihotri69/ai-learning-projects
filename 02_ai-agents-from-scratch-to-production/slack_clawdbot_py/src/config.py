import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env file from the current directory or parent directories
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class SlackConfig(BaseModel):
    bot_token: str = Field(default_factory=lambda: os.getenv("SLACK_BOT_TOKEN", ""))
    app_token: str = Field(default_factory=lambda: os.getenv("SLACK_APP_TOKEN", ""))
    signing_secret: str = Field(default_factory=lambda: os.getenv("SLACK_SIGNING_SECRET", ""))
    user_token: str = Field(default_factory=lambda: os.getenv("SLACK_USER_TOKEN", ""))

class AIConfig(BaseModel):
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    anthropic_api_key: str = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    default_model: str = Field(default_factory=lambda: os.getenv("DEFAULT_MODEL", "gpt-4o"))

class RAGConfig(BaseModel):
    enabled: bool = Field(default_factory=lambda: os.getenv("RAG_ENABLED", "true").lower() == "true")
    auto_index: bool = Field(default_factory=lambda: os.getenv("RAG_AUTO_INDEX", "true").lower() == "true")
    max_results: int = Field(default_factory=lambda: int(os.getenv("RAG_MAX_RESULTS", "5")))
    min_similarity: float = Field(default_factory=lambda: float(os.getenv("RAG_MIN_SIMILARITY", "0.65")))
    embedding_model: str = Field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))
    indexer_interval_hours: int = Field(default_factory=lambda: int(os.getenv("INDEXER_INTERVAL_HOURS", "6")))

class MemoryConfig(BaseModel):
    enabled: bool = Field(default_factory=lambda: os.getenv("MEMORY_ENABLED", "true").lower() == "true")
    api_key: str = Field(default_factory=lambda: os.getenv("MEM0_API_KEY", ""))

class FeaturesConfig(BaseModel):
    reactions: bool = True
    typing_indicator: bool = True
    require_approval: bool = False

class AppConfig(BaseModel):
    database_path: str = Field(
        default_factory=lambda: os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "slack_assistant.db"))
    )
    vectorstore_path: str = Field(
        default_factory=lambda: os.getenv("VECTORSTORE_PATH", str(BASE_DIR / "data" / "vectorstore.json"))
    )
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    timezone: str = "Asia/Kolkata"

class Config(BaseModel):
    slack: SlackConfig = Field(default_factory=SlackConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    app: AppConfig = Field(default_factory=AppConfig)

# Global configuration instance
config = Config()
