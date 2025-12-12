# app/core/nodes/validation.py
from typing import Dict, Any, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import PydanticOutputParser

from app.core.state import AgentState
from app.services.llm_factory import llm_factory
from app.prompts.validation import validation_prompt
from app.core.logger import logger

# 1. 更新校验结果结构
class ValidationResult(BaseModel):
    is_valid: bool = Field(..., description="是否通过")
    reason: str = Field(..., description="理由")
    # ✅ 核心修改：明确下一步动作
    action: Literal["pass", "retry_retrieval", "retry_generation"] = Field(..., description="下一步动作")

llm = llm_factory.get_llm(mode="smart")
parser = PydanticOutputParser(pydantic_object=ValidationResult)
chain = validation_prompt | llm | parser

async def validation_node(state: AgentState) -> Dict[str, Any]:
    logger.info("⚖️ [VALIDATION] 正在评估...")
    
    # 获取当前重试次数 (默认为0)
    current_retry = state.get("retry_count", 0)
    
    try:
        score: ValidationResult = await chain.ainvoke({
            "question": state["query"],
            "answer": state["answer"],
            "context": state.get("rag_context", ""),
            "format_instructions": parser.get_format_instructions() 
        })
        
        logger.info(f"   - 动作: {score.action} | 理由: {score.reason} | 重试: {current_retry}")
        
        # 逻辑：如果还要重试，就 +1；如果通过了，就不用动了
        next_retry_count = current_retry + 1 if score.action != "pass" else current_retry
        
        # ⚠️ 关键技巧：把校验失败的原因放入 state，这样 Generate 节点重试时能看到“错在哪了”
        return {
            "validation_status": score.action, # pass / retry_retrieval / retry_generation
            "validation_reason": score.reason,
            "retry_count": next_retry_count,
            # 如果通过了，才写入 messages；没通过就不写，等待下一次循环
            "messages": [AIMessage(content=state["answer"])] if score.action == "pass" else []
        }
        
    except Exception as e:
        logger.error(f"校验失败: {e}")
        # 出错默认放行，防止死循环
        return {
            "validation_status": "pass",
            "messages": [AIMessage(content=state["answer"])],
            "retry_count": current_retry
        }