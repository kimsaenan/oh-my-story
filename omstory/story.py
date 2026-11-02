"""
story.py — Oh! My Story 핵심: 아이와 Wacky가 한 페이지씩 동화책을 쓴다

한 페이지 흐름
  0. 안전 필터: 위험한 말이면 다정한 이야기로 돌리고 같은 질문을 다시 한다.
  1. 한국어면: 아이 말을 영어 문장으로 바꿔 보여 주고(따라 말하기), 이야기는 아이가 영어로 말한 뒤 이어진다.
  2. AI 생성: 지침 가이드(prompts/wacky_tutor_system.md) + RAG 교재 내용 + 이야기 씨앗·페이지 정보로
     캐릭터 반응, 동화책 문장, 다음 질문과 고를 거리를 만든다.
  3. 검사 → 재생성: 지침을 어기면 문제 목록을 붙여 1번 더 만든다.
  4. 대체: 그래도 안 되거나 AI를 쓸 수 없으면 편집자 문장(씨앗 대사 + 이어 쓰기 템플릿)으로 이어간다.

교재 주요 표현은 채점하지 않는다. 아이가 쓰면 ⭐ 표시만 하고, 안 써도 이야기는 계속 간다.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from . import config, guard, korean
from .analysis import expression_used, find_idea, has_korean
from .prompting import build_messages, page_plan
from .rag import UnitContext
from .scenes import FANTASY_SCENES, detect_scene

SPEAKERS = {"wacky", "jack", "amy", "tom", "mom"}
MAX_ATTEMPTS = 2  # 첫 생성 + 검사 후 1회 재생성
GO_ACTIVITIES = {"swimming", "surfing", "sunbathing", "diving", "snorkeling", "skiing", "snowboarding", "skating",
                 "shopping", "fishing", "camping", "hiking", "dancing", "flying"}

# 이어 쓰는 페이지(기본 페이지 이후)의 편집자 대사 — AI가 없을 때 쓴다
FREE_REACTIONS = [("tom", "Wow, I like that! Me, too!", "와, 그거 좋다! 나도!"),
                  ("amy", "That's so fun! What a surprise!", "정말 재밌다! 깜짝 놀랐어!"),
                  ("jack", "Cool! Let's go and see!", "멋지다! 가서 보자!"),
                  ("wacky", "Beep! I enjoy this story!", "삐빅! 이 이야기 정말 좋아!")]
FREE_QUESTIONS = [("What happens next?", "다음엔 무슨 일이 생길까?", ["A big wave comes.", "We find a little cave."]),
                  ("Who comes to play with you?", "누가 같이 놀러 올까?", ["Tom comes.", "A dolphin comes."]),
                  ("How do you feel now?", "지금 기분이 어때?", ["I feel happy.", "I feel excited."]),
                  ("Where do you want to go next?", "다음엔 어디로 가고 싶어?", ["To the sea!", "To the snowy hill!"]),
                  ("What do you like doing best now?", "지금 뭐 하는 게 제일 좋아?", ["I like swimming best.", "I like eating ice cream best."])]
ENDING = ("wacky", "Beep! What a great story! I like your story best!", "삐빅! 정말 멋진 이야기야! 네 이야기가 제일 좋아!")


@dataclass
class PageResult:
    child_text: str
    speaker: str
    reply_en: str
    reply_ko: str
    page_en: str = ""                    # 동화책 페이지 문장 (3인칭)
    page_ko: str = ""
    next_q: str = ""                     # 다음 페이지 질문 (Wacky)
    next_q_ko: str = ""
    choices: list[str] = field(default_factory=list)   # 고를 거리 (T4 힌트)
    idea: str = ""
    korean_to_english: str | None = None  # 한국어 → 영어 전환 문장 (따라 말하기)
    needs_english: bool = False           # 한국어인데 바꿀 수 없음 → 영어로 다시 말하기
    model_sentence: str = ""              # 완전한 문장 예시 (T7, 지적 없이)
    expression_used: bool = False         # 오늘의 주요 표현을 썼는가 (⭐)
    safe_redirect: bool = False
    feedback_ko: str = ""
    stickers: list[str] = field(default_factory=list)
    scene: str = ""
    rules_used: list[str] = field(default_factory=list)
    engine: str = "rule"                  # llm / rule / safety
    attempts: int = 1
    guard_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def ask_again(self) -> bool:
        """이야기를 넘기지 않고 같은 질문을 다시 하는가 (한국어 전환 대기, 안전 필터)."""
        return bool(self.korean_to_english) or self.needs_english or self.safe_redirect


# ---------------- 도우미 ----------------
def gerund_base(phrase: str) -> str:
    head, _, rest = phrase.partition(" ")
    if not head.endswith("ing"):
        return phrase
    b = head[:-3]
    if b.endswith(("mm", "nn", "pp", "tt", "gg")):
        b = b[:-1]
    elif b in ("mak", "hav", "danc", "rid", "driv", "writ", "bak", "skat", "div"):
        b += "e"
    return (b + " " + rest).strip()


def lets_together(idea: str) -> str:
    """교재 Useful Expression 'Let's go surfing together!'을 아이 아이디어에 맞춘다 (T2)."""
    words = idea.strip().split()
    if not words:
        return "Let's play together!"
    if words[0] in GO_ACTIVITIES or (len(words) > 1 and words[1] in GO_ACTIVITIES):
        return f"Let's go {idea.strip()} together!"
    if words[0].endswith("ing"):
        return f"Let's {gerund_base(idea.strip())} together!"
    return "Let's play together!"


def idea_ko(ctx: UnitContext, idea: str) -> str:
    return ctx.unit.get("vocabulary_ko", {}).get(idea.lower(), f"‘{idea}’")


def _fill(tpl: str, ctx: UnitContext, idea: str, child: str) -> str:
    return (tpl.replace("{together}", lets_together(idea)).replace("{W}", idea[:1].upper() + idea[1:])
            .replace("{w}", idea).replace("{ko}", idea_ko(ctx, idea)).replace("{child}", child.strip()))


def _stickers(ctx: UnitContext, *texts: str) -> list[str]:
    joined = " ".join(texts).lower()
    return [w for w in ctx.unit["vocabulary"] if w.lower() in joined][:4]


def _model(ctx: UnitContext, idea: str, used: bool) -> str:
    """주요 표현을 안 썼고 아이디어가 교재 어휘면, 완전한 문장 예시를 만든다 (T7)."""
    frame = ctx.unit.get("frame", "")
    if used or not frame or idea.lower() not in [w.lower() for w in ctx.unit["vocabulary"]]:
        return ""
    return frame.replace("___", idea)


def next_prompt(seed: dict, page_idx: int) -> tuple[str, str, list[str]]:
    """page_idx 페이지를 마친 뒤 Wacky가 할 다음 질문 (편집자 계획 → 이어 쓰기 질문 → 마지막이면 없음)."""
    if page_idx + 1 >= config.MAX_PAGES:
        return "", "", []
    nxt = page_plan(seed, page_idx + 1)
    if nxt:
        return nxt["q"], nxt.get("q_ko", ""), list(nxt.get("choices", []))
    q, ko, ch = FREE_QUESTIONS[(page_idx + 1) % len(FREE_QUESTIONS)]
    return q, ko, list(ch)


# ---------------- 0. 안전 필터 ----------------
def safety_page(ctx: UnitContext, seed: dict, page_idx: int, child_text: str, found: list[str]) -> PageResult:
    plan = page_plan(seed, page_idx)
    return PageResult(child_text, "wacky", "Beep! Let's make a kind and happy story.", "삐빅! 다정하고 즐거운 이야기를 만들어 보자.",
                      choices=list(plan.get("choices", [])) or ["I feel happy.", "We play together."],
                      safe_redirect=True, feedback_ko="우리 다정한 이야기를 만들어 볼까?", engine="safety",
                      rules_used=["T1", "T4"], error=f"안전 필터: {', '.join(found)}")


# ---------------- 4. 편집자 문장 (AI 없이도 같은 흐름) ----------------
def rule_page(ctx: UnitContext, seed: dict, page_idx: int, child_text: str, child_name: str = "Minjun") -> PageResult:
    plan = page_plan(seed, page_idx)
    if has_korean(child_text):  # 한국어 → 교재 단어 범위 안에서 영어로 (T4)
        conv = korean.convert(ctx, child_text)
        if conv:
            return PageResult(child_text, "wacky", "Beep! Great idea! Say it in English.", "삐빅! 멋진 생각이야! 영어로 말해 보자.",
                              korean_to_english=conv, idea=find_idea(ctx, conv), feedback_ko="좋은 생각이야! 영어로 바꿔 봤어.",
                              engine="rule", rules_used=["T1", "T4"])
        return PageResult(child_text, "wacky", "Beep! Can you try it in English?", "삐빅! 영어로 한번 말해 볼까?",
                          choices=list(plan.get("choices", [])) or ["I feel happy.", "It's fun!"], needs_english=True,
                          feedback_ko="이 말은 AI가 연결되면 영어로 바꿔 줄 수 있어요. 지금은 고를 거리로 말해 볼까?",
                          engine="rule", rules_used=["T4"])
    idea = find_idea(ctx, child_text) or "it"
    used = expression_used(ctx, child_text)
    last = page_idx + 1 >= config.MAX_PAGES
    if last:
        speaker, en, ko = ENDING
    elif plan:
        speaker, en, ko = plan["speaker"], _fill(plan["react"], ctx, idea, child_text), _fill(plan["react_ko"], ctx, idea, child_text)
    else:
        speaker, en, ko = FREE_REACTIONS[page_idx % len(FREE_REACTIONS)]
    q, q_ko, choices = next_prompt(seed, page_idx)
    model = _model(ctx, idea, used)
    # 동화책 문장: 아이 말을 그대로 인용 (한두 단어면 완전한 문장 예시로 — T7)
    quote = (model.split(".")[0] if model and len(child_text.split()) <= 2 else child_text.strip()).rstrip(".!?")
    quote = quote[:1].upper() + quote[1:]
    return PageResult(
        child_text, speaker, en, ko,
        page_en=f'{child_name} says, "{quote}!"', page_ko=f'{child_name}이(가) 말해요. "{quote}!"',
        next_q=q, next_q_ko=q_ko, choices=choices, idea=idea, model_sentence=model,
        expression_used=used, feedback_ko="오늘의 표현으로 말했어! ⭐" if used else "멋진 생각이야!",
        stickers=_stickers(ctx, child_text, idea), scene=detect_scene(child_text, idea) or plan.get("scene", ""),
        engine="rule", rules_used=["T1", "T3", "T6"] if used else ["T1", "T4", "T7"],
    )


# ---------------- 1~3. AI 생성 → 검사 → 재생성 ----------------
class GuardFailed(Exception):
    def __init__(self, issues: list[str]):
        super().__init__("; ".join(issues))
        self.issues = issues


def _client():
    from openai import OpenAI  # 지연 import: 키가 없으면 패키지도 필요 없음
    return OpenAI()


def _call(client, messages: list[dict]) -> dict:
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), messages=messages,
        response_format={"type": "json_object"}, temperature=0.8, max_tokens=600, timeout=20,
    )
    return json.loads(resp.choices[0].message.content)


def _to_result(ctx: UnitContext, seed: dict, page_idx: int, child_text: str, d: dict) -> PageResult:
    plan = page_plan(seed, page_idx)
    idea = str(d.get("idea") or find_idea(ctx, child_text))
    speaker = str(d.get("speaker") or plan.get("speaker") or "wacky").lower()
    reply = str(d.get("reply_en", "")).strip()
    stickers = [s for s in d.get("stickers", []) or [] if isinstance(s, str)] or _stickers(ctx, child_text, idea)
    scene = d.get("scene") if d.get("scene") in FANTASY_SCENES else (detect_scene(child_text, idea) or plan.get("scene", ""))
    rules = [r for r in d.get("rules_used", []) or [] if isinstance(r, str) and re.fullmatch(r"T[1-7]", r)]
    k2e = d.get("korean_to_english") or None
    return PageResult(
        child_text=child_text, speaker=speaker if speaker in SPEAKERS else "wacky", reply_en=reply,
        reply_ko=str(d.get("reply_ko", "")), page_en=str(d.get("page_en", "") or ""), page_ko=str(d.get("page_ko", "") or ""),
        next_q=str(d.get("next_question_en", "") or ""), next_q_ko=str(d.get("next_question_ko", "") or ""),
        choices=[c for c in d.get("choices", []) or [] if isinstance(c, str)][:3], idea=idea,
        korean_to_english=str(k2e) if k2e else None, model_sentence=str(d.get("model_sentence", "") or ""),
        expression_used=expression_used(ctx, child_text), safe_redirect=bool(d.get("safe_redirect", False)),
        feedback_ko=str(d.get("feedback_ko", "")), stickers=stickers[:4], scene=scene or "", rules_used=rules, engine="llm",
    )


def llm_page(ctx: UnitContext, seed: dict, page_idx: int, question: str, child_text: str, history: list[str],
             child_name: str = "Minjun", client=None) -> PageResult:
    client = client or _client()
    feedback: list[str] | None = None
    first_issues: list[str] = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        d = _call(client, build_messages(ctx, seed, page_idx, question, child_text, history, child_name, feedback))
        issues, warnings = guard.check_output(ctx, page_idx, child_text, d)
        if not issues:
            r = _to_result(ctx, seed, page_idx, child_text, d)
            r.attempts, r.guard_issues, r.warnings = attempt, first_issues, warnings
            return r
        first_issues = first_issues or issues
        feedback = issues
    raise GuardFailed(feedback or [])


def llm_available() -> bool:
    if not os.getenv("OPENAI_API_KEY"):
        return False
    try:
        import openai  # noqa: F401
        return True
    except ImportError:
        return False


def generate_page(ctx: UnitContext, seed: dict, page_idx: int, question: str, child_text: str,
                  history: list[str] | None = None, child_name: str = "Minjun", use_llm: bool = True, client=None) -> PageResult:
    found = guard.child_unsafe(child_text)
    if found:
        return safety_page(ctx, seed, page_idx, child_text, found)
    if use_llm and (client is not None or llm_available()):
        try:
            return llm_page(ctx, seed, page_idx, question, child_text, history or [], child_name, client=client)
        except GuardFailed as e:
            r = rule_page(ctx, seed, page_idx, child_text, child_name)
            r.error, r.guard_issues, r.attempts = "AI 결과가 지침 검사를 2번 통과하지 못해 편집자 문장으로 대체", e.issues, MAX_ATTEMPTS
            return r
        except Exception as e:  # 네트워크·형식 오류 → 편집자 문장으로 계속
            r = rule_page(ctx, seed, page_idx, child_text, child_name)
            r.error = f"AI 연결 실패 → 편집자 문장으로 대체: {type(e).__name__}"
            return r
    if seed.get("ai_only"):
        r = PageResult(child_text, "wacky", "Beep! This story opens with AI.", "삐빅! 이 이야기는 AI가 연결되면 열려요.",
                       needs_english=True, engine="rule", error="AI 체험 단원은 OPENAI_API_KEY가 필요해요")
        return r
    return rule_page(ctx, seed, page_idx, child_text, child_name)
