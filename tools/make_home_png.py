"""
make_home_png.py — Oh! My CEDU 첫 화면 한 장 목업 (옛 '동물농장' 지도형 UI 느낌)

구역: 파닉스 나라(Oh! My Phonics) · 말하기 나라(Oh! My Speaking + 그 안의 Oh! My Story) · 문법 나라(Oh! My Grammar)
- 교재 표지는 시리즈 간판으로 사용 (사용자 제공 이미지)
- Jack·Wacky·Amy·Tom·Mom은 Oh! My Speaking 캐릭터라 말하기 나라 구역에만 배치
실행: python tools/make_home_png.py <표지이미지폴더> <출력.png>
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from draw_assets import K, OUT, Pen, _clouds, _tree, shade  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
W, H = 1600, 1040
FONT_B = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_R = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
INK, BROWN = (60, 44, 36), (110, 80, 60)
C_PH, C_SP, C_GR, C_ST = (34, 150, 230), (245, 120, 40), (40, 160, 80), (130, 90, 230)


def font(sz, bold=True):
    return ImageFont.truetype(FONT_B if bold else FONT_R, sz)


def draw_map(p: Pen):
    # 하늘·바다·땅
    p.rect(0, 0, W, H, (190, 230, 252, 255), line=False)
    p.oval(1380, 40, 1530, 190, (255, 222, 110, 255))
    for a in range(0, 360, 30):
        r = math.radians(a)
        p.line([(1455 + 90 * math.cos(r), 115 + 90 * math.sin(r)), (1455 + 115 * math.cos(r), 115 + 115 * math.sin(r))], fill=(255, 200, 80, 255), lw=5)
    _clouds(p, ((140, 120, .8), (560, 80, .6), (1120, 120, .7)))
    land = [(20, 300), (240, 220), (560, 250), (820, 200), (1100, 240), (1380, 230), (1580, 300), (1590, 1020), (10, 1020)]
    p.poly([(x, y + 12) for x, y in land], (120, 190, 90, 255), line=False)
    p.poly(land, (160, 215, 110, 255))
    # 구역 바닥 (살짝 다른 초록)
    p.oval(40, 330, 560, 900, (172, 222, 122, 255), line=False)
    p.oval(1060, 330, 1580, 900, (150, 205, 105, 255), line=False)
    # 길
    path = [(280, 640), (520, 700), (800, 620), (1080, 700), (1320, 640)]
    p.line([(x, y) for x, y in path], fill=(245, 232, 190, 255), lw=34)
    p.line([(800, 620), (800, 900)], fill=(245, 232, 190, 255), lw=30)
    p.line([(800, 900), (420, 960), (300, 980)], fill=(245, 232, 190, 255), lw=26)
    p.line([(800, 900), (1180, 960), (1320, 980)], fill=(245, 232, 190, 255), lw=26)
    # 나무·꽃
    for x, y, s in ((90, 560, .5), (560, 480, .45), (1050, 480, .45), (1530, 560, .5), (640, 980, .4), (980, 990, .4), (60, 900, .45), (1540, 900, .45)):
        _tree(p, x, y, s)
    for i in range(70):
        x, y = 40 + (i * 137) % 1520, 320 + (i * 61) % 680
        p.oval(x - 4, y - 4, x + 4, y + 4, [(255, 255, 255, 230), (255, 214, 120, 230), (255, 160, 180, 230)][i % 3], line=False)
    # 떠 있는 작은 섬 (동물농장 느낌)
    p.poly([(70, 150), (230, 150), (150, 215)], (176, 140, 100, 255))
    p.oval(55, 125, 245, 170, (160, 215, 110, 255))
    _tree(p, 120, 135, .22); _tree(p, 180, 138, .18)


def phonics_zone(p: Pen):
    # ABC 블록 탑
    cols = [(240, 110, 110, 255), (90, 160, 230, 255), (255, 200, 70, 255), (110, 190, 120, 255), (190, 130, 220, 255)]
    blocks = [(130, 520), (200, 520), (270, 520), (165, 450), (235, 450), (200, 380)]
    for i, (x, y) in enumerate(blocks):
        p.rect(x, y, x + 70, y + 70, cols[i % 5], r=8)
    # 미끄럼틀
    p.rect(380, 420, 396, 600, (90, 160, 230, 255)); p.rect(440, 420, 456, 600, (90, 160, 230, 255))
    p.rect(372, 410, 464, 428, (255, 200, 70, 255), r=6)
    p.poly([(456, 440), (540, 590), (518, 600), (440, 470)], (240, 110, 110, 255))
    for y in (450, 490, 530, 570):
        p.line([(380, y), (456, y)], lw=2.5)
    # 음표 풍선
    for x, y, c in ((110, 360, cols[0]), (330, 330, cols[2]), (480, 360, cols[3])):
        p.oval(x - 26, y - 32, x + 26, y + 32, c)
        p.line([(x, y + 32), (x + 6, y + 90)], lw=2)


def speaking_zone(p: Pen):
    # 무대 건물
    x0, y0 = 640, 360
    p.rect(x0, y0 + 60, x0 + 320, y0 + 260, (255, 240, 220, 255))
    p.poly([(x0 - 20, y0 + 70), (x0 + 160, y0 - 30), (x0 + 340, y0 + 70)], (245, 120, 40, 255))
    p.rect(x0 + 40, y0 + 100, x0 + 280, y0 + 240, (60, 48, 90, 255), r=6)
    p.poly([(x0 + 40, y0 + 100), (x0 + 110, y0 + 100), (x0 + 90, y0 + 240), (x0 + 40, y0 + 240)], (150, 90, 210, 255))
    p.poly([(x0 + 280, y0 + 100), (x0 + 210, y0 + 100), (x0 + 230, y0 + 240), (x0 + 280, y0 + 240)], (150, 90, 210, 255))
    star = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = 34 if i % 2 == 0 else 15
        star.append((x0 + 160 + rr * math.cos(a), y0 + 160 + rr * math.sin(a)))
    p.poly(star, (255, 210, 80, 255))
    p.rect(x0 - 10, y0 + 250, x0 + 330, y0 + 272, (200, 150, 110, 255), r=6)


def story_house(p: Pen):
    # 이야기 숲: 펼친 책 지붕 집 (말하기 나라 안)
    x0, y0 = 690, 760
    p.rect(x0, y0, x0 + 200, y0 + 120, (236, 228, 255, 255))
    p.poly([(x0 - 20, y0 + 10), (x0 + 100, y0 - 60), (x0 + 100, y0 + 10)], (150, 110, 230, 255))
    p.poly([(x0 + 100, y0 - 60), (x0 + 220, y0 + 10), (x0 + 100, y0 + 10)], (180, 140, 245, 255))
    for k in range(3):
        p.line([(x0 + 10 + k * 24, y0 - 2 - k * 12), (x0 + 90, y0 - 40 + k * 14)], fill=(255, 255, 255, 200), lw=2)
    p.rect(x0 + 80, y0 + 50, x0 + 120, y0 + 120, (150, 110, 80, 255), r=10)
    p.oval(x0 + 20, y0 + 40, x0 + 60, y0 + 80, (255, 236, 150, 255)); p.oval(x0 + 140, y0 + 40, x0 + 180, y0 + 80, (255, 236, 150, 255))
    for x, y, s in ((x0 - 60, y0 + 90, .35), (x0 + 270, y0 + 95, .35)):
        _tree(p, x, y, s, (120, 175, 230, 255))


def grammar_zone(p: Pen):
    # 천문대 지붕 학교 + 망원경
    x0, y0 = 1170, 400
    p.rect(x0, y0 + 60, x0 + 280, y0 + 220, (250, 246, 236, 255))
    p.d.pieslice(((x0 + 70) * K, (y0 - 20) * K, (x0 + 210) * K, (y0 + 120) * K), 180, 360, fill=(70, 120, 200, 255), outline=OUT, width=int(2.2 * K))
    p.rect(x0 + 132, y0 + 2, x0 + 148, y0 + 50, (255, 210, 80, 255), lw=1.8)
    p.rect(x0 - 10, y0 + 50, x0 + 290, y0 + 70, (40, 160, 80, 255), r=6)
    for wx in (x0 + 30, x0 + 210):
        p.rect(wx, y0 + 100, wx + 40, y0 + 150, (200, 230, 248, 255), r=6)
    p.rect(x0 + 115, y0 + 140, x0 + 165, y0 + 220, (150, 110, 80, 255), r=12)
    # 망원경
    p.poly([(x0 + 330, y0 + 120), (x0 + 420, y0 + 70), (x0 + 430, y0 + 90), (x0 + 340, y0 + 140)], (240, 240, 245, 255))
    p.line([(x0 + 370, y0 + 115), (x0 + 345, y0 + 210)], lw=4); p.line([(x0 + 370, y0 + 115), (x0 + 400, y0 + 210)], lw=4)
    # ABC 깃발
    p.line([(x0 + 140, y0 - 20), (x0 + 140, y0 - 80)], lw=3); p.poly([(x0 + 140, y0 - 80), (x0 + 190, y0 - 66), (x0 + 140, y0 - 52)], (240, 110, 110, 255))


def small_places(p: Pen):
    # 스티커 가게 (왼쪽 아래)
    x0, y0 = 230, 880
    p.rect(x0, y0, x0 + 150, y0 + 90, (255, 250, 240, 255))
    for i in range(5):
        p.poly([(x0 - 10 + i * 34, y0 - 30), (x0 + 24 + i * 34, y0 - 30), (x0 + 24 + i * 34, y0), (x0 - 10 + i * 34, y0)], [(240, 110, 110, 255), (255, 255, 255, 255)][i % 2], lw=1.8)
    p.oval(x0 + 20, y0 + 25, x0 + 60, y0 + 65, (255, 210, 80, 255)); p.oval(x0 + 90, y0 + 25, x0 + 130, y0 + 65, (120, 190, 240, 255))
    # 엄마 아빠 집 (오른쪽 아래)
    x0, y0 = 1250, 850
    p.rect(x0, y0, x0 + 140, y0 + 90, (255, 255, 255, 255))
    p.poly([(x0 - 15, y0 + 6), (x0 + 70, y0 - 60), (x0 + 155, y0 + 6)], (232, 80, 138, 255))
    p.rect(x0 + 55, y0 + 40, x0 + 85, y0 + 90, (232, 80, 138, 255))
    p.d.polygon([((x0 + 70) * K, (y0 - 14) * K), ((x0 + 56) * K, (y0 - 28) * K), ((x0 + 84) * K, (y0 - 28) * K)], fill=(255, 255, 255, 255))


def paste_scaled(img, src, cx, bottom, h, shadow=True):
    s = src.copy()
    s = s.crop(s.getbbox()) if s.mode == "RGBA" and s.getbbox() else s
    s = s.resize((int(s.width * h / s.height), h), Image.LANCZOS)
    x, y = int(cx - s.width / 2), int(bottom - h)
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse((cx - s.width * .38, bottom - 10, cx + s.width * .38, bottom + 8), fill=(0, 0, 0, 60))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(3)))
    img.alpha_composite(s if s.mode == "RGBA" else s.convert("RGBA"), (x, y))


def signboard(img, cover: Image.Image, x, y, w, color):
    """교재 표지를 나무 간판처럼."""
    c = cover.convert("RGBA")
    c = c.resize((w, int(c.height * w / c.width)), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    pad = 10
    d.rectangle((x + w / 2 - 6, y + c.height, x + w / 2 + 6, y + c.height + 60), fill=(150, 110, 80), outline=INK, width=2)
    d.rounded_rectangle((x - pad, y - pad, x + w + pad, y + c.height + pad), 14, fill=(255, 255, 255), outline=color, width=6)
    img.alpha_composite(c, (x, y))


def tag(img, cx, y, text, color, sub=None, new=False, big=False):
    d = ImageDraw.Draw(img)
    f = font(30 if big else 22)
    tw = d.textlength(text, font=f)
    padx, h = 18, (50 if big else 38)
    x0, x1 = cx - tw / 2 - padx, cx + tw / 2 + padx
    if big:
        d.rounded_rectangle((x0, y + 4, x1, y + h + 4), h // 2, fill=shade(color, .7))
        d.rounded_rectangle((x0, y, x1, y + h), h // 2, fill=color, outline=(255, 255, 255), width=4)
        d.text((cx, y + h / 2), text, font=f, fill=(255, 255, 255), anchor="mm")
    else:
        d.rounded_rectangle((x0, y, x1, y + h), 12, fill=(255, 255, 255), outline=color, width=4)
        d.text((cx, y + h / 2), text, font=f, fill=INK, anchor="mm")
    if new:
        nf = font(16)
        d.rounded_rectangle((x1 - 12, y - 14, x1 + 40, y + 12), 8, fill=(255, 200, 40), outline=INK, width=2)
        d.text((x1 + 14, y - 1), "NEW", font=nf, fill=INK, anchor="mm")
    if sub:
        sf = font(17, bold=False)
        sw = d.textlength(sub, font=sf)
        d.rounded_rectangle((cx - sw / 2 - 10, y + h + 6, cx + sw / 2 + 10, y + h + 34), 10, fill=(255, 255, 255, 230))
        d.text((cx, y + h + 20), sub, font=sf, fill=BROWN, anchor="mm")


def icon(d, name, cx, cy):
    w = (255, 255, 255)
    if name == "내 방":
        d.polygon([(cx - 11, cy), (cx, cy - 11), (cx + 11, cy)], fill=w); d.rectangle((cx - 8, cy, cx + 8, cy + 10), fill=w)
    elif name == "스티커":
        pts = [(cx + 12 * math.cos(-math.pi / 2 + i * math.pi / 5) * (1 if i % 2 == 0 else .45),
                cy + 12 * math.sin(-math.pi / 2 + i * math.pi / 5) * (1 if i % 2 == 0 else .45)) for i in range(10)]
        d.polygon(pts, fill=w)
    elif name == "미션":
        d.line([(cx - 10, cy), (cx - 3, cy + 8), (cx + 11, cy - 8)], fill=w, width=5, joint="curve")
    else:
        d.ellipse((cx - 11, cy - 9, cx - 1, cy + 1), fill=w); d.ellipse((cx + 1, cy - 9, cx + 11, cy + 1), fill=w)
        d.polygon([(cx - 11, cy - 3), (cx + 11, cy - 3), (cx, cy + 11)], fill=w)


def header(img):
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 86), fill=(255, 250, 235))
    d.line((0, 86, W, 86), fill=(235, 215, 160), width=3)
    d.text((34, 43), "Oh! My", font=font(40), fill=(255, 138, 31), anchor="lm")
    ow = d.textlength("Oh! My ", font=font(40))
    d.rounded_rectangle((34 + ow, 14, 34 + ow + 170, 72), 14, fill=(255, 201, 60))
    d.text((34 + ow + 85, 43), "CEDU", font=font(40), fill=(58, 42, 0), anchor="mm")
    d.text((34 + ow + 190, 47), "초등 영어 놀이섬", font=font(20, False), fill=BROWN, anchor="lm")
    menus = [("내 방", (130, 90, 230)), ("스티커", (240, 110, 110)), ("미션", (40, 160, 80)), ("엄마아빠", (232, 80, 138))]
    x = W - 40
    for name, col in reversed(menus):
        tw = d.textlength(name, font=font(17))
        cx = x - max(56, tw) / 2
        d.ellipse((cx - 22, 10, cx + 22, 54), fill=col, outline=(255, 255, 255), width=3)
        icon(d, name, cx, 32)
        d.text((cx, 70), name, font=font(17), fill=INK, anchor="mm")
        x -= max(56, tw) + 22
    d.rounded_rectangle((x - 210, 26, x - 20, 62), 18, fill=(255, 255, 255), outline=(235, 215, 160), width=2)
    d.text((x - 115, 44), "민준 · ★ 128", font=font(18), fill=INK, anchor="mm")


def main(cover_dir: Path, out_path: Path):
    p = Pen(W, H, seed=3, bg=(255, 255, 255, 255))
    draw_map(p)
    phonics_zone(p); speaking_zone(p); story_house(p); grammar_zone(p); small_places(p)
    img = p.img.resize((W, H), Image.LANCZOS).convert("RGBA")

    # 시리즈 간판 (교재 표지)
    signboard(img, Image.open(cover_dir / "phonics_set.png"), 330, 250, 170, C_PH)
    signboard(img, Image.open(cover_dir / "speaking_set.png"), 990, 268, 150, C_SP)
    signboard(img, Image.open(cover_dir / "grammar_set.png"), 1460, 330, 110, C_GR)

    # Oh! My Speaking 캐릭터는 말하기 나라에만
    ch = ROOT / "assets" / "characters"
    paste_scaled(img, Image.open(ch / "mom.png"), 610, 640, 165)
    paste_scaled(img, Image.open(ch / "jack.png"), 675, 668, 145)
    paste_scaled(img, Image.open(ch / "amy.png"), 1000, 662, 140)
    paste_scaled(img, Image.open(ch / "tom.png"), 1065, 672, 140)
    paste_scaled(img, Image.open(ch / "wacky.png"), 930, 885, 115)

    header(img)
    # 구역 이름 (큰 배너) + 장소 이름표
    tag(img, 290, 300, "파닉스 나라", C_PH, big=True)
    tag(img, 200, 600, "알파벳 소리 블록", C_PH, sub="Oh! My Phonics 1~4")
    tag(img, 460, 615, "소리 미끄럼틀", C_PH, sub="소리 맞추기 게임")
    tag(img, 800, 288, "말하기 나라", C_SP, big=True)
    tag(img, 800, 645, "패턴 무대", C_SP, sub="Oh! My Speaking 1~6 · 교재 MP3")
    tag(img, 790, 895, "이야기 숲 · Oh! My Story", C_ST, sub="말한 대로 이어지는 AI 이야기", new=True)
    tag(img, 1310, 290, "문법 나라", C_GR, big=True)
    tag(img, 1310, 635, "문법 학교", C_GR, sub="Oh! My Grammar 1~3")
    tag(img, 305, 985, "스티커 가게", (240, 110, 110))
    tag(img, 1320, 952, "엄마 아빠", (232, 80, 138), sub="학습 리포트")

    d = ImageDraw.Draw(img)
    d.rounded_rectangle((W / 2 - 230, H - 34, W / 2 + 230, H - 8), 10, fill=(255, 255, 255, 200))
    d.text((W / 2, H - 21), "Oh! My CEDU 첫 화면 목업 · 배경·건물은 자리표시 그림", font=font(15, False), fill=(90, 80, 60), anchor="mm")
    img.convert("RGB").save(out_path, quality=92)
    print("saved", out_path, img.size)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
