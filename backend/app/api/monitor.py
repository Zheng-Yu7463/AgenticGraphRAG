from fastapi import APIRouter
from datetime import datetime
import os

import app.services.neo4j_service as neo4j_svc
import app.services.qdrant_service as qdrant_svc
from app.core.config import settings
from app.services.embedding_factory import embedding_factory
from app.api.schemas import SystemHealthResponse, ComponentStatus, ModelConfigInfo
from app.services.data_sync import data_sync_service

router = APIRouter()

@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health():
    """
    全系统健康检查 (Database + Services)
    """
    components = []
    has_error = False

    # 1. 检查 Neo4j
    neo4j_status = neo4j_svc.neo4j_manager.check_health()
    components.append(ComponentStatus(
        name="Neo4j Graph DB",
        status=neo4j_status.get("status", "down"),
        details=neo4j_status
    ))
    if neo4j_status.get("status") == "down": has_error = True

    # 2. 检查 Qdrant
    qdrant_status = qdrant_svc.qdrant_manager.check_health()
    components.append(ComponentStatus(
        name="Qdrant Vector DB",
        status=qdrant_status.get("status", "down"),
        details=qdrant_status
    ))
    if qdrant_status.get("status") == "down": has_error = True

    return SystemHealthResponse(
        timestamp=datetime.now().isoformat(),
        overall_status="unhealthy" if has_error else "healthy",
        components=components
    )

@router.post("/sync")
async def trigger_sync():
    """
    手动触发知识库同步 (Neo4j -> Qdrant)
    当图谱数据更新后，调用此接口刷新向量索引
    """
    try:
        result = await data_sync_service.sync_knowledge_base()
        return result
    except Exception as e:
        return {"status": "failed", "error": str(e)}
    
@router.get("/models")
async def get_model_configs():
    """
    获取当前加载的模型配置信息 (脱敏)
    """
    configs = []
    
    # 获取环境变量中的配置
    # LLM Fast
    configs.append(ModelConfigInfo(
        model_type="LLM (Fast)",
        model_name=settings.MODEL_FAST,
        provider=settings.LLM_BASE_URL,
        parameters={"temperature": settings.LLM_FAST_TEMPERATURE}
    ))
    
    # LLM Smart
    configs.append(ModelConfigInfo(
        model_type="LLM (Smart)",
        model_name=settings.MODEL_SMART,
        provider=settings.LLM_BASE_URL,
        parameters={"temperature": settings.LLM_SMART_TEMPERATURE}
    ))
    
    # LLM Strict
    configs.append(ModelConfigInfo(
        model_type="LLM (Strict)",
        model_name=settings.MODEL_STRICT,
        provider=settings.LLM_BASE_URL,
        parameters={"temperature": settings.LLM_STRICT_TEMPERATURE}
    ))
    
    # Embedding
    
    configs.append(ModelConfigInfo(
        model_type="Embedding",
        model_name=settings.EMBD_MODEL_NAME,
        provider=settings.EMBD_BASE_URL,
        dimensions=settings.EMBD_DIMENSIONS,
        parameters={}
    ))

    return {"models": configs}