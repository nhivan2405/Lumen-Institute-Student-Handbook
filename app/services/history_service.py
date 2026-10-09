"""Dịch vụ history che chi tiết SQLite khỏi route/API."""
import json
from app.db import database

def new_conversation() -> dict:
    return database.create_conversation()

def save_turn(conversation_id: str, question: str, answer: str, citations: list[dict]) -> None:
    database.add_message(conversation_id, "user", question)
    database.add_message(conversation_id, "assistant", answer, json.dumps(citations, ensure_ascii=False))
