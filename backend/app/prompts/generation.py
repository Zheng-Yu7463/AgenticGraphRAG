from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 生成回答的 Prompt
rag_generation_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个专业的 AI 助手。请根据提供的上下文回答用户的问题。

【上下文信息】
{context}

【回答要求】
1. 在有上下文信息的情况下，尽量基于上下文，不要编造信息，不要在回答中体现你有上下文信息，可以补充你的相关知识。
2. 如果上下文包含知识图谱关系（如 A -> B），请在不要回答中明确体现，尽量自然的融入回答中。
3. 如果上下文不足以回答问题，可以根据你的知识来回答，但是不要编造信息。
"""),
    # 自动插入历史对话
    MessagesPlaceholder(variable_name="messages"),
    ("user", "{question}")
])