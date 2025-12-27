import json
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from app.api.schemas import ChatRequest, ChatResponse, ChatHistoryRequest, ThreadSummary
from app.core.graph import app as agent_app  # 导入你编排好的图
from app.core.logger import logger
from app.services import chat_history

router = APIRouter()

async def event_generator(query: str, thread_id: str):
    """
    生成 SSE 事件流
    格式: data: {...} \n\n
    """
    config = {"configurable": {"thread_id": thread_id}}
    history_messages = chat_history.get_langchain_history(thread_id)
    # 在流式过程中保留最近的回答，校验节点不会返回 answer 字段
    last_answer: str | None = None
    inputs = {
        "query": query,
        "messages": history_messages + [HumanMessage(content=query)]
    }

    try:
        # 首次推送 thread_id 方便前端知晓
        yield f"data: {json.dumps({'type': 'thread', 'thread_id': thread_id}, ensure_ascii=False)}\n\n"

        # 使用 astream 监听图的执行过程
        async for event in agent_app.astream(inputs, config=config):
            
            # 1. 监听节点完成事件
            for node_name, state_update in event.items():

                # 记录最新的回答（生成节点返回 answer，后续校验节点需要用到）
                if isinstance(state_update, dict) and state_update.get("answer"):
                    last_answer = state_update.get("answer")
                
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
                    payload["final_answer"] = last_answer
                    
                    # 持久化当前轮对话
                    if payload["validation_status"] == "pass" and payload["final_answer"]:
                        chat_history.append_history(thread_id, [
                            {"role": "user", "content": query},
                            {"role": "assistant", "content": payload["final_answer"]}
                        ])

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
    thread_id = request.thread_id or chat_history.generate_thread_id()

    # 如果用户指定了 thread_id，但没有历史，则返回错误
    if request.thread_id and not chat_history.thread_exists(request.thread_id):
        logger.error(f"指定的 thread_id 不存在: {request.thread_id}")
        raise HTTPException(status_code=404, detail="thread_id 不存在或历史已清空")

    logger.info(f"收到请求: {request.query} (ID: {thread_id})")
    
    return StreamingResponse(
        event_generator(request.query, thread_id),
        media_type="text/event-stream"
    )

@router.post("/chat", response_model=ChatResponse)
async def chat_sync(request: ChatRequest):
    """
    同步对话接口 (等待所有步骤完成后一次性返回)
    """
    thread_id = request.thread_id or chat_history.generate_thread_id()

    if request.thread_id and not chat_history.thread_exists(request.thread_id):
        logger.error(f"指定的 thread_id 不存在: {request.thread_id}")
        raise HTTPException(status_code=404, detail="thread_id 不存在或历史已清空")

    logger.info(f"收到同步请求: {request.query} (ID: {thread_id})")
    config = {"configurable": {"thread_id": thread_id}}
    history_messages = chat_history.get_langchain_history(thread_id)
    
    try:
        final_state = await agent_app.ainvoke(
            {
                "query": request.query,
                "messages": history_messages + [HumanMessage(content=request.query)]
            },
            config=config
        )
        
        if final_state.get("answer"):
            chat_history.append_history(thread_id, [
                {"role": "user", "content": request.query},
                {"role": "assistant", "content": final_state["answer"]}
            ])
        
        return ChatResponse(
            thread_id=thread_id,
            answer=final_state["answer"],
            sources=final_state.get("entities", []),
            graph_data=final_state.get("graph_context", ""),
            validation_status=final_state.get("validation_status", "unknown")
        )
    except Exception as e:
        logger.error(f"执行失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/history")
async def get_history(body: ChatHistoryRequest):
    """
    获取指定线程的历史消息，避免把 thread_id 放在 URL 里
    """
    if not chat_history.thread_exists(body.thread_id):
        raise HTTPException(status_code=404, detail="thread_id 不存在或历史已清空")
    return {
        "thread_id": body.thread_id,
        "messages": chat_history.get_serializable_history(body.thread_id)
    }


@router.get("/chat/threads", response_model=List[ThreadSummary])
async def list_threads():
    """
    获取所有对话的概要信息（thread_id、标题、最近更新时间、消息数）
    """
    return chat_history.list_threads()


@router.delete("/chat/history", status_code=204)
async def delete_history(body: ChatHistoryRequest):
    """
    删除指定线程的对话历史
    """
    ok = chat_history.delete_thread(body.thread_id)
    if not ok:
        raise HTTPException(status_code=404, detail="thread_id 不存在或历史已清空")
