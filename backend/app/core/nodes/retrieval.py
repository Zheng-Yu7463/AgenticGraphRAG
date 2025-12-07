from typing import Dict, Any
from app.core.state import AgentState
from app.services.hybrid_search import hybrid_search_service
from app.core.logger import logger

async def retrieve_node(state: AgentState) -> Dict[str, Any]:
    """
    检索节点：调用 Hybrid Search
    """
    query = state["query"]
    logger.info(f"🔍 [检索节点] 开始检索: {query}")
    
    try:
        # 调用之前写好的混合检索服务
        result = await hybrid_search_service.search(query)
        
        return {
            "entities": result.get("entities", []),
            "graph_context": result.get("graph_context", ""),
            "rag_context": result.get("context_text", "")
        }
    except Exception as e:
        logger.error(f"❌ [检索节点] 失败: {e}")
        return {
            "entities": [],
            "graph_context": "",
            "rag_context": "检索服务暂时不可用。"
        }