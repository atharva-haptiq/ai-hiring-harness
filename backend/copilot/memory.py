"""
memory.py — In-process chat history store for the AI Hiring Copilot.

Keeps the last N messages per session so the orchestrator can pass
conversation context to the LLM on subsequent turns.

Usage:
    from copilot.memory import add_message, get_history

    add_message("session-abc", "user", "Rank candidates for job 1")
    add_message("session-abc", "assistant", "Here are the results...")

    history = get_history("session-abc")
    # [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]

Note:
    Storage is in-process only. History is lost when the server restarts.
    For persistence across restarts, replace _store with a database-backed
    implementation.
"""

from collections import deque
from typing import TypedDict

# Maximum number of messages retained per session.
_MAX_HISTORY = 5

# { session_id: deque([{"role": ..., "content": ...}, ...]) }
_store: dict[str, deque] = {}


class Message(TypedDict):
    role: str     # "user" or "assistant"
    content: str  # Message text


def add_message(session_id: str, role: str, content: str) -> None:
    """
    Append a message to the history for the given session.

    If the session does not exist it is created automatically.
    Once the history reaches _MAX_HISTORY messages, the oldest entry
    is dropped to make room for the new one (sliding window).

    Args:
        session_id -- Unique identifier for the conversation session.
        role       -- Speaker: "user" or "assistant".
        content    -- Message text.
    """
    if session_id not in _store:
        _store[session_id] = deque(maxlen=_MAX_HISTORY)
    _store[session_id].append(Message(role=role, content=content))


def get_history(session_id: str) -> list[Message]:
    """
    Return the stored message history for the given session.

    Args:
        session_id -- Unique identifier for the conversation session.

    Returns:
        List of messages in chronological order (oldest first).
        Returns an empty list if the session has no history yet.
    """
    return list(_store.get(session_id, []))


def clear_history(session_id: str) -> None:
    """
    Remove all stored messages for the given session.

    Args:
        session_id -- Unique identifier for the conversation session.
    """
    _store.pop(session_id, None)
