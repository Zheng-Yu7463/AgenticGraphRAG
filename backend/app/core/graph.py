from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.core.state import AgentState
from app.core.nodes.retrieval import retrieve_node
from app.core.nodes.generation import generation_node
from app.core.nodes.validation import validation_node

# ✅ 路由逻辑函数
def router_logic(state: AgentState) -> Literal["retrieve", "generate", END]:
    """
    根据校验结果和重试次数决定下一步
    """
    status = state.get("validation_status") # pass, retry_retrieval, retry_generation
    retry_count = state.get("retry_count", 0)
    
    # 1. 成功，直接结束
    if status == "pass":
        return END
    
    # 2. 超过最大重试次数 (3次)，强制结束
    # 注意：这里的 retry_count 已经在 validation node 里 +1 了
    if retry_count > 3:
        print("🛑 [Router] 超过最大重试次数 (3次)，强制放行")
        return END
    
    # 3. 分支判断
    if status == "retry_retrieval":
        print("↩️ [Router] 上下文不足 -> 返回检索")
        return "retrieve"
        
    elif status == "retry_generation":
        print("↩️ [Router] 生成质量差 -> 返回重写")
        return "generate"
    
    # 默认情况
    return END

# 1. 初始化
workflow = StateGraph(AgentState)

# 2. 添加节点
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("generate", generation_node)
workflow.add_node("validate", validation_node)

# 3. 设置基础边
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", "validate")

# 4. ✅ 设置条件边
workflow.add_conditional_edges(
    "validate",      # 从校验节点出来
    router_logic,    # 进入路由函数
    {                # 映射返回值
        "retrieve": "retrieve",
        "generate": "generate",
        END: END
    }
)

# 5. 编译
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

__all__ = ["app"]