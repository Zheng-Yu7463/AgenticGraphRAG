import asyncio
from langchain_core.messages import HumanMessage
from app.core.graph import app

# ✅ 1. 必须导入初始化函数
from app.services.hybrid_search import init_hybrid_search

async def test_full_flow():
    # ✅ 2. 在测试开始前，手动初始化服务
    # 因为这里没有 FastAPI 的 lifespan 帮你自动执行
    print("⚙️ [系统启动] 正在初始化 Hybrid Search Service...")
    init_hybrid_search()
    print("✅ [系统启动] 初始化完成\n")

    # 模拟用户 session
    config = {"configurable": {"thread_id": "test_user_007"}}
    
    # 📝 测试 1: 正常问题
    query = "马斯克的太空公司是什么"
    print(f"{'='*50}\n🧠 用户提问: {query}\n{'='*50}")
    
    inputs = {
        "query": query,
        "messages": [HumanMessage(content=query)]
    }
    
    # 流式运行，查看每个步骤
    async for event in app.astream(inputs, config=config):
        for node, values in event.items():
            print(f"✅ 节点完成: [{node}]")
            
            # 👇 更新打印逻辑，适配新的 Router 逻辑
            if node == "validate":
                status = values.get('validation_status') # 可能是 pass, retry_retrieval 等
                reason = values.get('validation_reason')
                retry = values.get('retry_count', 0)
                
                print(f"   👉 校验动作: {status}")
                print(f"   👉 校验理由: {reason}")
                print(f"   🔄 重试次数: {retry}")
    
    # 获取最终状态
    state = await app.aget_state(config)
    # 注意：有可能最后是强制结束的，所以要在取值前判断一下
    final_ans = state.values.get('answer', '无回答')
    print(f"\n🤖 最终回答: {final_ans}")
    
    # 📝 测试 2: 追问 (测试记忆)
    query2 = "它有什么著名的火箭？"
    print(f"\n\n{'='*50}\n🧠 用户追问: {query2}\n{'='*50}")
    
    inputs2 = {
        "query": query2,
        "messages": [HumanMessage(content=query2)]
    }
    
    async for event in app.astream(inputs2, config=config):
        for node, values in event.items():
            # 简略输出节点名，证明流在动
            print(f"✅ 节点完成: [{node}]")
            if node == "validate":
                 print(f"   👉 状态: {values.get('validation_status')}")
        
    state2 = await app.aget_state(config)
    print(f"\n🤖 最终回答: {state2.values.get('answer')}")

if __name__ == "__main__":
    asyncio.run(test_full_flow())