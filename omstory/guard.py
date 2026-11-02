"""
guard.py — 안전 필터 + AI 결과 검사

1) 아이 입력 안전 필터: 무섭거나 거친 말이 들어오면 이야기를 다정한 쪽으로 돌린다 (지침 6장 Never).
2) AI 결과 검사: 지침 가이드(prompts/wacky_tutor_system.md)를 지켰는지 코드로 확인한다.
   - 반드시 지킬 것(issues): 대사 길이, 다음 질문·고를 거리, 한국어 섞임, 지적하는 말, 위험한 말
   - 참고(warnings): 교재 밖 단어 비율, 주요 표현 사용 — 이야기를 막지 않고 기록만 한다 (주요 표현은 시험이 아니라 재료)
   issues가 있으면 story.py가 문제 목록을 붙여 한 번 더 만들게 하고, 그래도 안 되면 편집자 문장으로 대체한다.
"""
from __future__ import annotations

import re

from . import config
from .analysis import has_korean, off_unit_rate, story_pattern_hit
from .rag import UnitContext

# PoC용 최소 목록. 실제 서비스에서는 아동용 금칙어 사전 + 분류 모델을 함께 쓴다.
UNSAFE_EN = ["kill", "killed", "die", "dies", "dead", "blood", "gun", "guns", "knife", "bomb", "hate", "stupid",
             "idiot", "ugly", "shut up", "hurt", "punch", "kick you", "monster eats"]
UNSAFE_KO = ["죽", "피가", "총", "칼", "폭탄", "바보", "멍청", "싫어", "때려", "꺼져", "미워"]
CRITICISM = [r"\bwrong\b", r"\bmistake\b", r"\bthat'?s not right\b", r"^\s*no[,.!]", r"\bbad answer\b"]
MAX_OFF_UNIT_RATE = 0.35


def _has_any(text: str, words: list[str]) -> list[str]:
    t = text.lower()
    return [w for w in words if re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", t)]


def child_unsafe(text: str) -> list[str]:
    """아이 말에서 걸린 위험 단어 목록 (없으면 빈 목록)."""
    found = _has_any(text, UNSAFE_EN)
    found += [w for w in UNSAFE_KO if w in text]
    return found


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])[\"”']?\s+", text.strip()) if s]


def _unquoted(sentence: str) -> str:
    """아이 말을 인용한 부분("...")은 길이 검사에서 뺀다 (아이가 많이 말한 건 좋은 일)."""
    return re.sub(r"[\"“][^\"”]*[\"”]?", " ", sentence)


def check_output(ctx: UnitContext, page_idx: int, child_text: str, d: dict) -> tuple[list[str], list[str]]:
    """(issues, warnings). issues가 비면 통과."""
    issues: list[str] = []
    warnings: list[str] = []
    reply = str(d.get("reply_en", "")).strip()
    q = str(d.get("next_question_en", "") or "").strip()
    choices = [c for c in d.get("choices", []) or [] if isinstance(c, str)]
    korean_mode = bool(d.get("korean_to_english")) or bool(d.get("safe_redirect"))
    last = page_idx + 1 >= config.MAX_PAGES

    if not reply:
        return ["reply_en is empty."], warnings
    english = " ".join([reply, q, " ".join(choices), str(d.get("page_en", "")), str(d.get("korean_to_english") or "")])
    if has_korean(english):
        issues.append("English fields contain Korean. Korean goes only in the *_ko fields.")
    if _has_any(english, UNSAFE_EN):
        issues.append("Unsafe words. Make the story kind and safe (Rule 6).")
    if any(re.search(p, reply, re.I) for p in CRITICISM):
        issues.append("Do not tell the child they are wrong. Accept the idea and keep the story going.")
    ss = sentences(reply)
    if len(ss) > config.WACKY_MAX_SENTENCES:
        issues.append(f"reply_en has {len(ss)} sentences. Use 1-3 short sentences.")
    long_s = [s for s in ss if len(_unquoted(s).split()) > config.WACKY_MAX_WORDS]
    if long_s:
        issues.append(f"These sentences are too long ({config.WACKY_MAX_WORDS} words max): {long_s}")
    if not korean_mode:
        if len(str(d.get("page_en", "")).split()) > 18:
            issues.append("page_en is too long (16 words max).")
        if not last:
            last_q = sentences(q)[-1] if q else ""
            if not q.endswith("?") or len(last_q.split()) > 12 or len(q.split()) > 16:
                issues.append("next_question_en must be one short question (max 10 words, a short lead-in is OK) ending with '?'.")
            if not (1 <= len(choices) <= 3) or any(len(c.split()) > 7 for c in choices):
                issues.append("Give two short choices (max 6 words each) so the child is not stuck.")
        rate = off_unit_rate(ctx, " ".join([reply, q]), " ".join([child_text] + choices))
        if rate > MAX_OFF_UNIT_RATE:
            warnings.append(f"교재 밖 단어 비율 {rate:.0%}")
        if not story_pattern_hit(ctx, reply + " " + str(d.get("page_en", ""))):
            warnings.append("이번 페이지 대사에 주요 표현 없음 (참고)")
    return issues, warnings
