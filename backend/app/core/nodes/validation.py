from typing import Dict, Any, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import PydanticOutputParser # ✅ 引入解析器

from app.core.state import AgentState
from app.services.llm_factory import llm_factory
from app.prompts.validation import validation_prompt
from app.core.logger import logger

# 1. 定义输出结构
class ValidationResult(BaseModel):
    is_valid: bool = Field(..., description="回答是否有效且准确，true或false")
    reason: str = Field(..., description="简短的判断理由")
    status: Literal["valid", "invalid"] = Field(..., description="状态字符串")

# 2. 初始化组件
llm = llm_factory.get_llm(mode="smart")

parser = PydanticOutputParser(pydantic_object=ValidationResult)

# 3. 构建 Chain：Prompt -> LLM -> Parser
chain = validation_prompt | llm | parser

async def validation_node(state: AgentState) -> Dict[str, Any]:
    """
    ⚖️ 校验节点 (通用兼容版)
    """
    logger.info("⚖️ [VALIDATION] 正在校验...")
    
    query = state["query"]
    answer = state["answer"]
    context = state.get("rag_context", "")
    
    try:
        # 执行校验
        # ✅ 必须传入 format_instructions，LangChain 会自动生成一段
        # "The output should be formatted as a JSON instance..." 的指令
        score: ValidationResult = await chain.ainvoke({
            "question": query,
            "answer": answer,
            "context": context,
            "format_instructions": parser.get_format_instructions() 
        })
        
        logger.info(f"   - 结果: {score.status.upper()} | 理由: {score.reason}")
        
        # 处理最终回答
        final_answer = answer
        
        # 如果校验不通过，给回答打上补丁
        if not score.is_valid:
            final_answer = f"⚠️ [系统提示: 此回答可能存在偏差]\n{answer}\n\n(校验员备注: {score.reason})"
        
        return {
            "validation_status": score.status,
            "validation_reason": score.reason,
            "answer": final_answer,
            "messages": [AIMessage(content=final_answer)] # 确认无误，写入记忆
        }
        
    except Exception as e:
        logger.warning(f"⚠️ [VALIDATION] 校验解析失败: {e}，默认放行")
        return {
            "validation_status": "error",
            "validation_reason": "JSON Parse Error",
            "messages": [AIMessage(content=answer)]
        }