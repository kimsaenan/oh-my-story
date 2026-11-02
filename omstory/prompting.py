"""
prompting.py — Wacky(공동 작가)에게 보낼 프롬프트 만들기

- system: prompts/wacky_tutor_system.md (지침 가이드: 공동 작가 역할 + 이야기 끌어내기 + TG Teaching Tips T1~T7 + 출력 형식 + 예시)
- user  : 이번 페이지에 필요한 것만 — RAG로 꺼낸 교재 내용, 이야기 씨앗, 페이지 정보, 지금까지 이야기, 질문, 아이 말
- 검사(guard.py)에서 문제가 나오면 그 내용을 붙여 한 번 더 만들게 한다.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from . import config
from .rag import UnitContext
from .scenes import FANTASY_SCENES

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
SYSTEM_FILE = PROMPT_DIR / "wacky_tutor_system.md"


@lru_cache(maxsize=1)
def load_system() -> str:
    """지침 가이드 파일을 읽는다. 사람용 주석(<!-- -->)은 빼고 보낸다."""
    text = SYSTEM_FILE.read_text(encoding="utf-8")
    return re.sub(r"<!--.*?-->\s*", "", text, flags=re.S).strip()


def page_plan(seed: dict, page_idx: int) -> dict:
    """이번 페이지의 편집자 계획 (기본 페이지면 씨앗의 계획, 이어 쓰는 페이지면 비어 있음)."""
    pages = seed.get("pages", [])
    return pages[page_idx] if page_idx < len(pages) else {}


def build_user(ctx: UnitContext, seed: dict, page_idx: int, question: str, child_text: str, history: list[str],
               child_name: str = "the child", feedback: list[str] | None = None) -> str:
    plan = page_plan(seed, page_idx)
    nxt = page_plan(seed, page_idx + 1)
    last = page_idx + 1 >= config.MAX_PAGES
    base_end = page_idx + 1 == config.BASE_PAGES
    lines = [
        "[Retrieved textbook content — stay within this level]",
        ctx.prompt_block(),
        "",
        "[Story seed]",
        f"- Title: {seed['title']} · start place: {seed.get('scene') or 'any'}",
        f"- Child's name (author): {child_name}",
        "",
        f"[Page info] page {page_idx + 1} (base story {config.BASE_PAGES} pages, max {config.MAX_PAGES} pages)",
        f"- Page type: {'base page (planned by the editor)' if plan else 'free page (the child continues the story)'}",
        f"- Speaker for this page: {plan.get('speaker', 'any friend (wacky, jack, amy or tom)')}",
        f"- What happens: {plan.get('beat', 'Continue from the child idea. Yes-and, add one small new thing.')}",
        f"- Scene list (only if the child's idea moves the story): {', '.join(FANTASY_SCENES)}",
    ]
    if last:
        lines.append("- This is the LAST page: end the story happily (a Useful Expression is a nice last line). No next question.")
    elif nxt:
        lines.append(f'- Planned question for the next page: "{nxt["q"]}" (use it as next_question_en; choices can follow: {nxt.get("choices", [])})')
    else:
        lines.append("- Invent the next question and two choices yourself.")
    if base_end:
        lines.append("- The base story ends here. Make it feel like a happy chapter end, but still ask the next question "
                     "(the child may choose to continue).")
    lines += [
        "",
        "[Story so far]",
        "\n".join(history[-10:]) or "(start)",
        "",
        f'[Wacky asked] "{question}"',
        f'[Child said] "{child_text}"',
    ]
    if feedback:
        lines += ["", "[Your previous answer broke these rules. Fix them and answer again with JSON only]"]
        lines += [f"- {f}" for f in feedback]
    return "\n".join(lines)


def build_messages(ctx: UnitContext, seed: dict, page_idx: int, question: str, child_text: str, history: list[str],
                   child_name: str = "the child", feedback: list[str] | None = None) -> list[dict]:
    return [{"role": "system", "content": load_system()},
            {"role": "user", "content": build_user(ctx, seed, page_idx, question, child_text, history, child_name, feedback)}]


# 화면·리포트에 보여 줄 Teaching Rules 이름 (prompts/wacky_tutor_system.md 3장과 같은 번호)
RULE_NAMES_KO = {
    "T1": "상상·경험 살리기",
    "T2": "Useful Expressions·Questions 쓰기",
    "T3": "배운 표현 다시 쓰기",
    "T4": "필요할 때 힌트",
    "T5": "새 단어도 받아 주기",
    "T6": "느낌·생각 나누기",
    "T7": "완전한 문장으로",
}
