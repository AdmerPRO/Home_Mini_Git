import json
import time
import uuid
from pathlib import Path

USERNAME_PATTERN = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
)


def _messages_file(base_path: Path) -> Path:
    return Path(base_path) / "user_projects" / "messages_index.json"


def _load_messages(base_path: Path) -> dict:
    messages_file = _messages_file(base_path)
    if not messages_file.exists():
        return {"mailboxes": {}}
    with open(messages_file, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    mailboxes = data.get("mailboxes")
    return {"mailboxes": mailboxes if isinstance(mailboxes, dict) else {}}


def _save_messages(base_path: Path, data: dict) -> None:
    messages_file = _messages_file(base_path)
    messages_file.parent.mkdir(parents=True, exist_ok=True)
    with open(messages_file, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4, ensure_ascii=False)


def _require_safe_username(username: str) -> str:
    normalized = str(username).strip()
    if not normalized or any(char not in USERNAME_PATTERN for char in normalized):
        raise ValueError("Invalid username")
    return normalized


def send_message(
    base_path: Path,
    sender: str,
    recipient: str,
    subject: str,
    content: str,
) -> dict:
    sender_name = _require_safe_username(sender)
    recipient_name = _require_safe_username(recipient)
    payload = {
        "id": uuid.uuid4().hex,
        "sender": sender_name,
        "recipient": recipient_name,
        "subject": str(subject).strip()[:120] or "No subject",
        "content": str(content).strip()[:5000],
        "created_at": int(time.time() * 1000),
        "read": False,
    }
    if not payload["content"]:
        raise ValueError("Message content is required")

    data = _load_messages(base_path)
    mailbox = data["mailboxes"].setdefault(recipient_name, [])
    mailbox.append(payload)
    mailbox.sort(key=lambda item: item["created_at"], reverse=True)
    _save_messages(base_path, data)
    return payload


def get_inbox(base_path: Path, username: str) -> list[dict]:
    username = _require_safe_username(username)
    data = _load_messages(base_path)
    mailbox = data["mailboxes"].get(username, [])
    return sorted(mailbox, key=lambda item: item["created_at"], reverse=True)


def mark_message_read(base_path: Path, username: str, message_id: str) -> bool:
    username = _require_safe_username(username)
    data = _load_messages(base_path)
    mailbox = data["mailboxes"].get(username, [])
    for message in mailbox:
        if message.get("id") == message_id:
            message["read"] = True
            _save_messages(base_path, data)
            return True
    return False
