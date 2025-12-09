from langchain_core.output_parsers import StrOutputParser
from typing import Dict, Any

from app.core.state import AgentState
from app.services.llm_factory import llm_factory
from app.prompts.generation import rag_generation_prompt
from app.core.logger import logger

# 初始化生成链
llm = llm_factory.get_llm(mode="smart")
chain = rag_generation_prompt | llm | StrOutputParser()

async def generation_node(state: AgentState) -> Dict[str, Any]:
    logger.info("🧠 [GENERATION] 生成中...")
    
    # 检查是否有校验失败的反馈
    feedback = ""
    if state.get("validation_reason") and state.get("retry_count", 0) > 0:
        feedback = f"\n\n⚠️ 上一次生成的回答未通过校验，原因是：{state['validation_reason']}。请根据此反馈改进回答。"
        logger.warning(f"   - 接收到重试反馈: {state['validation_reason']}")

    current_context = state.get("rag_context", "") + feedback

    try:
        response = await chain.ainvoke({
            "context": current_context, # 传入带反馈的上下文
            "messages": state.get("messages", []),
            "question": state["query"]
        })
        logger.info(f"🧠 [GENERATION] 生成完成: {response}")
        return {"answer": response}
    except Exception as e:
        return {"answer": "生成出错"}