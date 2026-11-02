"""
speech.py — STT(음성→글자)와 TTS(글자→음성)

STT: faster-whisper(로컬). 단원 어휘를 initial_prompt로 넣어 아이가 말할 법한 단어를 더 잘 알아듣게 한다.
     → RAG로 꺼낸 단원 정보가 음성 인식도 돕는 구조.
TTS: edge-tts (PoC용). 캐릭터마다 다른 목소리(VOICES). 정식 서비스에서는 사용 조건이 분명한 공식 TTS(예: Azure Speech)나 교재 MP3로 교체.
"""
from __future__ import annotations

import asyncio
import os
import tempfile

_whisper = None


def stt_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def transcribe(audio_bytes: bytes, hint_words: list[str] | None = None, model_size: str | None = None) -> str:
    """녹음(wav 등 bytes) → 텍스트. 영어·한국어 섞인 말도 받기 위해 언어 자동 감지."""
    global _whisper
    from faster_whisper import WhisperModel

    if _whisper is None:
        _whisper = WhisperModel(model_size or os.getenv("WHISPER_MODEL", "base"), device="cpu", compute_type="int8")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        path = f.name
    try:
        prompt = ("Kids English practice. Words: " + ", ".join(hint_words)) if hint_words else None
        segments, _ = _whisper.transcribe(path, initial_prompt=prompt, vad_filter=True, beam_size=5)
        return " ".join(s.text.strip() for s in segments).strip()
    finally:
        os.unlink(path)


def tts_available() -> bool:
    try:
        import edge_tts  # noqa: F401
        return True
    except ImportError:
        return False


# 캐릭터별 목소리 (edge-tts 음성 + 높낮이·빠르기). 정식 서비스에서는 성우 녹음 또는 캐릭터 전용 TTS 음성으로 교체.
VOICES = {
    "wacky": {"voice": "en-US-AnaNeural", "pitch": "+25Hz", "rate": "+0%"},         # 로봇: 높고 통통 튀는 목소리
    "jack": {"voice": "en-US-AndrewNeural", "pitch": "+35Hz", "rate": "-5%"},       # 남자아이
    "amy": {"voice": "en-US-AnaNeural", "pitch": "+0Hz", "rate": "-10%"},           # 여자아이
    "tom": {"voice": "en-US-ChristopherNeural", "pitch": "+30Hz", "rate": "-5%"},   # 남자아이 (Jack과 다르게)
    "mom": {"voice": "en-US-JennyNeural", "pitch": "+0Hz", "rate": "-10%"},         # 엄마
}
DEFAULT_VOICE = VOICES["wacky"]


def voice_for(speaker: str | None) -> dict:
    v = dict(VOICES.get((speaker or "").lower(), DEFAULT_VOICE))
    if os.getenv("TTS_VOICE") and not speaker:  # 환경변수로 기본 목소리만 바꿀 수 있음
        v["voice"] = os.getenv("TTS_VOICE")
    return v


async def _tts(text: str, voice: str, rate: str, pitch: str = "+0Hz") -> bytes:
    import edge_tts

    out = b""
    async for chunk in edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch).stream():
        if chunk["type"] == "audio":
            out += chunk["data"]
    return out


def synthesize(text: str, speaker: str | None = None) -> bytes | None:
    """영어 문장 → mp3 bytes. speaker(wacky/jack/amy/tom/mom)에 따라 목소리가 달라짐. 실패하면 None (글자만 보여줌)."""
    if not text.strip() or not tts_available():
        return None
    v = voice_for(speaker)
    try:
        return asyncio.run(_tts(text, v["voice"], v["rate"], v["pitch"])) or None
    except Exception:
        return None
