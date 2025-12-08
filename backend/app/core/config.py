from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- 1. 路径锚点 (绝对路径) ---
# 无论在哪里运行，这里永远指向 backend/app/core/config.py
# .parent -> core
# .parent.parent -> app
# .parent.parent.parent -> backend (项目根目录)
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # --- 基础路径配置 ---
    BASE_DIR: Path = BACKEND_DIR
    LOG_DIR: Path = BACKEND_DIR / "logs"
    
    # --- 模型提供商 ---
    LLM_BASE_URL: str = "https://api.openai.com/v1" 
    LLM_API_KEY: str

    # --- 模型名称配置 ---
    MODEL_SMART: str = "gpt-4o"  
    MODEL_FAST: str = "gpt-4o-mini" 
    MODEL_STRICT: str = "gpt-4o"

    LLM_FAST_TEMPERATURE: float = 0.0
    LLM_SMART_TEMPERATURE: float = 0.7
    LLM_STRICT_TEMPERATURE: float = 0.0
    
    # --- Neo4j 配置 (自动读取环境变量) ---
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str 
    
    # --- 嵌入模型配置 ---
    EMBD_BASE_URL: str = "https://api.siliconflow.cn/v1/"
    EMBD_API_KEY: str
    EMBD_MODEL_NAME: str = "Qwen/Qwen3-Embedding-8B"
    EMBD_DIMENSIONS: int = 4096

    # --- Qdrant 配置 (自动读取环境变量) ---
    QDRANT_URL: str = "./qdrant_data"
    QDRANT_API_KEY: str | None = None

    # --- Pydantic 魔法配置 ---
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",  # 定位 .env
        env_ignore_empty=True,          # 忽略空行
        extra="ignore",                 # 忽略 .env 里多余的变量
        env_file_encoding="utf-8"
    )

# --- 5. 实例化 ---
settings = Settings()
# 确保日志目录存在
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)