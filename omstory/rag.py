"""
rag.py — 교재 지식베이스 조회 (Retrieval)

설계 원칙
- 1차 조회는 Unit ID 메타데이터 필터링: 아이가 들어온 단원의 데이터를 정확히 꺼낸다 (조회 정확도 100%).
- 이미 배운 단원(이전 단원)의 패턴·어휘도 함께 꺼내서, 이야기 속에서 계속 반복되게 한다 (나선형 복습).
- 단원 수가 적어 벡터 검색은 필요 없다. 교재·권이 늘어나면 같은 구조에 벡터 검색을 추가하면 된다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

KB_PATH = Path(__file__).resolve().parent.parent / "kb" / "units.json"

ARTICLES = {"a", "an", "the", "my", "your"}
TOKEN_RE = re.compile(r"[a-z][a-z'’\-]*")

# 이야기에서 써도 되는 아주 기본적인 단어 (기능어·감탄사·캐릭터 이름 등)
BASIC_WORDS = set("""
a an the is are am was were be it its it's isn't not no yes i you we they he she me us them my your our their his her
to and so but or with at in on of for up down here there now this that these those what who where how do does did don't
want go goes let's lets let come see look looks wow yay oh hi hello bye bye-bye beep boop pop yum hooray okay ok
good great nice cool fun very too all one two three new day today time together more some little many again home
can will have has had like likes love play plays sit down open opens right thank thanks welcome you're me too
please sure guess question picture friend friends room box magic secret jack amy tom mom wacky dad also really
just same hmm say english summer winter brrr beach snow vacation vacations go best enjoy watching fun here's that's what's who's there's they're i'm he's she's it'll we're happy
""".split())


def tokens(text: str) -> list[str]:
    return [t.replace("’", "'") for t in TOKEN_RE.findall(text.lower().replace("’", "'"))]


@dataclass
class UnitContext:
    """한 번의 대화에서 LLM과 지표 계산에 쓰는 단원 맥락."""
    unit: dict
    learned_units: list[dict] = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.unit["id"]

    @property
    def seeds(self) -> list[dict]:
        """편집자가 준비한 이야기 씨앗 (없으면 AI 체험용 기본 씨앗)."""
        return self.unit.get("seeds") or [default_seed(self.unit)]

    def seed(self, seed_id: str | None) -> dict:
        return next((s for s in self.seeds if s["id"] == seed_id), self.seeds[0])

    @property
    def key_expressions(self) -> list[dict]:
        """오늘의 주요 표현 (이야기 재료). 없으면 Key Patterns를 그대로 쓴다."""
        return self.unit.get("key_expressions") or [{"en": p, "ko": ""} for p in self.unit["key_patterns"]]

    @property
    def pattern_stems(self) -> list[str]:
        """핵심 패턴의 '문장 틀' (예: It's a robot. → it's / It's not a backpack. → it's not).
        지식베이스에 pattern_stems가 있으면 그것을 쓰고, 없으면 패턴에서 어휘·관사를 빼서 만든다."""
        if self.unit.get("pattern_stems"):
            return sorted(self.unit["pattern_stems"], key=len, reverse=True)
        vocab = set()
        for w in self.unit["vocabulary"]:
            vocab.update(tokens(w))
        stems = []
        for p in self.unit["key_patterns"]:
            stem = [t for t in tokens(p) if t not in vocab and t not in ARTICLES]
            s = " ".join(stem).strip()
            if s and s not in stems:
                stems.append(s)
        return sorted(stems, key=len, reverse=True)

    def allowed_words(self) -> set[str]:
        """교재 범위 단어 = 현재 단원 + 이미 배운 단원의 패턴·어휘·표현 + 기본 단어."""
        words = set(BASIC_WORDS)
        for u in [self.unit, *self.learned_units]:
            for key in ("key_patterns", "vocabulary", "useful_expressions", "useful_questions"):
                for s in u.get(key, []):
                    words.update(tokens(s))
            for sd in u.get("seeds", []):
                words.update(tokens(sd["opening"]["en"]))
                for pg in sd["pages"]:
                    words.update(tokens(pg["q"] + " " + " ".join(pg.get("choices", [])) + " " + pg.get("react", "")))
        return words

    def prompt_block(self) -> str:
        """LLM 프롬프트에 넣을 '검색된 교재 내용' 텍스트."""
        u = self.unit
        lines = [
            f"Current unit: Unit {u['no']:02d} \"{u['title']}\" (theme: {u['theme']})",
            f"- Today's key expressions (story ingredients): {' | '.join(e['en'] for e in self.key_expressions)}",
            f"- Key patterns (examples): {' | '.join(u['key_patterns'])}",
            f"- Vocabulary: {', '.join(u['vocabulary'])}",
            f"- Useful questions: {' | '.join(u['useful_questions']) or '-'}",
            f"- Useful expressions: {' | '.join(u['useful_expressions']) or '-'}",
        ]
        if self.learned_units:
            lines.append("Already learned (you may reuse):")
            for lu in self.learned_units:
                lines.append(f"- Unit {lu['no']:02d}: {' | '.join(lu['key_patterns'])}; words: {', '.join(lu['vocabulary'][:8])}")
        return "\n".join(lines)


@lru_cache(maxsize=1)
def load_kb(path: str | None = None) -> dict:
    return json.loads(Path(path or KB_PATH).read_text(encoding="utf-8"))


def list_units() -> list[dict]:
    return load_kb()["units"]


def default_seed(unit: dict) -> dict:
    """씨앗이 아직 없는 단원(AI 체험)용 기본 씨앗: 단원 주제와 주요 표현만으로 AI가 이야기를 만든다."""
    q = unit["useful_questions"][0] if unit.get("useful_questions") else "Where are we today?"
    return {"id": "theme", "title": f"{unit.get('theme_ko') or unit['theme']} 이야기", "emoji": "✨",
            "desc": f"'{unit['key_patterns'][0]}'로 시작하는 이야기", "scene": "park", "ai_only": True,
            "opening": {"speaker": "wacky", "en": "Beep! Let's make a new story together!", "ko": "삐빅! 같이 새 이야기를 만들자!"},
            "pages": [{"q": q, "q_ko": "", "choices": [], "speaker": "wacky", "scene": "",
                       "beat": f"Start a story about '{unit['theme']}' where the key expressions come up naturally."}]}


def playable_units() -> list[dict]:
    """편집자 씨앗·대사까지 준비된 단원 (AI 없이도 끝까지 동작)."""
    return [u for u in list_units() if u.get("seeds")]


def ai_units() -> list[dict]:
    """씨앗은 없지만 AI가 주요 표현으로 이야기를 만들 수 있는 단원 (AI 체험)."""
    return [u for u in list_units() if not u.get("seeds")]


def get_unit(unit_id: str) -> dict:
    for u in list_units():
        if u["id"] == unit_id:
            return u
    raise KeyError(f"단원을 찾을 수 없어요: {unit_id}")


def retrieve(unit_id: str, include_learned: bool = True) -> UnitContext:
    """Unit ID로 현재 단원을 조회하고, 선택적으로 이전 단원들을 함께 묶는다."""
    unit = get_unit(unit_id)
    learned = [u for u in list_units() if u.get("book") == unit.get("book") and u["no"] < unit["no"]] if include_learned else []
    return UnitContext(unit=unit, learned_units=learned)
