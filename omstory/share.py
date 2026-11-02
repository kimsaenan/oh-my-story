"""
share.py — 오늘의 이야기 기록 (중립적인 기록: 아이·보호자·선생님 누구나 같은 내용을 본다)

어디서 쓰일지(학원·집·방과후) 정하지 않고, "오늘 배운 표현으로 무엇을 말했는지"를 보여 준다.
실제 공유는 링크로 하며(PoC에서는 HTML 파일), 카카오 알림톡 같은 발송은 정식 서비스에서 붙인다.
"""
from __future__ import annotations

import base64
import html


def record_message(child: str, unit: dict, book_title: str, n_sentences: int, notes: list[dict]) -> str:
    made = ", ".join(n["en"] for n in notes[:3]) or "-"
    q = unit["useful_questions"][0] if unit.get("useful_questions") else unit["key_patterns"][0]
    return (f"[Oh! My Story] {child}의 오늘의 이야기 기록\n"
            f"· 동화책: {book_title} (Unit {unit['no']:02d} \"{unit['title']}\")\n"
            f"· 오늘 배운 표현: {' / '.join(unit['key_patterns'])}\n"
            f"· 영어로 말한 문장: {n_sentences}개 · 만든 표현: {len(notes)}개\n"
            f"· 이렇게 말했어요: {made}\n"
            f"· 이 표현으로 이야기해 보세요: \"{q}\"\n▶ 동화책 보기: (공유 링크)")


def record_page(child: str, unit: dict, book_title: str, cover_jpg: bytes, pages: list[dict],
                notes: list[dict], n_sentences: int) -> str:
    """공유용 1장짜리 페이지: 표지 + 페이지 문장 + 오늘 배운 표현 + 내가 만든 표현."""
    e = html.escape
    img = base64.b64encode(cover_jpg).decode()
    pg = "".join(f"<li><b>{e(p.get('page_en', ''))}</b><br><small>{e(p.get('page_ko', ''))}</small></li>" for p in pages if p.get("page_en"))
    nt = "".join(f"<li>{e(n['en'])} <small>· {e(n['tag'])}</small></li>" for n in notes)
    kp = " / ".join(e(k) for k in unit["key_patterns"])
    q = e(unit["useful_questions"][0]) if unit.get("useful_questions") else ""
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(book_title)} · Oh! My Story</title>
<style>body{{font-family:system-ui,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;max-width:560px;margin:0 auto;padding:16px;color:#1E2A4A;background:#FFF8EA}}
img{{width:100%;border-radius:18px}}h1{{font-size:1.4rem}}h2{{font-size:1.05rem;margin-top:22px}}small{{color:#5A6680}}li{{margin:6px 0}}
.box{{background:#fff;border-radius:16px;padding:12px 16px}}.k{{background:#E6F6FD;border-radius:16px;padding:12px 16px}}</style></head>
<body><h1>📖 {e(book_title)}</h1><p>지은이 {e(child)} · 함께 쓴 친구 Wacky · Unit {unit['no']:02d} {e(unit['title'])}</p>
<img src="data:image/jpeg;base64,{img}" alt="동화책 표지 장면">
<h2>오늘 배운 표현</h2><div class="k"><b>{kp}</b></div>
<h2>영어로 말한 문장 {n_sentences}개 · 내가 만든 표현 {len(notes)}개</h2><div class="box"><ul>{nt}</ul></div>
<h2>동화책 페이지</h2><div class="box"><ol>{pg}</ol></div>
<h2>이 표현으로 이야기해 보세요</h2><div class="k">“{q}”</div></body></html>"""
