import operator
from typing import Annotated, List, TypedDict, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    CRAG Agent 状态定义
    """
    # 用户输入
    query: str
    
    # ---------------- 历史对话 ----------------
    messages: Annotated[List[BaseMessage], add_messages]
    
    # ---------------- 检索数据 ----------------
    entities: List[str]      # 提取出的实体
    graph_context: str       # 图谱关系
    rag_context: str         # 最终拼接的上下文文本
    
    # ---------------- 中间结果 ----------------
    answer: str              # 生成节点产生的原始回答
    
    # ---------------- 校验结果 ----------------
    validation_status: str   # valid / invalid / error
    validation_reason: str   # 评分理由
    
    retry_count: int