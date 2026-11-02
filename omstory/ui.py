"""
ui.py — 디자인 캔버스("Oh! My Story 앱 디자인")를 Streamlit에 옮기기 위한 CSS와 HTML 조각

색: 크림 종이 #FFF8EA · 하늘 #5BC8F0 · 코랄 #FF7B7B · 햇살 #FFD34E · 잉크 #1E2A4A · Wacky 보라 #6A4BD6
글꼴: Jua(제목) · Nunito(영어) · Noto Sans KR(본문)
"""
from __future__ import annotations

import base64
import html
from functools import lru_cache
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
E = html.escape

BOOK_ICON = ('<svg width="{s}" height="{s}" viewBox="0 0 48 48" aria-hidden="true"><rect x="8" y="4" width="32" height="36" rx="4" fill="#5BC8F0"/>'
             '<rect x="8" y="4" width="6" height="36" rx="3" fill="#FF7B7B"/><path d="M8 37h32v5a2 2 0 0 1-2 2H12a4 4 0 0 1-4-4z" fill="#E9EEF2"/>'
             '<rect x="25" y="17" width="3" height="14" rx="1.5" fill="#4E6E78"/>'
             '<path d="M26.5 7l2.3 4.6 5 .7-3.6 3.5.9 5-4.6-2.4-4.6 2.4.9-5-3.6-3.5 5-.7z" fill="#FFD34E"/></svg>')

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Jua&family=Nunito:wght@700;800;900&family=Noto+Sans+KR:wght@400;500;700&display=swap');
:root{--paper:#FFF8EA;--sky:#5BC8F0;--sky-d:#3AA6CF;--coral:#FF7B7B;--sun:#FFD34E;--sun-d:#D8A91F;--ink:#1E2A4A;--muted:#5A6680;--line:#F0E3C8;--violet:#6A4BD6}
html,body,[data-testid="stAppViewContainer"],[data-testid="stApp"]{background:var(--paper)!important;color:var(--ink)}
[data-testid="stHeader"]{background:transparent}
footer,#MainMenu{visibility:hidden}
[data-testid="stHeaderActionElements"],h1 a,h2 a,h3 a{display:none!important}
.block-container{max-width:1180px;padding-top:1.2rem;padding-bottom:3rem}
html,body,p,span,div,label,button,input,textarea{font-family:'Noto Sans KR',sans-serif}
h1,h2,h3{font-family:'Jua',sans-serif!important;font-weight:400!important;color:var(--ink)}
.en{font-family:'Nunito',sans-serif;font-weight:800}
.muted{color:var(--muted)}
/* 기본 버튼 */
.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button{border-radius:16px;border:2px solid var(--line);background:#fff;color:var(--ink);font-weight:700;min-height:46px}
.stButton>button:hover,.stDownloadButton>button:hover{border-color:var(--sky);color:var(--ink)}
.stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"]{background:var(--sun);border:none;color:#3A2A00;font-family:'Jua',sans-serif;font-size:20px;box-shadow:0 5px 0 var(--sun-d);min-height:54px}
.stButton>button[kind="primary"]:hover{background:#FFDB6B;color:#3A2A00}
.stButton>button:disabled{opacity:.55}
/* 고를 거리 */
[class*="st-key-choice"] button{border-radius:999px;border:2px solid #D9CFF7;font-family:'Nunito',sans-serif;font-weight:800;background:#fff}
[class*="st-key-choice"] button:hover{border-color:var(--violet);background:#FBF9FF}
/* 동화책(펼친 책) */
.st-key-book{background:#FFFDF7;border-radius:26px;padding:20px 22px;box-shadow:0 12px 0 #E8D3A8,0 20px 30px -18px rgba(90,60,0,.45);margin-bottom:18px}
.st-key-shelf_panel,.st-key-start_panel,.st-key-panel_right{background:#fff;border-radius:26px;padding:18px 20px}
/* 카드 */
.oms-header{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:0 0 14px}
.oms-brand{display:flex;align-items:center;gap:10px}
.oms-brand b{font-family:'Jua',sans-serif;font-size:30px;font-weight:400}
.chip{display:inline-flex;align-items:center;gap:6px;background:#fff;border:2px solid var(--line);border-radius:999px;padding:4px 12px;font-size:14px;font-weight:700;color:var(--muted)}
.hero{background:var(--sky);border-radius:30px;padding:26px 26px 20px;box-shadow:0 10px 0 var(--sky-d);position:relative;overflow:hidden;min-height:330px}
.hero .tag{display:inline-block;background:#fff;color:#1E6E8E;border-radius:999px;padding:4px 14px;font-size:14px;font-weight:700}
.hero .unit{font-family:'Nunito',sans-serif;font-weight:900;font-size:18px;color:#0F4A63;margin-top:12px}
.hero h2{max-width:62%;font-family:'Nunito',sans-serif!important;font-weight:900!important;font-size:40px;line-height:1.05;color:#fff;margin:4px 0 6px}
.hero p{color:#08384C;font-size:17px;line-height:1.6;max-width:290px;position:relative;z-index:1}
.hero img{position:absolute;right:14px;bottom:10px;height:230px}
.hero .bubble{position:absolute;right:22px;top:22px;background:#fff;border-radius:18px 18px 4px 18px;padding:10px 14px;font-family:'Nunito',sans-serif;font-weight:800}
.tile{border-radius:16px;border:2px solid #EFE7D6;background:#fff;padding:10px;height:132px;box-sizing:border-box;overflow:hidden;display:flex;flex-direction:column;gap:4px}
.tile .no{font-family:'Nunito',sans-serif;font-weight:900;font-size:13px}
.tile .t{font-family:'Nunito',sans-serif;font-weight:800;font-size:13px;line-height:1.25}
.tile .tg{margin-top:auto;align-self:flex-start;font-size:11px;font-weight:700;border-radius:99px;padding:1px 8px}
.expr{border-radius:22px;padding:16px 18px;margin-bottom:10px}
.expr .e{font-family:'Nunito',sans-serif;font-weight:900;font-size:30px}
.seed{background:#fff;border:4px solid var(--line);border-radius:24px;overflow:hidden;margin-bottom:6px}
.seed.on{border-color:var(--sky);box-shadow:0 6px 0 var(--sky-d)}
.seed img{width:100%;height:130px;object-fit:cover;object-position:bottom;display:block}
.seed .t{padding:10px 14px 2px;font-family:'Jua',sans-serif;font-size:21px}
.seed .d{padding:0 14px 12px;font-size:13px;color:var(--muted);line-height:1.5}
.words{display:grid;grid-template-columns:repeat(auto-fill,minmax(72px,1fr));gap:8px;margin:6px 0 8px}
.words div{border:2px solid var(--line);background:#FFFBF2;border-radius:16px;padding:6px 2px;text-align:center;font-family:'Nunito',sans-serif;font-weight:800;font-size:11px}
.words img{width:44px;height:44px;object-fit:contain;display:block;margin:0 auto 2px}
.scene{position:relative;border-radius:20px;overflow:hidden}
.scene img{width:100%;display:block}
.scene .badge{position:absolute;right:14px;top:14px;background:var(--sun);color:#3A2A00;border-radius:999px;padding:5px 14px;font-size:14px;font-weight:700;box-shadow:0 4px 0 var(--sun-d)}
.scene .where{position:absolute;left:14px;top:14px;background:rgba(255,255,255,.92);border-radius:12px;padding:3px 12px;font-size:13px;font-weight:700}
.pagetext{font-family:'Nunito',sans-serif;font-weight:800;font-size:19px;line-height:1.5;margin:12px 0 2px}
.pageno{text-align:center;font-family:'Jua',sans-serif;color:#B49A6A;font-size:18px;margin-top:6px}
.msg{display:grid;grid-template-columns:44px minmax(0,1fr);gap:10px;margin:8px 0}
.msg img{width:44px;height:44px;object-fit:contain;border-radius:50%}
.msg .b{border-radius:4px 18px 18px 18px;padding:10px 14px}
.msg .b .en{font-size:16px}
.msg .b .ko{font-size:12px;color:var(--muted)}
.me{display:flex;flex-direction:column;align-items:flex-end;gap:6px;margin:8px 0}
.me .b{background:var(--sky);color:#08384C;border-radius:18px 4px 18px 18px;padding:10px 14px;font-family:'Nunito',sans-serif;font-weight:900;font-size:16px}
.me .b.ko{background:#EEF0F4;color:var(--ink);font-family:'Noto Sans KR',sans-serif;font-weight:700}
.pill{display:inline-block;font-size:12px;font-weight:700;border-radius:99px;padding:2px 10px;margin-left:4px}
.k2e{background:#FFF6D6;border:3px solid var(--sun);border-radius:22px;padding:14px 16px;margin:10px 0}
.k2e .big{font-family:'Nunito',sans-serif;font-weight:900;font-size:25px;line-height:1.25;margin:6px 0}
.steps{display:flex;flex-wrap:wrap;align-items:center;gap:6px;font-size:13px;color:var(--muted);margin:6px 0}
.steps span.s{border-radius:99px;padding:3px 10px;font-weight:700}
.progress{display:inline-flex;align-items:center;gap:8px;background:#fff;border-radius:999px;padding:6px 14px;font-size:13px;font-weight:700}
.progress .bar{width:110px;height:12px;border-radius:99px;background:#F3E6CC;overflow:hidden;display:inline-block}
.progress .bar i{display:block;height:12px;background:#FFC21A}
.cele{text-align:center;padding:10px 0 4px}
.cele .goal{display:inline-block;background:var(--sun);color:#3A2A00;border-radius:999px;padding:6px 16px;font-weight:700;box-shadow:0 4px 0 var(--sun-d)}
.cele h1{font-size:50px;margin:10px 0 4px}
.strip{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin:12px 0}
.strip div{width:96px;height:72px;border-radius:12px;overflow:hidden;position:relative;border:3px solid var(--sky);background:#FBF4E4}
.strip div.empty{border:3px dashed #E4CFA2}
.strip img{width:100%;height:100%;object-fit:cover}
.strip b{position:absolute;left:6px;bottom:4px;font-family:'Nunito',sans-serif;font-size:13px;background:#fff;border-radius:6px;padding:0 6px}
.cover{border-radius:10px 30px 30px 10px;background:var(--sky);border-left:20px solid var(--coral);box-shadow:0 26px 40px -24px rgba(40,60,90,.6),inset -6px 0 0 var(--sky-d);padding:24px;transform:rotate(-1.5deg);margin:6px 8px 20px}
.cover .tg{display:inline-block;background:#fff;color:#1E6E8E;border-radius:999px;padding:3px 12px;font-size:13px;font-weight:700}
.cover h2{color:#fff;font-size:38px;line-height:1.15;margin:10px 0 12px}
.cover img{width:100%;border-radius:18px;border:6px solid #fff;display:block}
.cover .by{color:#08384C;font-weight:700;margin-top:12px;line-height:1.5}
.stat{background:#fff;border-radius:20px;padding:14px 16px}
.stat b{font-family:'Nunito',sans-serif;font-weight:900;font-size:30px;display:block}
.stat span{font-size:14px;color:var(--muted)}
.stat.y{background:#FFF1C7}
.card{background:#fff;border-radius:22px;padding:14px 16px;margin:10px 0}
.notes div{display:flex;justify-content:space-between;gap:10px;font-size:14px;padding:3px 0}
.notes .en{font-size:14px}
.thumbs{display:flex;gap:10px;overflow-x:auto}
.thumbs div{min-width:120px;flex:1}
.thumbs img{width:100%;height:70px;object-fit:cover;border-radius:10px}
.thumbs span{font-family:'Nunito',sans-serif;font-weight:800;font-size:11px;color:#3C4763}
.rec{max-width:560px;margin:0 auto}
.rec .k{background:#E6F6FD;border-radius:18px;padding:12px 16px;margin:10px 0}
@media (max-width:640px){.hero p{max-width:58%}.tile{height:auto;min-height:0}.hero h2{font-size:32px}.hero img{height:150px}.hero .bubble{display:none}.cele h1{font-size:36px}.expr .e{font-size:24px}.oms-brand b{font-size:24px}}
</style>
"""


@lru_cache(maxsize=256)
def b64(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    mime = "image/png" if p.suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def b64_bytes(data: bytes, mime: str = "image/jpeg") -> str:
    return f"data:{mime};base64," + base64.b64encode(data).decode()


def char_src(name: str) -> str:
    return b64(str(ASSETS / "characters" / f"{name}.png"))


def bg_src(scene: str) -> str:
    return b64(str(ASSETS / "backgrounds" / f"{scene}.png"))


def icon(size: int = 40) -> str:
    return BOOK_ICON.format(s=size)


def header(left_html: str, right_html: str = "") -> str:
    return f'<div class="oms-header"><div class="oms-brand">{left_html}</div><div>{right_html}</div></div>'


def bubble(who: str, en: str, ko: str = "", bg: str = "#F4F1FF") -> str:
    colors = {"wacky": "#F4F1FF", "amy": "#FFF1F1", "jack": "#FFF8E8", "tom": "#EAF3FF", "mom": "#FDEAF2"}
    return (f'<div class="msg"><img src="{char_src(who)}" alt="{E(who)}" style="background:{colors.get(who, bg)}">'
            f'<div class="b" style="background:{colors.get(who, bg)}"><div class="en">{E(en)}</div>'
            f'{f"<div class=ko>{E(ko)}</div>" if ko else ""}</div></div>')


def me(text: str, pills: list[tuple[str, str, str]] | None = None, korean: bool = False) -> str:
    ps = "".join(f'<span class="pill" style="background:{bg};color:{fg}">{E(t)}</span>' for t, bg, fg in (pills or []))
    return f'<div class="me"><div class="b{" ko" if korean else ""}">{E(text)}</div><div>{ps}</div></div>'


def progress(n: int, goal: int) -> str:
    pct = min(100, int(100 * n / max(goal, 1)))
    return (f'<span class="progress">말한 문장 <span class="bar"><i style="width:{pct}%"></i></span>'
            f'<span class="en">{n} / {goal} ⭐</span></span>')
