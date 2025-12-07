from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.core.state import AgentState
from app.core.nodes.retrieval import retrieve_node
from app.core.nodes.generation import generation_node

# 1. 定义图结构
workflow = StateGraph(AgentState)

# 2. 添加节点
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("generate", generation_node)

# 3. 定义边 (简单的线性流程)
# Start -> Retrieve -> Generate -> End
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)

# 4. 编译图 (带记忆功能)
# MemorySaver 会在内存中保存对话状态
memory = MemorySaver()
app_graph = workflow.compile(checkpointer=memory)