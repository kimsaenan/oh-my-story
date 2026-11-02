"""
pipeline.py — 한 페이지 처리: (STT) → 안전 필터 → RAG + 지침 → 이야기 생성 → 검사 → (TTS)
앱과 평가 스크립트가 같은 함수를 쓰므로, 평가 결과가 실제 앱 동작과 같다.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

from . import speech
from .analysis import english_sentences, off_unit_rate
from .rag import UnitContext
from .story import PageResult, generate_page


@dataclass
class PageOutput:
    result: PageResult
    off_unit_rate: float
    timings: dict = field(default_factory=dict)   # 단계별 소요 시간(초)
    audio: bytes | None = None                    # 캐릭터 반응 음성 (캐릭터별 목소리)

    @property
    def child_sentences(self) -> list[str]:
        return english_sentences(self.result.child_text)

    def to_row(self) -> dict:
        r = asdict(self.result)
        for k in ("rules_used", "guard_issues", "warnings", "choices", "stickers"):
            r[k] = " | ".join(r.get(k) or [])
        r.update(off_unit_rate=round(self.off_unit_rate, 3), **{f"t_{k}": round(v, 3) for k, v in self.timings.items()})
        return r


def run_page(ctx: UnitContext, seed: dict, page_idx: int, question: str, *, text: str | None = None,
             audio: bytes | None = None, history: list[str] | None = None, child_name: str = "Minjun",
             use_llm: bool = True, with_tts: bool = True, client=None) -> PageOutput:
    timings = {}
    t0 = time.perf_counter()
    if audio is not None and not text:
        text = speech.transcribe(audio, hint_words=ctx.unit["vocabulary"])
        timings["stt"] = time.perf_counter() - t0
    text = (text or "").strip()

    t1 = time.perf_counter()
    res = generate_page(ctx, seed, page_idx, question, text, history, child_name, use_llm=use_llm, client=client)
    timings["generate"] = time.perf_counter() - t1

    rate = off_unit_rate(ctx, " ".join([res.reply_en, res.next_q]), " ".join([text] + res.choices))
    snd = None
    if with_tts:
        t2 = time.perf_counter()
        snd = speech.synthesize(res.reply_en, speaker=res.speaker)
        timings["tts"] = time.perf_counter() - t2
    timings["total"] = time.perf_counter() - t0
    return PageOutput(res, rate, timings, snd)
