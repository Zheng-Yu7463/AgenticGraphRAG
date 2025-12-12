from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.core.logger import logger
from app.api.endpoints import router as chat_router
from app.api.monitor import router as monitor_router
from app.services.hybrid_search import init_hybrid_search
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 服务启动中...")
    
    init_hybrid_search()
    
    try:
        from app.services.qdrant_service import qdrant_manager
        from app.services.data_sync import data_sync_service
        
        client = qdrant_manager.get_client()
        collection = settings.COLLECTION_NAME
        
        if not client.collection_exists(collection) or client.get_collection(collection).points_count == 0:
            logger.info("🔄 首次同步知识库...")
            result = await data_sync_service.sync_knowledge_base()
            logger.info(f"🔄 同步结果: {result}")
        else:
            logger.info("✅ 知识库已就绪")
            
    except Exception as e:
        logger.error(f"❌ 同步失败详情: {e}")
        logger.warning("⚠️ 同步失败，但服务正常启动（可通过 API 手动同步）")
    
    yield
    logger.info("🛑 服务关闭")

app = FastAPI(title="Agentic GraphRAG", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(chat_router, prefix="/api/v1")
app.include_router(monitor_router, prefix="/api/v1/monitor")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)