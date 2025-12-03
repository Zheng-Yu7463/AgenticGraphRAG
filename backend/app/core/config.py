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

    # --- Neo4j 配置 (自动读取环境变量) ---
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str 
    
    # --- 嵌入模型配置 ---
    EMBD_BASE_URL: str = "https://api.siliconflow.cn/v1/embeddings"
    EMBD_API_KEY: str
    EMBD_MODEL_NAME: str = "Qwen/Qwen3-Embedding-8B"

    # --- Qdrant 配置 (自动读取环境变量) ---
    QDRANT_URL: str = "./qdrant_data"
    QDRANT_API_KEY: str | None = None

    # --- Pydantic 魔法配置 ---
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",  # 精准定位 .env
        env_ignore_empty=True,          # 忽略空行
        extra="ignore",                 # 忽略 .env 里多余的变量 (比如 API_KEY)
        env_file_encoding="utf-8"
    )

# --- 5. 实例化 ---
# 整个项目只需要这就行了，其他地方 import settings 即可
settings = Settings()

# 顺手把日志目录建好 (最佳实践：Fail Fast，如果没权限建目录这里就炸，而不是等写日志时才炸)
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)