# app/services/llm_factory.py
from typing import Literal
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from app.core.config import settings
from app.core.logger import logger

class LLMFactory:
    """
    LLM 工厂类
    用于根据不同的任务需求（模式），生产配置不同的 LangChain ChatModel 实例
    支持 create_agent 高层 API 和低层 ChatOpenAI 使用
    """
    def __init__(self):
        self.fast_model = self.init_llm(mode="fast")
        self.smart_model = self.init_llm(mode="smart")
        self.strict_model = self.init_llm(mode="strict")

    def init_llm(self, mode: Literal["smart", "fast", "strict"] = "smart") -> BaseChatModel:
        """
        获取 LLM 实例的核心方法
        
        Args:
            mode:
                - "smart": 高智能模式 (qwen-max), 适合生成回答、推理、create_agent
                - "fast":  极速模式 (qwen-plus), 适合实体抽取、简单分类
                - "strict": 严谨模式 (qwen-plus, Temp=0), 适合 Validator 校验、JSON 格式化
        
        Returns:
            BaseChatModel 实例 (可直接用于 create_agent 的 model 参数)
            
        Examples:
            >>> # 直接用
            >>> llm = LLMFactory.get_llm(mode="fast")
            >>> response = llm.invoke([{"role": "user", "content": "..."}])
            
            >>> # 用于 create_agent
            >>> agent = create_agent(model=llm, tools=[...])
        """
        
        # 1. API Key 检查
        if not settings.LLM_API_KEY:
            logger.error("❌ 未找到 LLM_API_KEY，请检查环境变量或 .env 配置")
            raise ValueError("LLM_API_KEY is missing")

        try:
            # 2. 根据模式配置参数
            config_map = {
                "smart": {
                    "model": getattr(settings, "MODEL_SMART", "qwen-max"),
                    "temperature": 0.7,
                    "max_tokens": 20000
                },
                "fast": {
                    "model": getattr(settings, "MODEL_FAST", "qwen-plus"),
                    "temperature": 0.0,
                    "max_tokens": 20000
                },
                "strict": {
                    "model": getattr(settings, "MODEL_STRICT", "qwen-plus"),
                    "temperature": 0.0,
                    "max_tokens": 20000
                }
            }

            if mode not in config_map:
                error_msg = f"❌ 未知的 LLM 模式: {mode}，支持: smart/fast/strict"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # 3. 创建 LLM 实例
            config = config_map[mode]
            llm = ChatOpenAI(
                base_url=settings.LLM_BASE_URL,
                api_key=settings.LLM_API_KEY,
                model=config["model"],
                temperature=config["temperature"],
                max_tokens=config["max_tokens"]
            )

            logger.success(
                f"✅ LLM 已初始化 | Mode: {mode} | Model: {config['model']} | Temp: {config['temperature']}"
            )
            return llm

        except Exception as e:
            logger.error(f"❌ LLM 初始化失败 (Mode: {mode}): {str(e)}")
            raise
   
    
    @staticmethod
    def get_llm(
        mode: Literal["smart", "fast", "strict"] = "smart"
    ) -> BaseChatModel:
        if mode == "fast":
            return llm_factory.fast_model
        elif mode == "smart":
            return llm_factory.smart_model
        elif mode == "strict":
            return llm_factory.strict_model
        else:
            error_msg = f"❌ 未知的 LLM 模式: {mode}，支持: smart/fast/strict"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
llm_factory = LLMFactory()

if __name__ == "__main__":
    from langchain_core.messages import HumanMessage
    from langchain.agents import create_agent
    from langchain.tools import tool

    logger.info("🤖 开始测试 LLM Factory...")

    try:
        # 1. 测试 Fast 模式
        logger.info("1️⃣ 测试 FAST 模式...")
        fast_llm = LLMFactory.get_llm(mode="fast")
        res_fast = fast_llm.invoke([HumanMessage(content="1+1等于几？只回答数字。")])
        logger.success(f"✅ Fast Mode 响应: {res_fast.content.split()[0]}")

        # 2. 测试 Smart 模式
        logger.info("2️⃣ 测试 SMART 模式...")
        smart_llm = LLMFactory.get_llm(mode="smart")
        if smart_llm:
            logger.success("✅ Smart Mode 初始化成功")

        # 3. 测试 Strict 模式
        logger.info("3️⃣ 测试 STRICT 模式...")
        strict_llm = LLMFactory.get_llm(mode="strict")
        if strict_llm:
            logger.success("✅ Strict Mode 初始化成功")

        # 4. 测试与 create_agent 集成
        logger.info("4️⃣ 测试与 create_agent 集成...")
        
        @tool
        def demo_tool(query: str) -> str:
            """演示工具"""
            return f"Demo result for: {query}"
        
        agent = create_agent(
            model=LLMFactory.get_llm(mode="smart"),
            tools=[demo_tool],
            system_prompt="你是一个有帮助的助手"
        )
        logger.success("✅ Agent 创建成功")

        logger.success("🎉 所有测试通过！")

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")