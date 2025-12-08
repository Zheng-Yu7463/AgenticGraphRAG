from langchain_core.prompts import ChatPromptTemplate

# 实体抽取 Prompt
entity_extraction_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个专业的信息提取助手。请从文本中提取与查询相关的专有名词（实体），并返回 JSON 格式。

    【提取要求】
    1. 提取目标：人名、公司名、产品名、地名、特定技术名词等。
    2. 保持原词：不要翻译或修改实体名称。
    3. 如果没有明显实体，返回空列表。

    【格式要求】
    请严格遵守以下 JSON 输出格式：
    {format_instructions}
    """),
    ("user", """
    查询语句：{query}
    参考文本：{text}
    """)
])