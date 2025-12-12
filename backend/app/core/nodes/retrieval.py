from typing import Dict, Any
from app.core.state import AgentState
import app.services.hybrid_search as search_service 

from app.core.logger import logger

async def retrieve_node(state: AgentState) -> Dict[str, Any]:
    """
    🔍 检索节点
    """
    query = state["query"]
    logger.info(f"🔍 [RETRIEVAL] 开始检索: {query}")
    
    try:
        # ✅ 运行时动态从模块中获取最新的 service 实例
        service = search_service.hybrid_search_service
        
        if service is None:
            raise ValueError("HybridSearchService 尚未初始化！")

        # 调用混合检索服务
        result = await service.search(query)
        
        entities = result.get("entities", [])
        graph_ctx = result.get("graph_context", "")
        text_ctx = result.get("context_text", "")
        
        logger.info(f"   - 找到实体: {entities}")
        
        return {
            "entities": entities,
            "graph_context": graph_ctx,
            "rag_context": text_ctx
        }
    except Exception as e:
        logger.error(f"❌ [RETRIEVAL] 失败: {e}")
        return {
            "entities": [], 
            "graph_context": "", 
            "rag_context": "检索服务暂时不可用。"
        }