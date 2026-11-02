"""
textbook_audio.py — 교재 원음(MP3) 연결

원칙: 교재에 있는 문장은 교재 성우 목소리(원음)로, AI가 새로 만든 대사만 TTS로 들려준다.
- kb/audio/<unit>/index.json : 대사 ID → 잘라 둔 원음 파일 (tools/split_audio.py로 생성)
- 교재 음원은 AI로 가공하지 않고, 대사 ID로 찾아서 그대로 재생만 한다.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

AUDIO_ROOT = Path(__file__).resolve().parent.parent / "kb" / "audio"
UNIT_DIRS = {"b6_u01": "b6_u01"}


def slug(s: str) -> str:
    return re.sub(r"[^a-z]+", "_", s.lower()).strip("_")


@lru_cache(maxsize=8)
def load_index(unit_id: str) -> dict:
    d = UNIT_DIRS.get(unit_id)
    p = AUDIO_ROOT / d / "index.json" if d else None
    if not p or not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _path(unit_id: str, rel: str) -> Path | None:
    p = AUDIO_ROOT / UNIT_DIRS[unit_id] / rel
    return p if p.exists() else None


def clip(unit_id: str, clip_id: str | None) -> Path | None:
    """대사 ID → 원음 파일 경로 (없으면 None → 앱이 TTS로 대체)."""
    if not clip_id:
        return None
    c = load_index(unit_id).get("clips", {}).get(clip_id)
    return _path(unit_id, c["file"]) if c else None


def dialogue(unit_id: str) -> tuple[Path | None, str]:
    d = load_index(unit_id).get("dialogue")
    return (_path(unit_id, d["file"]), d["text"]) if d else (None, "")


def word(unit_id: str, w: str) -> Path | None:
    return clip(unit_id, f"word.{slug(w)}")


def model_sentence(unit_id: str, idea: str, frame: str) -> list[Path]:
    """아이 아이디어가 교재 어휘면, 그 패턴 문장의 원음을 돌려준다 (리캐스트·모범 문장용).
    교재 밖 아이디어(예: swimming with dolphins)는 빈 목록 → TTS로 대체."""
    s = slug(idea)
    ids = ([f"enjoy.{s}"] if "enjoy" in frame.lower() else []) + ([f"best.{s}"] if "best" in frame.lower() else [])
    paths = [clip(unit_id, i) for i in ids]
    return [p for p in paths if p]


def join_mp3(paths: list[Path]) -> bytes:
    """MP3 조각 이어 붙이기 (같은 인코딩이라 프레임을 그대로 이어도 재생된다)."""
    return b"".join(p.read_bytes() for p in paths)
