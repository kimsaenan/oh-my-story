"""
card.py — 스토리 카드(PNG) 만들기

기본: 미리 준비한 스티커·배경을 조합 (AI 그림 없이, 비용 0, 캐릭터 일관성 유지).
- assets/stickers/<단어>.png, assets/backgrounds/<scene>.png 가 있으면 그 그림(교재 원화)을 쓰고,
  없으면 색 원 + 단어 이름의 자리표시 스티커를 그린다.
선택: AI 그림은 시즌 마무리 표지처럼 '한 번만' 쓰는 것을 권장 (make_card의 cover_image 인자로 넣기).
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
W, H = 1080, 1440

SCENES = {  # (하늘, 땅) 색
    "classroom": ("#dceeff", "#f3d9a4"), "toyroom": ("#ffe3f1", "#f6cfa0"), "picnic": ("#cdeeff", "#9fd97a"),
    "park": ("#cdeeff", "#8fd17a"), "home": ("#fff1d6", "#e9c08f"), "zoo": ("#d7f2ff", "#a7d36e"),
    "petshop": ("#e9f7ef", "#f2d29b"), "room": ("#efe8ff", "#d9b98c"),
}
CHAR_COLORS = {"wacky": "#7a56e0", "jack": "#e2b322", "amy": "#ff8a3d", "tom": "#3b6fd8", "mom": "#e2577a"}
INK, MUTED, ACCENT, SUN = "#1f2a37", "#5b6676", "#6a4bd6", "#ffc93c"

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    str(ASSETS / "fonts" / "NotoSansKR-Bold.ttf"),
]


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    cands = FONT_CANDIDATES if bold else [c.replace("Bold", "Regular").replace("malgunbd", "malgun") for c in FONT_CANDIDATES]
    for p in cands:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default(size)


def _color_for(word: str) -> str:
    h = int(hashlib.md5(word.encode()).hexdigest()[:6], 16)
    palette = ["#ff8a65", "#4fc3f7", "#81c784", "#ba68c8", "#ffb74d", "#f06292", "#4db6ac", "#9575cd"]
    return palette[h % len(palette)]


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    lines = []
    for para in text.split("\n"):
        words, cur = para.split(" "), ""
        for w in words:
            t = (cur + " " + w).strip()
            if draw.textlength(t, font=font) <= max_w:
                cur = t
            else:
                if cur:
                    lines.append(cur)
                # 한국어처럼 공백 없이 긴 줄 대비
                while draw.textlength(w, font=font) > max_w and len(w) > 1:
                    cut = max(1, int(len(w) * max_w / draw.textlength(w, font=font)) - 1)
                    lines.append(w[:cut]); w = w[cut:]
                cur = w
        if cur:
            lines.append(cur)
    return lines


def find_sticker(phrase: str) -> Path | None:
    """'flying chair' → chair.png 처럼, 문구 안의 단어 중 준비된 스티커를 찾는다 (뒤쪽 단어·긴 단어 우선)."""
    folder = ASSETS / "stickers"
    words = phrase.lower().replace("-", " ").split()
    for n in (3, 2, 1):
        for i in range(len(words) - n, -1, -1):
            cand = "_".join(words[i:i + n])
            for name in (cand, cand.rstrip("s")):
                p = folder / f"{name}.png"
                if p.exists():
                    return p
    return None


def _fit_font_size(word: str, max_w: int | None, fs: int = 30) -> int:
    while max_w and fs > 15 and ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(word, font=_font(fs)) + 32 > max_w:
        fs -= 2
    return fs


def _sticker(word: str, size: int, max_w: int | None = None, fs: int | None = None) -> Image.Image:
    """준비된 그림이 있으면 그림 + 이름표, 없으면 색 원 + 이름표. 이름표는 max_w 안에 들어가게 글자 크기를 줄인다."""
    fs = fs or _fit_font_size(word, max_w)
    lf = _font(fs)
    tw = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(word, font=lf)
    cw = int(max(size, tw + 32))
    img = Image.new("RGBA", (cw, size + 44), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cw / 2
    p = find_sticker(word)
    if p:
        art = Image.open(p).convert("RGBA").resize((size, size), Image.LANCZOS)
        img.paste(art, (int(cx - size / 2), 0), art)
    else:
        d.ellipse((cx - size / 2 + 6, 6, cx + size / 2 - 6, size - 6), fill=_color_for(word), outline="white", width=8)
        d.text((cx, size / 2), word[0].upper(), font=_font(int(size * .42)), fill="white", anchor="mm")
    d.rounded_rectangle((cx - tw / 2 - 12, size + 2, cx + tw / 2 + 12, size + 42), 10, fill="white")
    d.text((cx, size + 22), word, font=lf, fill=INK, anchor="mm")
    return img


def _character(key: str, size: int) -> Image.Image:
    p = ASSETS / "characters" / f"{key}.png"
    if p.exists():
        return Image.open(p).convert("RGBA").resize((size, size))
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, size - 4, size - 4), fill=CHAR_COLORS.get(key, ACCENT), outline="white", width=7)
    d.text((size / 2, size / 2), key[0].upper(), font=_font(int(size * .45)), fill="white", anchor="mm")
    return img


def make_card(unit: dict, child_name: str, child_sentences: list[str], story_lines: list[tuple[str, str]],
              stickers: list[str], ideas: list[str], cover_image: Image.Image | None = None,
              characters: list[str] | None = None, scene: str | None = None) -> bytes:
    """스토리 카드 PNG bytes. story_lines = [(speaker, english)], characters = 장면에 세울 캐릭터 (기본: 이야기에 나온 캐릭터)"""
    if characters is None:
        characters = ["wacky"] + [sp for sp, _ in story_lines if sp in CHAR_COLORS and sp != "wacky"]
        characters = list(dict.fromkeys(characters))[:3]
    img = Image.new("RGB", (W, H), "#fffaf0")
    d = ImageDraw.Draw(img)

    # 상단 띠
    d.rectangle((0, 0, W, 120), fill=ACCENT)
    d.text((48, 60), "Oh! My Story", font=_font(52), fill="white", anchor="lm")
    d.text((W - 48, 60), f"Unit {unit['no']:02d} · {unit['title']}", font=_font(32), fill="white", anchor="rm")

    # 장면 영역
    top, scene_h = 150, 560
    scene = scene or unit.get("scene", "")
    sky, ground = SCENES.get(scene, ("#dceeff", "#e6d2a8"))
    if cover_image is not None:
        img.paste(cover_image.convert("RGB").resize((W - 96, scene_h)), (48, top))
    else:
        bg = ASSETS / "backgrounds" / f"{scene}.png"
        if bg.exists():
            b = Image.open(bg).convert("RGB")
            bw, bh = b.size  # 장면 비율에 맞게 가운데를 잘라서 채우기
            tw_, th_ = W - 96, scene_h
            scale = max(tw_ / bw, th_ / bh)
            b = b.resize((int(bw * scale), int(bh * scale)), Image.LANCZOS)
            b = b.crop(((b.width - tw_) // 2, b.height - th_, (b.width - tw_) // 2 + tw_, b.height))
            mask = Image.new("L", (tw_, th_), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, tw_, th_), 36, fill=255)
            img.paste(b, (48, top), mask)
        else:
            d.rounded_rectangle((48, top, W - 48, top + scene_h), 36, fill=sky)
            d.rounded_rectangle((48, top + int(scene_h * .62), W - 48, top + scene_h), 36, fill=ground)
            d.rectangle((48, top + int(scene_h * .62), W - 48, top + int(scene_h * .62) + 40), fill=ground)
        # 캐릭터: 장면 왼쪽에 서 있게 (교재 캐릭터 그림이 있으면 그 그림)
        real = any((ASSETS / "characters" / f"{c}.png").exists() for c in characters)
        n_items = len(list(dict.fromkeys([i for i in ideas if i][:3] + [s for s in stickers if s not in ideas][:3])))
        if real and n_items >= 3 and len(characters) >= 3:  # 스티커 3개면 캐릭터 2명으로 줄여 이름표 공간 확보
            characters = characters[:2]
        csize = (290 if len(characters) >= 3 else 310) if real else 130
        for k, ch in enumerate(characters):
            c = _character(ch, csize)
            x = 60 + k * int(csize * .58)
            y = top + scene_h - csize - 18 if real else top + 30
            img.paste(c, (x, y), c)
        # 스티커 (아이 상상 → 단원 어휘 순): 캐릭터 오른쪽 공간에
        items = [i for i in ideas if i][:3] + [s for s in stickers if s not in ideas][:3]
        items = list(dict.fromkeys(items))[:4 if real else 5] or ["star"]
        if real:
            # 캐릭터 오른쪽 바닥에 한 줄로 (최대 3개) → 위쪽 배경은 비워 둬서 장면이 답답하지 않게
            items = items[:3]
            right_x0 = 60 + (len(characters) - 1) * int(csize * .58) + csize + 4
            cell_w = (W - 60 - right_x0) / max(1, len(items))
            size = int(min(170, cell_w - 16))
            fs = min(_fit_font_size(w, int(cell_w - 10)) for w in items)  # 이름표 글자 크기 통일 (칸을 넘지 않게)
            for k, w in enumerate(items):
                s = _sticker(w, size, fs=fs)
                x = int(right_x0 + cell_w * k + (cell_w - s.width) / 2)
                y = top + scene_h - s.height - 30
                img.paste(s, (x, y), s)
        else:
            size, x0 = 150, 108
            gap = (W - 48 - 20 - x0) / max(1, len(items))
            for k, w in enumerate(items):
                s = _sticker(w, size)
                x = int(x0 + gap * k + (gap - s.width) / 2)
                img.paste(s, (x, top + int(scene_h * .40) - (k % 2) * 70), s)

    # 아이 문장
    y = top + scene_h + 40
    d.text((48, y), f"{child_name}의 문장", font=_font(30), fill=MUTED)
    y += 50
    for s in child_sentences[:3]:
        for line in _wrap(d, f"“{s}”", _font(40), W - 96):
            d.text((48, y), line, font=_font(40), fill=INK)
            y += 54
    # 이야기
    y += 16
    d.line((48, y, W - 48, y), fill="#eadfc8", width=3)
    y += 24
    for sp, en in story_lines[-3:]:
        for line in _wrap(d, f"{sp.capitalize()}: {en}", _font(30, bold=False), W - 96):
            if y > H - 150:
                break
            d.text((48, y), line, font=_font(30, bold=False), fill=MUTED)
            y += 42

    # 보상 스탬프
    d.ellipse((W - 250, H - 250, W - 50, H - 50), fill=SUN, outline="white", width=8)
    d.text((W - 150, H - 165), "★", font=_font(64), fill="#3a2a00", anchor="mm")
    d.text((W - 150, H - 105), "+100P", font=_font(36), fill="#3a2a00", anchor="mm")
    d.text((48, H - 70), "Oh! My Speaking 교재와 함께하는 Oh! My Story", font=_font(26, bold=False), fill=MUTED)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
