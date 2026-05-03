import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional


STORE_PATH = os.path.join("data", "context_store.json")


def _empty_store() -> Dict[str, Dict[str, Any]]:
    return {
        "category": {},
        "merchant": {},
        "customer": {},
        "trigger": {},
        "sent_suppression_keys": {},
        "conversations": {}
    }


def load_store() -> Dict[str, Dict[str, Any]]:
    if not os.path.exists(STORE_PATH):
        return _empty_store()

    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        store = _empty_store()
        store.update(data)
        return store

    except json.JSONDecodeError:
        return _empty_store()


def save_store(store: Dict[str, Dict[str, Any]]) -> None:
    os.makedirs("data", exist_ok=True)

    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def put_context(scope: str, context_id: str, version: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    store = load_store()

    existing = store[scope].get(context_id)

    if existing and existing["version"] > version:
        return {
            "accepted": False,
            "reason": "stale_version",
            "current_version": existing["version"]
        }

    if existing and existing["version"] == version:
        return {
            "accepted": True,
            "ack_id": f"ack_{scope}_{context_id}_{version}",
            "stored_at": existing["stored_at"]
        }

    store[scope][context_id] = {
        "version": version,
        "payload": payload,
        "stored_at": now_utc()
    }

    save_store(store)

    return {
        "accepted": True,
        "ack_id": f"ack_{scope}_{context_id}_{version}",
        "stored_at": store[scope][context_id]["stored_at"]
    }


def get_context(scope: str, context_id: str) -> Optional[Dict[str, Any]]:
    store = load_store()
    item = store.get(scope, {}).get(context_id)

    if not item:
        return None

    return item["payload"]


def count_contexts() -> Dict[str, int]:
    store = load_store()

    return {
        "category": len(store["category"]),
        "merchant": len(store["merchant"]),
        "customer": len(store["customer"]),
        "trigger": len(store["trigger"])
    }

#supressed trick

def is_suppressed(suppression_key: str) -> bool:
    store = load_store()
    return suppression_key in store.get("sent_suppression_keys", {})


def mark_suppressed(suppression_key: str) -> None:
    store = load_store()
    store.setdefault("sent_suppression_keys", {})
    store["sent_suppression_keys"][suppression_key] = now_utc()
    save_store(store)


#convesration store

def save_conversation(conversation_id: str, data: dict):
    store = load_store()
    store.setdefault("conversations", {})
    store["conversations"][conversation_id] = data
    save_store(store)


def get_conversation(conversation_id: str):
    store = load_store()
    return store.get("conversations", {}).get(conversation_id)