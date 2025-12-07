from langchain_core.messages import AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Dict, Any

from app.core.state import AgentState
from app.services.llm_factory import llm_factory
from app.core.logger import logger

# 初始化 LLM
llm = llm_factory.get_llm(mode="smart")

# 定义 Prompt
rag_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个专业的智能助手。请基于以下上下文回答用户的问题。
    
    上下文信息：
    {context}
    
    注意：
    1. 如果上下文包含图谱实体关系，请在回答中自然体现。
    2. 保持回答条理清晰。"""),
    
    # ✅ 自动插入历史消息 (User + AI)
    MessagesPlaceholder(variable_name="messages"),
    
    ("user", "{question}")
])

# LCEL 链
rag_chain = rag_prompt | llm | StrOutputParser()

async def generation_node(state: AgentState) -> Dict[str, Any]:
    """
    生成节点：生成回答并更新历史
    """
    logger.info("🧠 [生成节点] 正在生成回答...")
    
    query = state["query"]
    context = state.get("rag_context", "")
    messages = state.get("messages", [])
    
    try:
        response_text = await rag_chain.ainvoke({
            "context": context,
            "messages": messages,
            "question": query
        })
        
        logger.success("✅ 回答生成完毕")
        
        return {
            "answer": response_text,
            "messages": [AIMessage(content=response_text)]
        }
    except Exception as e:
        logger.error(f"❌ 生成失败: {e}")
        return {
            "answer": "抱歉，生成回答时出现错误。",
            "messages": [AIMessage(content="系统错误")]
        }