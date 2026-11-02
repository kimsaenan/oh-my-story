"""
korean.py — 한국어로 말해도 OK: 아이 말을 영어 문장으로 바꾸기

- AI가 연결돼 있으면 AI(지침 4장)가 아이 말 그대로를 영어 문장으로 바꾼다 (교재에 없는 상상도 가능).
- AI가 없을 때는 Word List 한글 뜻으로 만든 사전(kb units.json의 ko_keywords)으로 교재 단어 범위 안에서만 바꾼다.
  예) "스키 타는 거 좋아" → "I enjoy skiing."  /  "서핑이 제일 좋아" → "I like surfing best."
"""
from __future__ import annotations

from .rag import UnitContext

BEST_WORDS = ("제일", "가장", "최고")


def convert(ctx: UnitContext, text: str) -> str | None:
    """교재 단어로 바꿀 수 있으면 영어 문장, 없으면 None."""
    kw = ctx.unit.get("ko_keywords", {})
    hit = next((en for ko, en in sorted(kw.items(), key=lambda x: -len(x[0])) if ko in text), None)
    if not hit:
        return None
    if any(b in text for b in BEST_WORDS):
        return f"I like {hit} best."
    return f"I enjoy {hit}."
