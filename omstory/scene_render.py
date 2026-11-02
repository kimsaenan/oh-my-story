"""
scene_render.py — 살아 있는 장면: 매 페이지 배경 + 캐릭터 + 지금까지 모은 스티커(+ 마법 상자)를 한 장으로 합친다.

- 그림은 모두 미리 그린 것(assets/)만 쓴다. AI 그림 생성 없음.
- 그림이 없는 상상(예: crab family)은 '마법 상자'로 장면에 들어간다.
"""
from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw

from .card import _font, find_sticker

ASSETS = Path(__file__).resolve().parent.parent / "assets"
W, H = 1200, 720


@lru_cache(maxsize=32)
def _bg(scene: str) -> Image.Image:
    p = ASSETS / "backgrounds" / f"{scene}.png"
    if not p.exists():
        p = ASSETS / "backgrounds" / "park.png"
    b = Image.open(p).convert("RGB")
    scale = max(W / b.width, H / b.height)
    b = b.resize((int(b.width * scale), int(b.height * scale)), Image.LANCZOS)
    x = (b.width - W) // 2
    return b.crop((x, b.height - H, x + W, b.height))


@lru_cache(maxsize=16)
def _char(name: str, height: int) -> Image.Image | None:
    p = ASSETS / "characters" / f"{name}.png"
    if not p.exists():
        return None
    im = Image.open(p).convert("RGBA")
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    return im.resize((max(1, int(im.width * height / im.height)), height), Image.LANCZOS)


@lru_cache(maxsize=64)
def _sticker_img(path: str, size: int) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    s = size / max(im.size)
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)


def _magic_box(label: str, size: int = 170) -> Image.Image:
    lf = _font(26)
    tw = int(ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(label, font=lf))
    cw = max(size, tw + 30)
    img = Image.new("RGBA", (cw, size + 50), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x0 = (cw - size) // 2
    d.rounded_rectangle((x0, 0, x0 + size, size), 34, fill=(106, 75, 214, 190), outline="white", width=7)
    c, r = (x0 + size / 2, size / 2), size * 0.28
    import math
    pts = [(c[0] + (r if k % 2 == 0 else r * .45) * math.cos(-math.pi / 2 + k * math.pi / 5),
            c[1] + (r if k % 2 == 0 else r * .45) * math.sin(-math.pi / 2 + k * math.pi / 5)) for k in range(10)]
    d.polygon(pts, fill=(255, 211, 78, 255))
    d.rounded_rectangle((cw / 2 - tw / 2 - 12, size + 6, cw / 2 + tw / 2 + 12, size + 46), 12, fill="white")
    d.text((cw / 2, size + 26), label, font=lf, fill=(30, 42, 74), anchor="mm")
    return img


def render_scene(scene: str, characters: list[str], stickers: list[str], magic: str | None = None,
                 fmt: str = "JPEG") -> bytes:
    """characters: 앞에 오는 캐릭터가 크게. stickers: 단어(스티커 파일을 찾음), 최근 것이 오른쪽."""
    img = _bg(scene or "park").copy()
    x = 40
    for k, name in enumerate(characters[:2]):
        ch = _char(name, int(H * (0.62 if k == 0 else 0.5)))
        if ch:
            img.paste(ch, (x, H - ch.height - 24), ch)
            x += int(ch.width * 0.82)
    items = [s for s in stickers if find_sticker(s)][-3:]
    tiles = [_sticker_img(str(find_sticker(s)), 190) for s in items]
    if magic:
        tiles.append(_magic_box(magic))
    rx = W - 30
    for t in reversed(tiles):
        rx -= t.width
        if rx < x - 40:
            break
        img.paste(t, (rx, H - t.height - 34), t)
        rx -= 18
    buf = io.BytesIO()
    if fmt == "JPEG":
        img.convert("RGB").save(buf, format="JPEG", quality=86)
    else:
        img.save(buf, format="PNG")
    return buf.getvalue()
