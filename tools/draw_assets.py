"""
draw_assets.py — 교재 그림체(부드러운 파스텔 + 갈색 손그림 선)에 맞춘 자리표시용 배경·소품 생성기

실행: python tools/draw_assets.py
결과: assets/backgrounds/<scene>.png, assets/stickers/<단어>.png

실제 서비스에서는 교재 Vocabulary 원화나 디자이너가 그린 그림으로 같은 이름의 파일을 교체하면 된다.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
STK = ROOT / "assets" / "stickers"
BG = ROOT / "assets" / "backgrounds"
OUT = (88, 66, 56, 255)          # 갈색 손그림 선
K = 3                            # 3배로 그린 뒤 줄여서 부드럽게


class Pen:
    def __init__(self, w: int = 400, h: int = 400, seed: int = 1, bg=(0, 0, 0, 0)):
        self.w, self.h = w, h
        self.img = Image.new("RGBA", (w * K, h * K), bg)
        self.d = ImageDraw.Draw(self.img)
        self.r = random.Random(seed)

    def _j(self, pts, amt=1.2, step=14):
        """선을 잘게 나누고 살짝 흔들어 손으로 그린 느낌을 낸다."""
        out = []
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
            for i in range(n):
                t = i / n
                out.append(((x0 + (x1 - x0) * t + self.r.uniform(-amt, amt)) * K,
                            (y0 + (y1 - y0) * t + self.r.uniform(-amt, amt)) * K))
        return out

    def poly(self, pts, fill, line=True, lw=2.2):
        self.d.polygon([(x * K, y * K) for x, y in pts], fill=fill)
        if line:
            j = self._j(list(pts))
            self.d.line(j + j[:1], fill=OUT, width=int(lw * K), joint="curve")

    def rect(self, x0, y0, x1, y1, fill, r=0, line=True, lw=2.2):
        if r:
            self.d.rounded_rectangle((x0 * K, y0 * K, x1 * K, y1 * K), r * K, fill=fill)
            if line:
                self.d.rounded_rectangle((x0 * K, y0 * K, x1 * K, y1 * K), r * K, outline=OUT, width=int(lw * K))
        else:
            self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill, line, lw)

    def oval(self, x0, y0, x1, y1, fill, line=True, lw=2.2):
        self.d.ellipse((x0 * K, y0 * K, x1 * K, y1 * K), fill=fill)
        if line:
            cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
            pts = [(cx + rx * math.cos(a), cy + ry * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 40, endpoint=False)]
            j = self._j(pts, step=999)
            self.d.line(j + j[:1], fill=OUT, width=int(lw * K), joint="curve")

    def line(self, pts, fill=OUT, lw=2.2):
        self.d.line([(x * K, y * K) for x, y in pts], fill=fill, width=int(lw * K), joint="curve")

    def done(self, path: Path, grain=True):
        img = self.img.resize((self.w, self.h), Image.LANCZOS)
        if grain:  # 종이 질감
            a = np.asarray(img).astype(np.int16)
            noise = np.random.default_rng(7).normal(0, 6, a.shape[:2])[..., None]
            a[..., :3] = np.clip(a[..., :3] + noise, 0, 255)
            img = Image.fromarray(a.astype(np.uint8), "RGBA")
        if img.getbbox() and self.img.mode == "RGBA" and img.getpixel((0, 0))[3] == 0:
            img = img.crop(img.getbbox())
            s = max(img.size) + 16
            can = Image.new("RGBA", (s, s), (0, 0, 0, 0))
            can.paste(img, ((s - img.width) // 2, (s - img.height) // 2), img)
            img = can
        path.parent.mkdir(parents=True, exist_ok=True)
        if not grain:  # 배경은 색 수를 줄여 파일 크기를 작게
            img = img.convert("RGB").quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        img.save(path, optimize=True)


def shade(c, f=0.85):
    return tuple(int(v * f) for v in c[:3]) + (255,)


# ---------------- 소품 (Unit 01 교실 물건) ----------------
def backpack(p):
    c = (232, 136, 72, 255)
    p.rect(110, 120, 290, 340, c, r=50)
    p.rect(140, 90, 260, 140, shade(c), r=30)
    p.rect(140, 220, 260, 310, shade(c, .9), r=20)
    p.line([(150, 250), (250, 250)])
    p.rect(185, 200, 215, 232, (250, 214, 120, 255), r=6)


def toy_robot(p):
    c = (226, 90, 80, 255)
    p.line([(200, 70), (200, 100)]); p.oval(188, 56, 212, 80, (255, 201, 60, 255))
    p.rect(140, 100, 260, 190, c, r=18)
    p.oval(160, 125, 190, 155, "white"); p.oval(210, 125, 240, 155, "white")
    p.oval(170, 133, 182, 147, OUT); p.oval(220, 133, 232, 147, OUT)
    p.rect(130, 200, 270, 300, (120, 160, 220, 255), r=16)
    p.rect(180, 225, 220, 265, (255, 201, 60, 255), r=6)
    p.rect(100, 210, 128, 280, c, r=12); p.rect(272, 210, 300, 280, c, r=12)
    p.rect(150, 300, 190, 345, c, r=10); p.rect(210, 300, 250, 345, c, r=10)


def desk(p):
    wood = (196, 140, 92, 255)
    p.rect(70, 150, 330, 185, wood, r=6)
    p.rect(90, 185, 110, 330, shade(wood)); p.rect(290, 185, 310, 330, shade(wood))
    p.rect(180, 185, 300, 240, shade(wood, .92)); p.oval(232, 205, 248, 220, (250, 214, 120, 255))


def book(p):
    p.poly([(110, 110), (290, 90), (300, 300), (120, 320)], (90, 130, 210, 255))
    p.poly([(120, 320), (300, 300), (302, 315), (124, 335)], (245, 240, 225, 255))
    p.line([(140, 112), (150, 318)], fill=(60, 95, 170, 255), lw=4)
    p.rect(170, 150, 260, 180, (245, 240, 225, 255), r=4)


def chair(p):
    c = (255, 196, 70, 255)
    p.rect(120, 90, 280, 210, c, r=40)
    p.rect(110, 210, 290, 245, shade(c), r=14)
    for x0, x1 in ((125, 150), (250, 275)):
        p.poly([(x0, 245), (x0 + 15, 245), (x0 - 5, 340), (x0 - 20, 340)], (190, 140, 90, 255))
    p.poly([(185, 245), (215, 245), (212, 330), (188, 330)], (190, 140, 90, 255))


def board(p):
    p.rect(60, 90, 340, 280, (200, 160, 110, 255), r=10)
    p.rect(78, 106, 322, 264, (250, 250, 245, 255), r=4)
    p.line([(100, 140), (220, 140)], fill=(110, 160, 220, 255), lw=4)
    p.line([(100, 170), (260, 170)], fill=(240, 120, 120, 255), lw=4)
    p.rect(150, 280, 250, 292, (200, 160, 110, 255))
    p.line([(140, 292), (120, 340)]); p.line([(260, 292), (280, 340)])


def clock(p):
    p.oval(90, 90, 310, 310, (120, 190, 220, 255))
    p.oval(112, 112, 288, 288, (255, 252, 240, 255))
    for i in range(12):
        a = i / 12 * 2 * math.pi
        p.line([(200 + 72 * math.sin(a), 200 - 72 * math.cos(a)), (200 + 80 * math.sin(a), 200 - 80 * math.cos(a))], lw=3)
    p.line([(200, 200), (200, 140)], lw=4); p.line([(200, 200), (245, 215)], lw=4)
    p.oval(192, 192, 208, 208, (240, 110, 110, 255))


def crayon(p):
    c = (90, 150, 230, 255)
    p.poly([(150, 120), (250, 120), (250, 300), (150, 300)], c)
    p.poly([(150, 120), (200, 50), (250, 120)], shade(c, .8))
    p.rect(150, 160, 250, 185, (255, 255, 255, 220), line=False)
    p.rect(150, 240, 250, 265, (255, 255, 255, 220), line=False)


def notebook(p):
    c = (230, 92, 92, 255)
    p.rect(120, 80, 290, 320, c, r=10)
    for y in range(100, 310, 22):
        p.oval(108, y, 128, y + 12, (220, 220, 220, 255))
    p.rect(160, 120, 260, 150, (255, 245, 225, 255), r=4)


def pencil(p):
    p.poly([(120, 290), (270, 110), (300, 135), (150, 315)], (255, 200, 70, 255))
    p.poly([(120, 290), (150, 315), (100, 340)], (245, 214, 170, 255))
    p.poly([(100, 340), (112, 326), (114, 334)], OUT, line=False)
    p.poly([(270, 110), (300, 135), (312, 120), (284, 95)], (240, 140, 160, 255))


def ruler(p):
    p.poly([(80, 230), (300, 90), (330, 135), (110, 275)], (255, 224, 130, 255))
    for i in range(1, 10):
        t = i / 10
        x, y = 80 + 220 * t, 230 - 140 * t
        L = 24 if i % 5 == 0 else 14
        p.line([(x + 2, y + 2), (x + 2 + L * .55, y + 2 + L * .85)], lw=2)


def present(p):
    p.rect(110, 170, 290, 330, (240, 110, 130, 255), r=8)
    p.rect(95, 140, 305, 180, (250, 140, 160, 255), r=8)
    p.rect(185, 140, 215, 330, (255, 214, 90, 255))
    p.oval(140, 95, 200, 145, (255, 214, 90, 255)); p.oval(200, 95, 260, 145, (255, 214, 90, 255))


# ---------------- 소품 (Unit 08 방 물건) ----------------
def table(p):
    wood = (196, 140, 92, 255)
    p.oval(70, 150, 330, 210, wood)
    p.rect(185, 195, 215, 320, shade(wood)); p.oval(140, 310, 260, 340, shade(wood))


def sofa(p):
    c = (110, 170, 200, 255)
    p.rect(90, 120, 310, 230, c, r=30)
    p.rect(60, 180, 110, 300, shade(c), r=20); p.rect(290, 180, 340, 300, shade(c), r=20)
    p.rect(100, 220, 300, 290, shade(c, .92), r=14)
    p.rect(80, 300, 100, 330, (150, 110, 80, 255)); p.rect(300, 300, 320, 330, (150, 110, 80, 255))


def lamp(p):
    p.poly([(140, 90), (260, 90), (300, 190), (100, 190)], (255, 214, 120, 255))
    p.rect(192, 190, 208, 320, (150, 110, 80, 255))
    p.oval(140, 310, 260, 345, (150, 110, 80, 255))


def rug(p):
    p.oval(60, 140, 340, 280, (240, 150, 140, 255))
    p.oval(100, 165, 300, 255, (250, 205, 160, 255))
    p.oval(150, 190, 250, 230, (240, 150, 140, 255))


def bed(p):
    p.rect(60, 120, 100, 320, (190, 140, 100, 255), r=8)
    p.rect(90, 200, 340, 290, (150, 190, 230, 255), r=14)
    p.rect(100, 170, 170, 210, (255, 255, 250, 255), r=14)
    p.rect(170, 190, 340, 240, (255, 200, 120, 255), r=10)
    p.rect(320, 230, 345, 320, (190, 140, 100, 255), r=8)


def bookshelf(p):
    wood = (196, 140, 92, 255)
    p.rect(100, 60, 300, 340, wood, r=6)
    cols = [(230, 110, 110, 255), (110, 160, 220, 255), (120, 190, 120, 255), (255, 200, 80, 255), (180, 130, 210, 255)]
    for row, y in enumerate((80, 170, 260)):
        p.rect(115, y, 285, y + 75, shade(wood, .75), line=False)
        x = 122
        for i in range(6):
            w = 18 + (i * 7 + row * 5) % 12
            p.rect(x, y + 12 + (i % 2) * 6, x + w, y + 75, cols[(i + row) % 5], lw=1.6)
            x += w + 4


def closet(p):
    c = (210, 170, 130, 255)
    p.rect(100, 60, 300, 340, c, r=8)
    p.line([(200, 70), (200, 330)])
    p.oval(180, 190, 192, 202, OUT); p.oval(208, 190, 220, 202, OUT)


def mirror(p):
    p.oval(130, 70, 270, 300, (220, 180, 120, 255))
    p.oval(145, 85, 255, 285, (215, 238, 248, 255))
    p.line([(170, 130), (200, 110)], fill=(255, 255, 255, 255), lw=5)
    p.rect(185, 300, 215, 340, (220, 180, 120, 255))


def picture(p):
    p.rect(90, 100, 310, 280, (200, 150, 100, 255), r=6)
    p.rect(110, 120, 290, 260, (205, 235, 250, 255))
    p.poly([(110, 260), (170, 180), (220, 240), (250, 200), (290, 260)], (130, 200, 120, 255), lw=1.8)
    p.oval(240, 135, 270, 165, (255, 214, 90, 255), lw=1.8)


def curtains(p):
    p.rect(70, 80, 330, 96, (190, 140, 100, 255), r=6)
    for x0, x1 in ((80, 190), (210, 320)):
        p.poly([(x0, 96), (x1, 96), (x1 - 10, 330), (x0 + 10, 330)], (240, 160, 170, 255))
        for k in range(1, 4):
            x = x0 + (x1 - x0) * k / 4
            p.line([(x, 110), (x, 320)], fill=(210, 120, 135, 255), lw=2)


def alarm_clock(p):
    p.oval(110, 70, 170, 130, (240, 110, 110, 255)); p.oval(230, 70, 290, 130, (240, 110, 110, 255))
    p.oval(100, 100, 300, 300, (240, 110, 110, 255))
    p.oval(125, 125, 275, 275, (255, 252, 240, 255))
    p.line([(200, 200), (200, 150)], lw=4); p.line([(200, 200), (240, 215)], lw=4)
    p.line([(140, 290), (120, 330)], lw=5); p.line([(260, 290), (280, 330)], lw=5)


# ---------------- 아이 상상에 자주 나올 만한 것 ----------------
def teddy_bear(p):
    c = (196, 140, 92, 255)
    p.oval(120, 70, 170, 120, c); p.oval(230, 70, 280, 120, c)
    p.oval(130, 80, 270, 210, c)
    p.oval(175, 150, 225, 195, (240, 214, 180, 255))
    p.oval(160, 125, 176, 141, OUT); p.oval(224, 125, 240, 141, OUT); p.oval(192, 158, 208, 170, OUT)
    p.oval(120, 190, 280, 330, c)
    p.oval(160, 230, 240, 310, (240, 214, 180, 255))


def baby_dragon(p):
    c = (120, 200, 140, 255)
    p.poly([(250, 260), (330, 230), (300, 290)], c)
    p.poly([(150, 160), (110, 100), (180, 140)], (255, 200, 120, 255))
    p.poly([(250, 160), (290, 100), (220, 140)], (255, 200, 120, 255))
    p.oval(120, 190, 280, 330, c)
    p.poly([(272, 235), (328, 200), (316, 270)], (255, 200, 120, 255))
    p.oval(130, 110, 270, 230, c)
    p.oval(165, 150, 185, 172, OUT); p.oval(215, 150, 235, 172, OUT)
    p.oval(160, 240, 240, 310, (240, 230, 170, 255))
    p.poly([(128, 235), (72, 200), (84, 270)], (255, 200, 120, 255))


def ball(p):
    p.oval(100, 100, 300, 300, (240, 110, 110, 255))
    p.d.arc((60 * K, 130 * K, 240 * K, 330 * K), 280, 60, fill=(255, 245, 235, 255), width=int(14 * K))
    p.d.arc((160 * K, 70 * K, 340 * K, 270 * K), 100, 240, fill=(255, 245, 235, 255), width=int(14 * K))
    p.d.ellipse((100 * K, 100 * K, 300 * K, 300 * K), outline=OUT, width=int(2.2 * K))


def star(p):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = 120 if i % 2 == 0 else 52
        pts.append((200 + r * math.cos(a), 205 + r * math.sin(a)))
    p.poly(pts, (255, 210, 80, 255))


def rocket(p):
    p.poly([(160, 140), (200, 60), (240, 140)], (240, 110, 110, 255))
    p.rect(160, 140, 240, 290, (245, 245, 250, 255), r=12)
    p.oval(182, 170, 218, 206, (120, 190, 240, 255))
    p.poly([(160, 250), (120, 320), (160, 295)], (240, 110, 110, 255)); p.poly([(240, 250), (280, 320), (240, 295)], (240, 110, 110, 255))
    p.poly([(175, 290), (200, 350), (225, 290)], (255, 200, 90, 255))


def fish(p):
    c = (255, 170, 90, 255)
    p.poly([(110, 200), (60, 140), (60, 260)], c)
    p.oval(100, 130, 320, 270, c)
    p.poly([(190, 140), (230, 95), (250, 145)], shade(c, .9))
    p.oval(255, 175, 275, 195, OUT)
    p.line([(170, 160), (180, 240)], fill=shade(c, .85), lw=4)


def moon(p):
    p.oval(90, 90, 310, 310, (255, 230, 140, 255))
    p.oval(140, 140, 180, 180, (240, 210, 120, 255), lw=1.6); p.oval(220, 200, 270, 250, (240, 210, 120, 255), lw=1.6)
    p.oval(180, 240, 205, 265, (240, 210, 120, 255), lw=1.6)


def cake(p):
    p.rect(100, 200, 300, 320, (250, 200, 150, 255), r=10)
    p.rect(100, 180, 300, 230, (255, 160, 190, 255), r=14)
    for x in (140, 200, 260):
        p.rect(x - 8, 120, x + 8, 180, (120, 180, 240, 255), r=4)
        p.oval(x - 9, 98, x + 9, 124, (255, 200, 80, 255), lw=1.6)


def mushroom(p):
    p.rect(165, 200, 235, 320, (250, 240, 225, 255), r=14)
    p.d.pieslice((90 * K, 90 * K, 310 * K, 290 * K), 180, 360, fill=(230, 90, 90, 255), outline=OUT, width=int(2.2 * K))
    for x, y in ((150, 160), (200, 125), (250, 160)):
        p.oval(x - 14, y - 14, x + 14, y + 14, (255, 255, 255, 255), line=False)


def snowman(p):
    p.oval(140, 70, 260, 180, (255, 255, 255, 255)); p.oval(110, 160, 290, 330, (255, 255, 255, 255))
    p.oval(172, 108, 186, 122, OUT); p.oval(214, 108, 228, 122, OUT)
    p.poly([(200, 130), (245, 140), (200, 148)], (255, 160, 80, 255))
    p.rect(120, 168, 280, 188, (240, 110, 110, 255), r=8, lw=1.6)


PROPS = {
    "backpack": backpack, "robot": toy_robot, "desk": desk, "book": book, "chair": chair, "board": board,
    "clock": clock, "crayon": crayon, "notebook": notebook, "pencil": pencil, "ruler": ruler, "present": present,
    "table": table, "sofa": sofa, "lamp": lamp, "rug": rug, "bed": bed, "bookshelf": bookshelf, "closet": closet,
    "mirrors": mirror, "pictures": picture, "curtains": curtains, "alarm_clock": alarm_clock,
    "teddy_bear": teddy_bear, "baby_dragon": baby_dragon, "dragon": baby_dragon, "ball": ball, "star": star,
    "rocket": rocket, "fish": fish, "moon": moon, "cake": cake, "mushroom": mushroom, "snowman": snowman,
}


# ---------------- 6권 Unit 01 계절 활동 소품 ----------------
def swim_ring(p):
    p.oval(90, 90, 310, 310, (240, 100, 100, 255)); p.oval(155, 155, 245, 245, (0, 0, 0, 0))
    for a0 in (20, 110, 200, 290):
        p.d.pieslice((90 * K, 90 * K, 310 * K, 310 * K), a0, a0 + 45, fill=(255, 250, 245, 255))
    p.d.ellipse((155 * K, 155 * K, 245 * K, 245 * K), fill=(0, 0, 0, 0), outline=OUT, width=int(2.2 * K))
    p.d.ellipse((90 * K, 90 * K, 310 * K, 310 * K), outline=OUT, width=int(2.2 * K))


def surfboard(p):
    pts = [(200 + 70 * math.cos(a) * (1 - .25 * abs(math.sin(a))), 200 + 165 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 40, endpoint=False)]
    rot = lambda x, y: (200 + (x - 200) * math.cos(.5) - (y - 200) * math.sin(.5), 200 + (x - 200) * math.sin(.5) + (y - 200) * math.cos(.5))
    p.poly([rot(x, y) for x, y in pts], (90, 190, 230, 255))
    p.line([rot(200, 50), rot(200, 350)], fill=(255, 250, 240, 255), lw=8)


def sunglasses_sun(p):
    for i in range(12):
        a = i * math.pi / 6
        p.line([(200 + 115 * math.cos(a), 200 + 115 * math.sin(a)), (200 + 160 * math.cos(a), 200 + 160 * math.sin(a))], fill=(255, 180, 60, 255), lw=8)
    p.oval(90, 90, 310, 310, (255, 214, 90, 255))
    p.rect(115, 160, 190, 215, (60, 70, 100, 255), r=20); p.rect(210, 160, 285, 215, (60, 70, 100, 255), r=20)
    p.line([(190, 180), (210, 180)], lw=5)
    p.d.arc((150 * K, 200 * K, 250 * K, 270 * K), 20, 160, fill=OUT, width=int(4 * K))


def flippers(p):
    for x, ang in ((140, -0.15), (260, 0.15)):
        pts = [(x - 30, 110), (x + 30, 110), (x + 65, 320), (x - 65, 320)]
        p.poly([(x + (px - x) * math.cos(ang) - (py - 215) * math.sin(ang), 215 + (px - x) * math.sin(ang) + (py - 215) * math.cos(ang)) for px, py in pts], (255, 200, 60, 255))
        p.rect(x - 32, 95, x + 32, 150, (70, 120, 200, 255), r=18)
    for bx, by, r in ((320, 90, 16), (345, 55, 10), (300, 50, 8)):
        p.oval(bx - r, by - r, bx + r, by + r, (220, 240, 255, 255), lw=1.6)


def snorkel_mask(p):
    p.rect(300, 60, 325, 260, (255, 160, 60, 255), r=10)
    p.rect(250, 50, 340, 80, (255, 160, 60, 255), r=12)
    p.rect(70, 140, 320, 175, (60, 70, 100, 255), r=16)
    p.rect(90, 110, 300, 250, (120, 200, 240, 255), r=46)
    p.rect(110, 130, 280, 230, (200, 236, 255, 255), r=34)
    p.line([(130, 150), (160, 190)], fill=(255, 255, 255, 255), lw=6)


def sandcastle(p):
    sand, dark = (238, 200, 130, 255), (215, 172, 104, 255)
    p.rect(80, 220, 320, 330, sand, r=8)
    p.rect(150, 140, 250, 225, sand)
    for x0 in (80, 280):
        p.rect(x0, 160, x0 + 40, 225, dark)
    for x in range(150, 250, 25):
        p.rect(x, 120, x + 15, 142, sand, lw=1.6)
    p.rect(185, 265, 215, 330, dark, r=14)
    p.line([(200, 140), (200, 70)], lw=3); p.poly([(200, 70), (245, 85), (200, 100)], (240, 100, 100, 255))


def seashell(p):
    c = (255, 190, 200, 255)
    pts = [(200, 330)] + [(200 + 150 * math.cos(a), 300 - 190 * math.sin(a) * .95) for a in np.linspace(0.15, math.pi - 0.15, 22)]
    p.poly(pts, c)
    for a in np.linspace(0.45, math.pi - 0.45, 6):
        p.line([(200, 325), (200 + 140 * math.cos(a), 300 - 180 * math.sin(a))], fill=shade(c, .82), lw=4)
    p.rect(165, 310, 235, 345, shade(c, .9), r=12)


def volleyball(p):
    p.oval(100, 100, 300, 300, (255, 255, 255, 255))
    p.d.pieslice((100 * K, 100 * K, 300 * K, 300 * K), 200, 300, fill=(255, 210, 70, 255))
    p.d.pieslice((100 * K, 100 * K, 300 * K, 300 * K), 20, 120, fill=(90, 160, 230, 255))
    for box, a, b in (((40, 60, 260, 280), 300, 30), ((140, 120, 360, 340), 120, 210)):
        p.d.arc(tuple(v * K for v in box), a, b, fill=OUT, width=int(2.4 * K))
    p.d.ellipse((100 * K, 100 * K, 300 * K, 300 * K), outline=OUT, width=int(2.2 * K))


def snowball(p):
    p.oval(70, 260, 330, 330, (235, 245, 255, 255))
    for x, y, r in ((150, 230, 60), (250, 245, 50), (205, 175, 55)):
        p.oval(x - r, y - r, x + r, y + r, (255, 255, 255, 255))
        p.oval(x - r * .5, y - r * .6, x - r * .2, y - r * .3, (220, 235, 250, 255), line=False)


def snow_angel(p):
    snow, sh = (255, 255, 255, 255), (200, 222, 245, 255)
    p.oval(40, 60, 360, 350, (230, 242, 255, 255))
    p.oval(170, 85, 230, 145, sh)
    p.poly([(200, 145), (90, 120), (70, 190), (150, 205), (130, 320), (200, 300), (270, 320), (250, 205), (330, 190), (310, 120)], sh)
    p.oval(185, 98, 215, 128, snow, line=False)


def skis(p):
    for ang, col in ((-0.35, (240, 100, 100, 255)), (0.35, (90, 160, 230, 255))):
        c, s = math.cos(ang), math.sin(ang)
        R = lambda x, y: (200 + (x - 200) * c - (y - 200) * s, 200 + (x - 200) * s + (y - 200) * c)
        p.poly([R(185, 60), R(215, 60), R(215, 345), R(185, 345)], col)
        p.poly([R(185, 60), R(215, 60), R(200, 35)], col)
        p.rect(*R(178, 200), *R(222, 222), (60, 70, 100, 255), r=4) if False else None
    for x in (110, 290):
        p.line([(x, 70), (x + (200 - x) * .25, 330)], fill=(120, 120, 130, 255), lw=5)
        p.oval(x - 6, 60, x + 6, 80, (255, 200, 60, 255), lw=1.4)


def snowboard(p):
    c, s = math.cos(.6), math.sin(.6)
    R = lambda x, y: (200 + (x - 200) * c - (y - 200) * s, 200 + (x - 200) * s + (y - 200) * c)
    pts = [R(200 + 60 * math.cos(a), 200 + 170 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 40, endpoint=False)]
    p.poly([(x, y) for x, y in pts], (150, 110, 220, 255))
    for y in (140, 260):
        a, b = R(160, y), R(240, y)
        p.line([a, b], fill=(60, 70, 100, 255), lw=12)
    p.line([R(200, 40), R(200, 360)], fill=(255, 210, 80, 255), lw=6)


def ice_skate(p):
    boot = (255, 255, 255, 255)
    p.poly([(130, 80), (220, 80), (225, 220), (320, 240), (320, 290), (120, 290)], boot)
    for y in (110, 140, 170, 200):
        p.line([(180, y), (215, y + 6)], fill=(240, 120, 140, 255), lw=4)
    p.rect(120, 290, 320, 305, (90, 100, 130, 255), r=4)
    p.line([(140, 305), (140, 325)], lw=4); p.line([(290, 305), (290, 325)], lw=4)
    p.d.arc((95 * K, 300 * K, 350 * K, 345 * K), 0, 180, fill=(170, 180, 200, 255), width=int(6 * K))
    p.line([(110, 330), (330, 330)], fill=(170, 180, 200, 255), lw=6)


PROPS.update({
    "swimming": swim_ring, "surfing": surfboard, "sunbathing": sunglasses_sun, "diving": flippers,
    "snorkeling": snorkel_mask, "sandcastle": sandcastle, "seashell": seashell, "volleyball": volleyball,
    "snowmen": snowman, "snowball": snowball, "snow_angel": snow_angel, "skiing": skis,
    "snowboarding": snowboard, "ice_skating": ice_skate,
})


# ---------------- 배경 (1600x900) ----------------
def background(scene: str) -> Pen:
    W, H = 1600, 900
    p = Pen(W, H, seed=hash(scene) % 1000, bg=(255, 255, 255, 255))
    L = lambda *a, **k: p.line(*a, **k)
    if scene in ("classroom", "toyroom", "home", "petshop", "room"):
        wall = {"classroom": (232, 242, 236), "toyroom": (252, 232, 238), "home": (255, 240, 214),
                "petshop": (226, 244, 236), "room": (236, 232, 252)}[scene] + (255,)
        floor = {"classroom": (232, 200, 150), "toyroom": (240, 205, 160), "home": (220, 180, 135),
                 "petshop": (236, 208, 160), "room": (226, 194, 150)}[scene] + (255,)
        p.rect(0, 0, W, 600, wall, line=False)
        p.rect(0, 600, W, H, floor, line=False)
        L([(0, 600), (W, 600)], lw=3)
        for x in range(0, W, 160):
            L([(x, 600), (x - 120, H)], fill=shade(floor, .9), lw=2)
        # 창문
        p.rect(1180, 110, 1460, 380, (200, 230, 248, 255), r=10)
        L([(1320, 110), (1320, 380)], lw=3); L([(1180, 245), (1460, 245)], lw=3)
        p.oval(1360, 140, 1420, 200, (255, 236, 150, 255), lw=1.8)
        if scene == "classroom":
            p.rect(300, 110, 900, 400, (110, 150, 120, 255), r=8)
            p.rect(290, 400, 910, 418, (200, 160, 110, 255))
            L([(360, 180), (560, 180)], fill=(250, 250, 240, 255), lw=4); L([(360, 230), (640, 230)], fill=(250, 250, 240, 255), lw=4)
            p.oval(980, 120, 1080, 220, (255, 252, 240, 255))
        elif scene == "toyroom":
            for y in (230, 380):
                p.rect(120, y, 620, y + 18, (200, 150, 110, 255))
            for i, x in enumerate(range(150, 600, 90)):
                col = [(240, 120, 120), (120, 170, 230), (255, 200, 90), (140, 200, 140), (190, 140, 220)][i % 5] + (255,)
                p.rect(x, 170, x + 60, 230, col, r=10)
                p.oval(x, 320, x + 60, 380, col)
        elif scene == "home":
            for i, x in enumerate((200, 420, 640)):
                p.rect(x, 150, x + 160, 300, (200, 150, 100, 255), r=6)
                p.rect(x + 16, 166, x + 144, 284, [(250, 225, 200), (215, 235, 250), (230, 245, 220)][i] + (255,))
                p.oval(x + 50, 190, x + 110, 250, [(240, 170, 140), (160, 190, 230), (160, 210, 150)][i] + (255,), lw=1.8)
        elif scene == "petshop":
            for y in (200, 380):
                p.rect(100, y, 800, y + 18, (200, 150, 110, 255))
            for x in range(140, 760, 160):
                p.rect(x, 250, x + 120, 380, (215, 238, 248, 180), r=10)
                p.oval(x + 30, 320, x + 90, 370, (255, 214, 140, 255), lw=1.6)
        elif scene == "room":
            for x in range(40, 1100, 120):
                L([(x, 0), (x, 600)], fill=shade(wall, .95), lw=6)
    else:
        sky = {"picnic": (205, 236, 252), "park": (200, 234, 250), "zoo": (212, 240, 250)}[scene] + (255,)
        p.rect(0, 0, W, H, sky, line=False)
        p.oval(1300, 70, 1460, 230, (255, 220, 110, 255))
        for cx, cy, s in ((260, 140, 1), (820, 100, .8), (1120, 220, .7)):
            for dx, dy, r in ((0, 0, 60), (70, -25, 75), (150, 0, 60)):
                p.oval(cx + dx * s - r * s, cy + dy * s - r * s, cx + dx * s + r * s, cy + dy * s + r * s, (255, 255, 255, 255), line=False)
        hill = (170, 215, 130, 255)
        p.poly([(0, 560), (300, 470), (650, 520), (1000, 450), (1350, 510), (W, 470), (W, H), (0, H)], hill)
        p.poly([(0, 640), (400, 600), (900, 650), (W, 610), (W, H), (0, H)], (150, 205, 110, 255))
        for x, s in ((120, 1), (1480, .9), (980, .7)):
            p.rect(x - 14 * s, 470 - 60 * s, x + 14 * s, 600 - 40 * s, (150, 110, 80, 255))
            p.oval(x - 90 * s, 300 - 60 * s, x + 90 * s, 470 - 50 * s, (110, 180, 100, 255))
        if scene == "picnic":
            p.poly([(520, 720), (1080, 720), (1180, 860), (420, 860)], (240, 130, 130, 255))
            for i in range(1, 6):
                L([(520 + 112 * i, 720), (420 + 152 * i, 860)], fill=(255, 245, 240, 255), lw=6)
        if scene == "park":
            p.rect(620, 560, 980, 590, (200, 150, 110, 255), r=6)
            p.rect(640, 590, 660, 650, (150, 110, 80, 255)); p.rect(940, 590, 960, 650, (150, 110, 80, 255))
        if scene == "zoo":
            for x in range(0, W, 70):
                p.rect(x, 520, x + 40, 640, (220, 180, 130, 255), r=6)
            p.rect(0, 550, W, 570, (190, 150, 110, 255), line=False)
    for _ in range(40):  # 꽃·점 장식
        x, y = p.r.uniform(30, W - 30), p.r.uniform(650, H - 20)
        p.oval(x - 4, y - 4, x + 4, y + 4, p.r.choice([(255, 255, 255, 200), (255, 214, 120, 200), (255, 170, 180, 200)]), line=False)
    return p


def _clouds(p, items, col=(255, 255, 255, 255), line=False):
    for cx, cy, s in items:
        for dx, dy, r in ((0, 0, 60), (70, -25, 75), (150, 0, 60)):
            p.oval(cx + dx * s - r * s, cy + dy * s - r * s, cx + dx * s + r * s, cy + dy * s + r * s, col, line=line)


def _tree(p, x, y, s=1.0, leaf=(110, 180, 100, 255)):
    p.rect(x - 14 * s, y - 60 * s, x + 14 * s, y + 70 * s, (150, 110, 80, 255))
    p.oval(x - 90 * s, y - 230 * s, x + 90 * s, y - 50 * s, leaf)


def _pine(p, x, y, s=1.0, snow=False):
    p.rect(x - 12 * s, y - 20 * s, x + 12 * s, y + 40 * s, (150, 110, 80, 255))
    for k in range(3):
        top = y - 220 * s + k * 60 * s
        p.poly([(x, top), (x - (70 + k * 25) * s, top + 110 * s), (x + (70 + k * 25) * s, top + 110 * s)], (90, 160, 110, 255))
        if snow:
            p.poly([(x, top), (x - 30 * s, top + 45 * s), (x + 30 * s, top + 45 * s)], (255, 255, 255, 255), lw=1.6)


def fantasy_background(scene: str) -> Pen:
    """아이 상상용 배경: 우주, 바닷속, 사탕 나라, 바닷가, 성, 숲, 눈 나라, 구름 위."""
    W, H = 1600, 900
    p = Pen(W, H, seed=sum(map(ord, scene)), bg=(255, 255, 255, 255))
    r = p.r
    if scene == "space":
        p.rect(0, 0, W, H, (44, 48, 98, 255), line=False)
        for _ in range(120):
            x, y, s = r.uniform(0, W), r.uniform(0, 640), r.choice((2, 3, 4, 6))
            p.oval(x - s, y - s, x + s, y + s, r.choice([(255, 255, 255, 255), (255, 230, 150, 255), (200, 210, 255, 255)]), line=False)
        p.oval(1160, 90, 1400, 330, (240, 160, 120, 255))
        p.d.arc((1080 * K, 170 * K, 1480 * K, 250 * K), 160, 380, fill=(255, 214, 140, 255), width=int(10 * K))
        p.oval(260, 120, 360, 220, (120, 190, 240, 255)); p.oval(285, 145, 330, 185, (130, 200, 120, 255), line=False)
        p.poly([(0, 640), (300, 600), (700, 630), (1100, 590), (W, 620), (W, H), (0, H)], (196, 196, 214, 255))
        for cx, cy, rx in ((300, 760, 90), (900, 700, 60), (1300, 800, 110), (650, 840, 50)):
            p.oval(cx - rx, cy - rx * .35, cx + rx, cy + rx * .35, (168, 168, 190, 255), lw=1.8)
        # 로켓
        p.poly([(760, 260), (800, 180), (840, 260)], (240, 110, 110, 255))
        p.rect(760, 260, 840, 420, (245, 245, 250, 255), r=12)
        p.oval(782, 290, 818, 326, (120, 190, 240, 255))
        p.poly([(760, 380), (725, 440), (760, 420)], (240, 110, 110, 255)); p.poly([(840, 380), (875, 440), (840, 420)], (240, 110, 110, 255))
        p.poly([(775, 420), (800, 480), (825, 420)], (255, 200, 90, 255))
    elif scene == "underwater":
        for i, c in enumerate([(150, 215, 240), (120, 195, 232), (95, 175, 222), (80, 160, 212)]):
            p.rect(0, i * 170, W, (i + 1) * 170 + 2, c + (255,), line=False)
        for _ in range(26):
            x, y, s = r.uniform(40, W - 40), r.uniform(40, 600), r.uniform(8, 22)
            p.oval(x - s, y - s, x + s, y + s, (255, 255, 255, 60), lw=1.6)
        p.poly([(0, 650), (400, 620), (900, 660), (W, 625), (W, H), (0, H)], (240, 220, 170, 255))
        for x in (120, 260, 1380, 1500, 980):
            pts = [(x + 18 * math.sin(t / 2), 660 - t * 22) for t in range(16)]
            p.line(pts, fill=(80, 170, 110, 255), lw=14)
        for x, y, c, d in ((450, 260, (255, 170, 90), 1), (1100, 180, (255, 120, 140), -1), (700, 420, (255, 214, 90), 1)):
            p.oval(x - 60, y - 34, x + 60, y + 34, c + (255,))
            tail = [(x - 60 * d, y), (x - 105 * d, y - 34), (x - 105 * d, y + 34)]
            p.poly(tail, c + (255,))
            p.oval(x + 28 * d - 7, y - 12, x + 28 * d + 7, y + 2, OUT)
        for x in (520, 1240):
            p.d.pieslice(((x - 40) * K, 700 * K, (x + 40) * K, 780 * K), 180, 360, fill=(250, 190, 200, 255), outline=OUT, width=int(2 * K))
    elif scene == "candy":
        p.rect(0, 0, W, H, (255, 222, 238, 255), line=False)
        _clouds(p, ((220, 140, 1), (1000, 110, .8)), (255, 245, 250, 255))
        for x, y, c in ((0, 600, (255, 170, 200)), (500, 560, (190, 160, 240)), (1050, 600, (160, 220, 200))):
            p.oval(x - 120, y - 140, x + 420, y + 200, c + (255,))
        p.rect(0, 640, W, H, (190, 130, 100, 255), line=False)
        p.line([(0, 640), (W, 640)], lw=3)
        for x in range(60, W, 140):
            p.oval(x - 10, 700 + (x % 3) * 40, x + 10, 720 + (x % 3) * 40, r.choice([(255, 255, 255, 255), (255, 214, 90, 255), (120, 200, 240, 255)]), line=False)
        for x, h, c in ((180, 300, (255, 120, 150)), (1420, 340, (120, 190, 240)), (1000, 260, (255, 200, 80))):
            p.rect(x - 8, 640 - h + 120, x + 8, 640, (255, 252, 245, 255))
            p.oval(x - 90, 640 - h - 60, x + 90, 640 - h + 120, c + (255,))
            p.d.arc(((x - 55) * K, (640 - h - 25) * K, (x + 55) * K, (640 - h + 85) * K), 0, 300, fill=(255, 255, 255, 255), width=int(9 * K))
    elif scene == "beach":
        p.rect(0, 0, W, 430, (200, 234, 252, 255), line=False)
        p.oval(1260, 70, 1420, 230, (255, 220, 110, 255))
        _clouds(p, ((240, 130, .9), (760, 90, .7)))
        p.rect(0, 430, W, 600, (90, 180, 225, 255), line=False)
        for x in range(40, W, 180):
            p.line([(x, 480 + (x % 2) * 40), (x + 70, 480 + (x % 2) * 40)], fill=(255, 255, 255, 230), lw=4)
        p.poly([(0, 590), (500, 570), (1000, 600), (W, 575), (W, H), (0, H)], (245, 222, 165, 255))
        p.line([(1380, 600), (1350, 300)], fill=(160, 115, 80, 255), lw=26)
        for a in (200, 240, 290, 330, 20):
            rad = math.radians(a)
            p.poly([(1350, 300), (1350 + 190 * math.cos(rad), 300 + 90 * math.sin(rad) + 40), (1350 + 150 * math.cos(rad), 300 + 70 * math.sin(rad) + 70)], (110, 180, 100, 255))
        p.line([(250, 820), (250, 560)], fill=(200, 150, 110, 255), lw=8)
        p.d.pieslice((120 * K, 470 * K, 380 * K, 650 * K), 180, 360, fill=(240, 110, 110, 255), outline=OUT, width=int(2 * K))
    elif scene == "castle":
        p.rect(0, 0, W, H, (205, 232, 252, 255), line=False)
        _clouds(p, ((200, 120, .9), (1250, 90, .8)))
        p.poly([(0, 580), (500, 500), (1000, 560), (W, 500), (W, H), (0, H)], (165, 212, 130, 255))
        cx = 1050
        p.rect(cx - 200, 260, cx + 200, 560, (236, 224, 248, 255))
        for tx in (cx - 250, cx + 170):
            p.rect(tx, 200, tx + 80, 560, (226, 212, 244, 255))
            p.poly([(tx - 15, 200), (tx + 40, 100), (tx + 95, 200)], (150, 120, 220, 255))
            p.line([(tx + 40, 100), (tx + 40, 60)], lw=3); p.poly([(tx + 40, 60), (tx + 80, 72), (tx + 40, 84)], (240, 110, 110, 255))
        p.rect(cx - 50, 160, cx + 50, 260, (226, 212, 244, 255))
        p.poly([(cx - 65, 160), (cx, 70), (cx + 65, 160)], (150, 120, 220, 255))
        p.d.pieslice(((cx - 60) * K, 430 * K, (cx + 60) * K, 550 * K), 180, 360, fill=(150, 110, 80, 255), outline=OUT, width=int(2 * K))
        p.rect(cx - 60, 490, cx + 60, 560, (150, 110, 80, 255))
        for wx in (cx - 140, cx + 100):
            p.rect(wx, 330, wx + 40, 390, (255, 236, 150, 255), r=18)
        p.poly([(cx - 60, 560), (cx + 60, 560), (cx + 200, H), (cx - 200, H)], (240, 224, 190, 255))
    elif scene == "forest":
        p.rect(0, 0, W, H, (214, 238, 214, 255), line=False)
        for x, s in ((80, 1.2), (330, .9), (1250, 1.1), (1500, 1.0), (620, .7), (950, .8)):
            _tree(p, x, 560, s, (90, 165, 95, 255) if x % 2 else (120, 185, 105, 255))
        p.rect(0, 620, W, H, (150, 200, 110, 255), line=False)
        p.line([(0, 620), (W, 620)], lw=2.5)
        for x, y, s in ((520, 760, 1), (1150, 720, .8), (820, 820, .6)):
            p.rect(x - 14 * s, y - 50 * s, x + 14 * s, y + 30 * s, (250, 240, 225, 255))
            p.d.pieslice(((x - 60 * s) * K, (y - 100 * s) * K, (x + 60 * s) * K, (y + 10 * s) * K), 180, 360, fill=(230, 90, 90, 255), outline=OUT, width=int(2 * K))
            for dx in (-25, 0, 25):
                p.oval(x + dx * s - 7, y - 75 * s - 7, x + dx * s + 7, y - 75 * s + 7, (255, 255, 255, 255), line=False)
    elif scene == "snow":
        p.rect(0, 0, W, H, (220, 236, 250, 255), line=False)
        p.poly([(0, 520), (400, 430), (800, 500), (1200, 420), (W, 480), (W, H), (0, H)], (245, 250, 255, 255))
        p.poly([(0, 650), (500, 610), (1000, 660), (W, 620), (W, H), (0, H)], (255, 255, 255, 255))
        for x, s in ((150, 1.1), (1450, 1.0), (1150, .7)):
            _pine(p, x, 560, s, snow=True)
        p.oval(860, 520, 1000, 640, (255, 255, 255, 255)); p.oval(830, 600, 1030, 780, (255, 255, 255, 255))
        p.oval(900, 560, 914, 574, OUT); p.oval(946, 560, 960, 574, OUT)
        p.poly([(930, 585), (975, 595), (930, 600)], (255, 160, 80, 255))
        p.rect(840, 640, 1020, 660, (240, 110, 110, 255), r=8, lw=1.6)
        for _ in range(90):
            x, y = r.uniform(0, W), r.uniform(0, H)
            p.oval(x - 4, y - 4, x + 4, y + 4, (255, 255, 255, 255), line=False)
    elif scene == "sky":
        p.rect(0, 0, W, H, (190, 225, 252, 255), line=False)
        rb = [(255, 120, 120), (255, 180, 100), (255, 230, 120), (140, 210, 140), (120, 180, 240), (180, 140, 220)]
        for i, c in enumerate(rb):
            p.d.arc(((300 + i * 22) * K, (120 + i * 22) * K, (1300 - i * 22) * K, (1000 - i * 22) * K), 180, 360, fill=c + (255,), width=int(20 * K))
        p.oval(1330, 60, 1470, 200, (255, 220, 110, 255))
        _clouds(p, ((150, 200, .8), (1150, 150, .7)))
        for x in range(-60, W + 100, 170):
            p.oval(x - 130, 600 - (x % 3) * 20, x + 130, 820, (255, 255, 255, 255))
        p.rect(0, 720, W, H, (255, 255, 255, 255), line=False)
    return p


FANTASY = ["space", "underwater", "candy", "beach", "castle", "forest", "snow", "sky"]
SCENES = ["classroom", "toyroom", "picnic", "park", "home", "zoo", "petshop", "room"]

if __name__ == "__main__":
    for name, fn in PROPS.items():
        pen = Pen(seed=len(name))
        fn(pen)
        pen.done(STK / f"{name}.png")
    for s in SCENES:
        background(s).done(BG / f"{s}.png", grain=False)
    for s in FANTASY:
        fantasy_background(s).done(BG / f"{s}.png", grain=False)
    print(f"소품 {len(PROPS)}개, 배경 {len(SCENES) + len(FANTASY)}개(단원 {len(SCENES)} + 상상 {len(FANTASY)}) 생성 → {STK.parent}")
