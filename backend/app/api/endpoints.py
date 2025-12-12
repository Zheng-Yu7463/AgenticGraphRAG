import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from app.api.schemas import ChatRequest, ChatResponse
from app.core.graph import app as agent_app # 导入你编排好的图
from app.core.logger import logger

router = APIRouter()

async def event_generator(query: str, thread_id: str):
    """
    生成 SSE 事件流
    格式: data: {...} \n\n
    """
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {
        "query": query,
        "messages": [HumanMessage(content=query)]
    }

    try:
        # 使用 astream 监听图的执行过程
        async for event in agent_app.astream(inputs, config=config):
            
            # 1. 监听节点完成事件
            for node_name, state_update in event.items():
                
                # 构造要发给前端的数据包
                payload = {"type": "update", "node": node_name}
                
                # 提取不同节点的关键信息
                if node_name == "retrieve":
                    payload["status"] = "retrieval_done"
                    payload["entities"] = state_update.get("entities", [])
                
                elif node_name == "generate":
                    payload["status"] = "generation_done"
                    # 注意：此时 answer 还没校验，可以选择不发给前端，或者发给前端预览
                
                elif node_name == "validate":
                    payload["status"] = "validation_done"
                    payload["validation_status"] = state_update.get("validation_status")
                    payload["reason"] = state_update.get("validation_reason")
                    # 校验完成后的 Answer 才是最终 Answer
                    payload["final_answer"] = state_update.get("answer")

                # 发送 SSE 数据帧
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        # 2. 发送结束信号
        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.error(f"流式生成出错: {e}")
        err_payload = {"type": "error", "message": str(e)}
        yield f"data: {json.dumps(err_payload, ensure_ascii=False)}\n\n"

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    流式对话接口 (Server-Sent Events)
    前端可以通过 EventSource 接收实时状态更新
    """
    logger.info(f"收到请求: {request.query} (ID: {request.thread_id})")
    
    return StreamingResponse(
        event_generator(request.query, request.thread_id),
        media_type="text/event-stream"
    )

@router.post("/chat", response_model=ChatResponse)
async def chat_sync(request: ChatRequest):
    """
    同步对话接口 (等待所有步骤完成后一次性返回)
    """
    logger.info(f"收到同步请求: {request.query}")
    config = {"configurable": {"thread_id": request.thread_id}}
    
    try:
        final_state = await agent_app.ainvoke(
            {"query": request.query, "messages": [HumanMessage(content=request.query)]},
            config=config
        )
        
        return ChatResponse(
            answer=final_state["answer"],
            sources=final_state.get("entities", []),
            graph_data=final_state.get("graph_context", ""),
            validation_status=final_state.get("validation_status", "unknown")
        )
    except Exception as e:
        logger.error(f"执行失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))