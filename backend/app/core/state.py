import operator
from typing import Annotated, List, TypedDict, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    LangGraph 状态定义
    messages: 存储完整的对话历史 (User + AI)
    """
    query: str
    # ✅ 核心：add_messages 会自动把新消息 append 到列表末尾，而不是覆盖
    messages: Annotated[List[BaseMessage], add_messages]
    
    # 检索结果
    entities: List[str]
    graph_context: str
    rag_context: str
    
    # 最终答案
    answer: str