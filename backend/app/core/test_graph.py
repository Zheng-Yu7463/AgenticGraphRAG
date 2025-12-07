import asyncio
from langchain_core.messages import HumanMessage
from app.core.graph import app_graph

async def main():
    # 模拟一个用户的 Session ID
    config = {"configurable": {"thread_id": "user_999"}}
    
    print("--- 🟢 第一轮对话 ---")
    question1 = "马斯克的太空公司叫什么？"
    
    # 注意：LangGraph 的输入通常需要包含 messages
    inputs1 = {
        "query": question1,
        "messages": [HumanMessage(content=question1)]
    }
    
    async for event in app_graph.astream(inputs1, config=config):
        for key, value in event.items():
            print(f"Update from node: {key}")
            # print(value) # 调试用
            
    # 获取最终状态
    final_state1 = await app_graph.aget_state(config)
    print(f"\n🤖 AI回答: {final_state1.values['answer']}")
    
    print("\n\n--- 🔵 第二轮对话 (测试记忆) ---")
    question2 = "它最著名的火箭是什么？" 
    # 注意：这里我们指代了“它”，如果记忆不生效，AI会不知道“它”是谁
    
    inputs2 = {
        "query": question2,
        "messages": [HumanMessage(content=question2)]
    }
    
    async for event in app_graph.astream(inputs2, config=config):
        for key, value in event.items():
            print(f"Update from node: {key}")

    final_state2 = await app_graph.aget_state(config)
    print(f"\n🤖 AI回答: {final_state2.values['answer']}")

if __name__ == "__main__":
    asyncio.run(main())