"""
Oh! My Story 핵심 동작 테스트 (OpenAI 키 없이 실행)

python -m pytest -q
- 이야기 씨앗 → 기본 3페이지 → 이어 쓰기 → 최대 8페이지 마무리
- 한국어 → 영어 전환, 안전 필터, 주요 표현 ⭐(채점 아님)
- 가짜 AI 클라이언트로 '생성 → 지침 검사 → 재생성 → 대체' 흐름
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from omstory import config, guard, korean
from omstory import textbook_audio as tba
from omstory.analysis import english_sentences, find_idea
from omstory.prompting import build_messages, load_system
from omstory.rag import ai_units, playable_units, retrieve
from omstory.scene_render import render_scene
from omstory.story import generate_page, lets_together, next_prompt, rule_page


@pytest.fixture(scope="module")
def ctx():
    return retrieve("b6_u01")


class FakeClient:
    """미리 정한 JSON 답을 순서대로 돌려주는 가짜 OpenAI 클라이언트. 받은 메시지를 기록한다."""

    def __init__(self, *answers: dict):
        self.answers = list(answers)
        self.calls: list[list[dict]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.calls.append(kw["messages"])
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(self.answers.pop(0))))])


GOOD = {"speaker": "amy", "reply_en": "Surfing! I enjoy surfing, too. Look at the waves!", "reply_ko": "서핑! 나도 좋아해.",
        "page_en": "Minjun goes surfing with Amy.", "page_ko": "민준이는 Amy와 서핑을 해요.",
        "next_question_en": "Look! Something is in the sand. What is it?", "next_question_ko": "모래 속에 뭔가 있어. 뭘까?",
        "choices": ["It's a seashell.", "It's a treasure map."], "idea": "surfing", "korean_to_english": None,
        "model_sentence": "I enjoy surfing.", "expression_used": False, "safe_redirect": False, "feedback_ko": "멋져!",
        "stickers": ["surfing"], "scene": "beach", "rules_used": ["T1", "T6"]}
BAD = dict(GOOD, reply_en="No, that is wrong. Surfing is a very dangerous and complicated sport for little children.",
           next_question_en="", choices=[])


# ---------- 지침 가이드 ----------
def test_system_prompt_is_co_author_guide():
    s = load_system()
    for k in ["T1.", "T2.", "T3.", "T4.", "T5.", "T6.", "T7.", "Yes, and", "co-author", "korean_to_english"]:
        assert k in s
    assert "<!--" not in s


def test_user_prompt_has_rag_seed_and_page(ctx):
    seed = ctx.seed("summer")
    user = build_messages(ctx, seed, 0, seed["pages"][0]["q"], "surfing", [], "Minjun")[1]["content"]
    assert "I enjoy ~." in user and "story ingredients" in user          # RAG + 주요 표현 = 재료
    assert "신나는 여름 방학" in user and "Planned question for the next page" in user
    last = build_messages(ctx, seed, config.MAX_PAGES - 1, "q", "bye", [], "Minjun")[1]["content"]
    assert "LAST page" in last


# ---------- 이야기 흐름 (편집자 문장) ----------
def test_base_pages_follow_seed_plan(ctx):
    seed = ctx.seed("summer")
    r1 = rule_page(ctx, seed, 0, "surfing")
    assert r1.speaker == "amy" and "surfing" in r1.reply_en
    assert r1.next_q == seed["pages"][1]["q"] and r1.choices                      # 다음 질문 + 고를 거리
    assert r1.model_sentence.startswith("I enjoy surfing")                         # T7, 지적 없이
    r3 = rule_page(ctx, seed, 2, "I like swimming best.")
    assert r3.expression_used and "Let's go swimming together!" in r3.reply_en     # T2 마무리


def test_free_pages_until_max(ctx):
    seed = ctx.seed("summer")
    q, _, ch = next_prompt(seed, config.BASE_PAGES - 1)                            # 기본 이후: 이어 쓰기 질문
    assert q.endswith("?") and len(ch) == 2
    last = rule_page(ctx, seed, config.MAX_PAGES - 1, "We go home.")
    assert last.next_q == "" and last.choices == []                                 # 최대 페이지에서 마무리


def test_every_rule_page_passes_guide(ctx):
    """편집자 문장도 AI와 같은 지침 검사를 통과해야 한다."""
    for seed in ctx.seeds:
        for i in range(config.MAX_PAGES):
            for text in ["surfing", "I like swimming with dolphins best.", "It's a treasure map."]:
                r = rule_page(ctx, seed, i, text)
                d = {"reply_en": r.reply_en, "page_en": r.page_en, "next_question_en": r.next_q, "choices": r.choices}
                issues, _ = guard.check_output(ctx, i, text, d)
                assert issues == [], (seed["id"], i, text, issues)


@pytest.mark.parametrize("text,idea", [("I enjoy surfing.", "surfing"), ("i like ice skating best", "ice skating"),
                                       ("It's a treasure map.", "treasure map"), ("A little dolphin!", "little dolphin")])
def test_find_idea(ctx, text, idea):
    assert find_idea(ctx, text) == idea


def test_speech_volume_counts_english_sentences():
    assert len(english_sentences("I enjoy surfing. I like surfing best.")) == 2
    assert english_sentences("surfing") == [] and english_sentences("서핑 좋아") == []


# ---------- 한국어 → 영어 ----------
def test_korean_to_english_rule(ctx):
    assert korean.convert(ctx, "스키 타는 거 좋아") == "I enjoy skiing."
    assert korean.convert(ctx, "서핑이 제일 좋아") == "I like surfing best."
    r = rule_page(ctx, ctx.seed("winter"), 0, "눈사람 만드는 거")
    assert r.korean_to_english == "I enjoy building snowmen." and r.ask_again
    r2 = rule_page(ctx, ctx.seed("summer"), 1, "보물이 나왔어")                       # 교재 밖 → 고를 거리로
    assert r2.needs_english and r2.choices


def test_lets_together():
    assert lets_together("surfing") == "Let's go surfing together!"
    assert lets_together("ice skating") == "Let's go ice skating together!"
    assert lets_together("building sandcastles") == "Let's build sandcastles together!"


# ---------- 안전 필터 ----------
def test_safety_filter(ctx):
    r = generate_page(ctx, ctx.seed("summer"), 0, "q", "I enjoy fighting with a gun.", use_llm=False)
    assert r.safe_redirect and r.ask_again and r.engine == "safety"
    assert guard.child_unsafe("I like having snowball fights best.") == []


# ---------- AI 결과 검사 → 재생성 → 대체 ----------
def test_guard(ctx):
    assert guard.check_output(ctx, 0, "surfing", GOOD)[0] == []
    issues = " ".join(guard.check_output(ctx, 0, "surfing", BAD)[0])
    assert "wrong" in issues and "too long" in issues and "question" in issues and "choices" in issues


def test_llm_good_first_try(ctx):
    fake = FakeClient(GOOD)
    r = generate_page(ctx, ctx.seed("summer"), 0, "q", "surfing", client=fake)
    assert r.engine == "llm" and r.attempts == 1 and r.next_q and r.choices
    assert fake.calls[0][0]["role"] == "system"


def test_llm_retry_then_fallback(ctx):
    fake = FakeClient(BAD, GOOD)
    r = generate_page(ctx, ctx.seed("summer"), 0, "q", "surfing", client=fake)
    assert r.engine == "llm" and r.attempts == 2 and r.guard_issues
    assert "broke these rules" in fake.calls[1][1]["content"]
    r2 = generate_page(ctx, ctx.seed("summer"), 0, "q", "surfing", client=FakeClient(BAD, BAD))
    assert r2.engine == "rule" and "지침 검사" in (r2.error or "")


def test_llm_korean_to_english(ctx):
    ans = dict(GOOD, reply_en="Beep! Great idea! Say it in English.", page_en="", next_question_en="", choices=[],
               korean_to_english="A crab family lives in the sandcastle!")
    r = generate_page(ctx, ctx.seed("summer"), 1, "q", "모래성에 꽃게 가족이 살아!", client=FakeClient(ans))
    assert r.korean_to_english.startswith("A crab family") and r.ask_again


# ---------- 단원·장면·원음 ----------
def test_units_open_and_ai_trial():
    assert [u["id"] for u in playable_units()] == ["b6_u01"]
    assert len(ai_units()) == 7
    c3 = retrieve("b6_u03")
    assert c3.seeds[0]["ai_only"] and c3.seeds[0]["pages"][0]["q"] == c3.unit["useful_questions"][0]
    r = generate_page(c3, c3.seeds[0], 0, "q", "It's $100.", use_llm=False)
    assert r.error and "OPENAI_API_KEY" in r.error                                   # 키 없으면 체험 불가 안내


def test_scene_render():
    img = render_scene("beach", ["amy", "wacky"], ["surfing", "building sandcastles"], "crab family")
    assert img[:2] == b"\xff\xd8" and len(img) > 10_000


def test_textbook_audio_links():
    assert tba.dialogue("b6_u01")[0] is not None and tba.clip("b6_u01", "q.summer") is not None
    assert len(tba.model_sentence("b6_u01", "surfing", "I enjoy ___. I like ___ best.")) == 2


def test_each_character_has_its_own_voice():
    from omstory.speech import VOICES
    assert len({(v["voice"], v["pitch"]) for v in VOICES.values()}) == len(VOICES)
