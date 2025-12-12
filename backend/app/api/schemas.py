from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# 接收用户的请求
class ChatRequest(BaseModel):
    query: str = Field(..., description="用户的问题", example="马斯克的太空公司是什么")
    thread_id: str = Field(..., description="会话ID，用于记忆上下文", example="user_123")
    stream: bool = Field(False, description="是否开启流式输出")

# 响应给用户的结构 (非流式模式下使用)
class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []      # 引用了哪些实体
    graph_data: str = ""         # 图谱信息 (可选，用于前端可视化)
    validation_status: str = ""  # 校验状态
    
class ComponentStatus(BaseModel):
    name: str
    status: str  # "healthy", "degraded", "down"
    details: Dict[str, Any] = {}

class SystemHealthResponse(BaseModel):
    timestamp: str
    overall_status: str
    components: List[ComponentStatus]

class ModelConfigInfo(BaseModel):
    model_type: str  # "llm_fast", "llm_smart", "embedding"
    model_name: str
    provider: str
    parameters: Dict[str, Any]  # 温度, top_p 等