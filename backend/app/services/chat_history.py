import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

# 持久化存储位置（单用户场景）
_HISTORY_FILE = Path(__file__).resolve().parent.parent / "logs" / "chat_history.json"
_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_store() -> Dict[str, Dict[str, Any]]:
    """
    兼容旧结构：如果值是 list 则转换为带 metadata 的 dict
    """
    if not _HISTORY_FILE.exists():
        return {}
    try:
        raw = json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

    store: Dict[str, Dict[str, Any]] = {}
    for thread_id, value in raw.items():
        if isinstance(value, list):
            store[thread_id] = {
                "title": thread_id,
                "messages": value,
                "updated_at": datetime.utcnow().isoformat()
            }
        elif isinstance(value, dict):
            store[thread_id] = {
                "title": value.get("title", thread_id),
                "messages": value.get("messages", []),
                "updated_at": value.get("updated_at", datetime.utcnow().isoformat())
            }
    return store


def _save_store(store: Dict[str, Dict[str, Any]]) -> None:
    _HISTORY_FILE.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_title(first_user_msg: str, fallback: str) -> str:
    text = (first_user_msg or "").strip()
    if not text:
        return fallback
    return text[:30]


def get_serializable_history(thread_id: str) -> List[Dict[str, str]]:
    """返回给前端的可序列化历史"""
    store = _load_store()
    if thread_id not in store:
        return []
    return store[thread_id].get("messages", [])


def get_langchain_history(thread_id: str) -> List[BaseMessage]:
    """转成 LangChain 消息对象用于上下文"""
    history = get_serializable_history(thread_id)
    lc_messages: List[BaseMessage] = []
    for item in history:
        role = item.get("role")
        content = item.get("content", "")
        if role == "assistant":
            lc_messages.append(AIMessage(content=content))
        else:
            lc_messages.append(HumanMessage(content=content))
    return lc_messages


def append_history(thread_id: str, messages: List[Dict[str, str]]) -> None:
    """
    追加一轮对话，并在首次创建时生成标题
    messages: [{"role": "user"|"assistant", "content": "..."}]
    """
    store = _load_store()
    now = datetime.utcnow().isoformat()
    entry = store.get(thread_id)

    if not entry:
        user_msg = next((m["content"] for m in messages if m.get("role") == "user"), "")
        entry = {
            "title": _make_title(user_msg, thread_id),
            "messages": [],
            "updated_at": now
        }

    entry["messages"].extend(messages)
    entry["updated_at"] = now
    store[thread_id] = entry
    _save_store(store)


def thread_exists(thread_id: str) -> bool:
    store = _load_store()
    return thread_id in store


def generate_thread_id() -> str:
    ts = int(time.time() * 1000)
    rand = uuid4().hex[:6]
    return f"thread-{ts}-{rand}"


def list_threads() -> List[Dict[str, Any]]:
    """
    返回所有线程的概要：thread_id、title、updated_at、message_count
    """
    store = _load_store()
    items = []
    for tid, entry in store.items():
        msgs = entry.get("messages", [])
        items.append({
            "thread_id": tid,
            "title": entry.get("title", tid),
            "updated_at": entry.get("updated_at", ""),
            "message_count": len(msgs)
        })
    # 按更新时间倒序
    return sorted(items, key=lambda x: x.get("updated_at", ""), reverse=True)


def delete_thread(thread_id: str) -> bool:
    """
    删除指定线程，返回是否删除成功
    """
    store = _load_store()
    if thread_id not in store:
        return False
    del store[thread_id]
    _save_store(store)
    return True
