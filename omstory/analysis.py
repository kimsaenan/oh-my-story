"""
analysis.py — 아이 발화 분석과 지표 계산 (LLM 없이 규칙으로 판단 → KPI를 객관적으로 측정)
"""
from __future__ import annotations

import re

from .rag import UnitContext, tokens

HANGUL_RE = re.compile(r"[가-힣]")


def has_korean(text: str) -> bool:
    return bool(HANGUL_RE.search(text))


def with_article(x: str) -> str:
    """idea 앞에 알맞은 관사 붙이기 (이름·복수·이미 관사 있음은 그대로)."""
    x = x.strip()
    if not x:
        return x
    if x[0].isupper() or re.match(r"^(a|an|the|my|your|some|two|three)\b", x, re.I) or x.lower().endswith("s"):
        return x
    return ("an " if x[0].lower() in "aeiou" else "a ") + x


def check_pattern(turn: dict, text: str) -> bool:
    return bool(re.search(turn["check"], text.strip(), re.I))


def extract_idea(turn: dict, text: str) -> str:
    """아이가 빈칸에 넣은 말(상상한 것)을 뽑는다."""
    if not turn.get("pick"):
        return ""
    m = re.search(turn["pick"], text.strip(), re.I)
    if not m:
        return ""
    return re.sub(r"[.!?]+$", "", m.group(1)).strip()


def make_sentence(turn: dict, idea: str) -> str:
    """패턴 문장으로 다시 만들어 주기(recast)."""
    return turn["make"].replace("{a}", with_article(idea)).replace("{w}", idea)


def story_pattern_hit(ctx: UnitContext, story: str) -> bool:
    """생성된 이야기에 단원 핵심 패턴(문장 틀)이 들어 있는가 — PRD KPI 'RAG 정밀도'."""
    s = " ".join(tokens(story))
    # "i like ~ best" 처럼 ~ 자리에는 1~4단어가 들어갈 수 있다
    pats = [r"(?:\s+\S+){1,4}\s+".join(re.escape(part.strip()) for part in stem.split("~")) for stem in ctx.pattern_stems]
    return any(re.search(rf"(?<![a-z']){p}(?![a-z'])", s) for p in pats)


def off_unit_words(ctx: UnitContext, story: str, child_text: str = "") -> list[str]:
    """이야기 속 단어 중 교재 범위(현재+배운 단원+기본 단어)와 아이가 직접 말한 단어 밖의 단어."""
    allowed = ctx.allowed_words() | set(tokens(child_text))
    out = []
    for w in tokens(story):
        base = re.sub(r"('s|s|es)$", "", w)
        if w in allowed or base in allowed or len(w) <= 1:
            continue
        if w not in out:
            out.append(w)
    return out


def off_unit_rate(ctx: UnitContext, story: str, child_text: str = "") -> float:
    total = len(tokens(story)) or 1
    return len(off_unit_words(ctx, story, child_text)) / total


# ---------------- 이야기 페이지용 (주요 표현 = 재료, 채점 아님) ----------------
LEAD_RE = re.compile(r"^\s*(?:i\s+(?:enjoy|like|love|want)\s+|it'?s\s+|it\s+is\s+|they'?re\s+|there'?s\s+|there\s+is\s+|"
                     r"i'?m\s+|we\s+|let'?s\s+(?:go\s+)?)?(?:a\s+|an\s+|the\s+|my\s+)?", re.I)


def find_idea(ctx: UnitContext, text: str) -> str:
    """아이 말에서 이야기에 넣을 아이디어를 뽑는다: 교재 어휘가 있으면 그 단어, 없으면 앞뒤 군더더기를 뺀 구절."""
    t = text.strip()
    low = t.lower()
    for w in sorted(ctx.unit["vocabulary"], key=len, reverse=True):
        if w.lower() in low:
            return w
    core = LEAD_RE.sub("", t)
    core = re.sub(r"\s+best\b", "", core, flags=re.I)
    core = re.sub(r"[.!?\"]+$", "", core).strip()
    words = core.split()
    return " ".join(words[:5]) if words else ""


def expression_used(ctx: UnitContext, text: str) -> bool:
    """아이가 오늘의 주요 표현(문장 틀)을 썼는가 — 별 반짝임용 (이야기는 안 써도 계속 간다)."""
    return story_pattern_hit(ctx, text)


def english_sentences(text: str) -> list[str]:
    """아이가 영어로 말한 문장들 (발화량 집계: 영어 단어 2개 이상인 문장)."""
    if has_korean(text):
        return []
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p.strip()]
    return [p for p in parts if len(re.findall(r"[A-Za-z]+", p)) >= 2]
