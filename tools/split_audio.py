"""
split_audio.py — 교재 MP3를 문장(대사) 단위로 잘라 대사 ID에 연결한다.

원칙
- 교재 음원은 AI로 가공하지 않는다. 무음 구간으로 자르기만 하고, 원음 그대로 쓴다.
- 어떤 조각이 어떤 문장인지는 TG(교사용 지침서)의 트랙별 스크립트 순서로 맞춘다.
  (각 트랙 앞부분의 안내 멘트 조각은 건너뛴다)
- 결과: kb/audio/b6_u01/clips/<대사ID>.mp3 + kb/audio/b6_u01/index.json

실행: python tools/split_audio.py
주의: 자동으로 자른 결과이므로, 실제 서비스 전에는 사람이 한 번 들어보고 확인해야 한다.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "kb" / "audio" / "b6_u01"
TRACKS = BASE / "tracks"
CLIPS = BASE / "clips"

SUMMER = ["swimming", "surfing", "sunbathing", "diving", "snorkeling",
          "building sandcastles", "collecting seashells", "playing beach volleyball"]
WINTER = ["building snowmen", "having snowball fights", "making snow angels",
          "skiing", "snowboarding", "ice skating"]


def slug(s: str) -> str:
    return re.sub(r"[^a-z]+", "_", s.lower()).strip("_")


def segments(path: Path, noise: int = -38, min_sil: float = 0.45) -> list[tuple[float, float]]:
    """ffmpeg silencedetect로 '말하는 구간' 목록을 구한다."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
                          f"silencedetect=noise={noise}dB:d={min_sil}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(path)], capture_output=True, text=True).stdout)
    if len(ends) < len(starts):
        ends.append(dur)
    out, cur = [], 0.0
    for a, b in zip(starts, ends):
        if a - cur > 0.15:
            out.append((cur, a))
        cur = b
    if dur - cur > 0.15:
        out.append((cur, dur))
    return out


def plan() -> list[dict]:
    """트랙별 TG 스크립트 순서 → (트랙, 조각 번호, 대사 ID, 문장)."""
    items: list[dict] = []

    def add(track, idx, cid, text, kind):
        items.append({"track": track, "seg": idx, "id": cid, "text": text, "kind": kind})

    # Track 02: 안내 4조각 + 여름 단어 8개 (Vocabulary A: Listen, point, and say)
    for i, w in enumerate(SUMMER):
        add("02", 4 + i, f"word.{slug(w)}", w, "word")
    # Track 04: 안내 4조각 + [질문, I enjoy, I like best] × 9 (첫 묶음은 swimming 예시)
    add("04", 4, "q.summer", "What do you like doing in the summer?", "question")
    for i, w in enumerate(SUMMER):
        g = 4 + 3 * (i + 1)
        add("04", g + 1, f"enjoy.{slug(w)}", f"I enjoy {w}.", "pattern")
        add("04", g + 2, f"best.{slug(w)}", f"I like {w} best.", "pattern")
    # Track 05: 안내 4조각 + [번호, 질문, I enjoy, I like best] × 6 (겨울 활동)
    add("05", 5, "q.winter", "What do you like doing in the winter?", "question")
    for i, w in enumerate(WINTER):
        g = 4 + 4 * i
        add("05", g + 2, f"enjoy.{slug(w)}", f"I enjoy {w}.", "pattern")
        add("05", g + 3, f"best.{slug(w)}", f"I like {w} best.", "pattern")
    # Track 06: "Me, too." (Listen and say B 마지막 대사)
    add("06", 9, "expr.me_too", "Me, too.", "expression")
    return items


def main() -> None:
    CLIPS.mkdir(parents=True, exist_ok=True)
    segs = {t: segments(TRACKS / f"Track_{t}.mp3") for t in ("02", "04", "05", "06")}
    expected = {"02": 12, "04": 31, "05": 28, "06": 10}
    for t, n in expected.items():
        if len(segs[t]) != n:
            raise SystemExit(f"Track {t}: 조각 {len(segs[t])}개 (예상 {n}개) — 무음 기준을 확인하세요")

    index = {
        "_meta": {
            "source": "Oh! My Speaking 6 Unit 01 교재 음원 (Track 01~09)",
            "method": "무음 구간으로 자르고 TG 스크립트 순서로 대사 ID에 연결 (원음 그대로, AI 가공 없음)",
            "review": "자동 분할 결과 — 서비스 전 사람이 들어보고 확인 필요",
            "not_used_in_step5": ["Track_07", "Track_08", "Track_09 (Listen and Check — 교재 Step 4 평가용)"],
        },
        "dialogue": {"id": "dialogue.unit01", "file": "tracks/Track_01.mp3",
                     "text": "Jack: I like summer best. I love summer vacations! / Amy: Me, too. / "
                             "Amy: What do you like doing in the summer? / Jack: I enjoy swimming. I like swimming best. / "
                             "Amy: How about surfing? / Jack: Oh, surfing is fun! / Amy: Great! Let's go surfing together! / "
                             "Jack: Oh no! I enjoy watching surfing."},
        "clips": {},
    }
    for it in plan():
        a, b = segs[it["track"]][it["seg"]]
        a, b = max(0.0, a - 0.08), b + 0.12
        out = CLIPS / f"{it['id']}.mp3"
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(TRACKS / f"Track_{it['track']}.mp3"),
                        "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-c:a", "libmp3lame", "-q:a", "4", str(out)], check=True)
        index["clips"][it["id"]] = {"file": f"clips/{out.name}", "text": it["text"], "kind": it["kind"],
                                    "track": it["track"], "start": round(a, 2), "end": round(b, 2)}
    (BASE / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"대사 클립 {len(index['clips'])}개 → {CLIPS}")


if __name__ == "__main__":
    main()
