# app/prompts/validation.py
from langchain_core.prompts import ChatPromptTemplate

validation_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个严格的评分员。请评估 AI 的回答。

请输出 JSON 格式，字段说明：
- is_valid: bool (是否完全通过)
- reason: str (理由)
- action: str (必须是以下三个字符串之一)
    - "pass": 回答完美，无需修改，哪怕检索不成功，生成的答案根据你的知识判断正确即可。
    - "retry_retrieval": 在回答有问题的前提下，问题大概率来源于检索失误，需要重新检索。
    - "retry_generation": 在回答有问题的前提下，上下文里有答案，但 AI 没写好（有幻觉、逻辑错误、格式不对），需要重新生成。

请严格遵守以下格式指令：
{format_instructions}
"""),
    ("user", """
【上下文】
{context}

【用户问题】
{question}

【AI 回答】
{answer}
""")
])