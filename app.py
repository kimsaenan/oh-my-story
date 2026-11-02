"""
Oh! My Story — 아이의 상상이 이야기가 되는 초등 맞춤형 AI 스피킹 스토리
(Oh! My Speaking 교재 연계형 AI 말하기 짝 서비스) · Streamlit 작동 데모

화면 흐름 (디자인 캔버스와 같은 순서)
  1. 단원 책장 → 2. 오늘의 주요 표현·이야기 씨앗 → 3. 이야기 페이지(한국어 → 영어 포함)
  → 4. 오늘의 목표 달성(다음 페이지 쓰기) → 5. 나의 동화책 완성 + 오늘의 이야기 기록
실행: streamlit run app.py
"""
from __future__ import annotations

import statistics

import streamlit as st

from omstory import config, speech
from omstory import textbook_audio as tba
from omstory import ui
from omstory.analysis import english_sentences, has_korean
from omstory.card import find_sticker
from omstory.pipeline import run_page
from omstory.prompting import RULE_NAMES_KO
from omstory.rag import ai_units, list_units, retrieve
from omstory.scene_render import render_scene
from omstory.scenes import SCENE_LABELS
from omstory.share import record_message, record_page
from omstory.story import llm_available, next_prompt

st.set_page_config(page_title="Oh! My Story", page_icon="📖", layout="wide", initial_sidebar_state="collapsed")
st.markdown(ui.CSS, unsafe_allow_html=True)
S = st.session_state
E = ui.E

UNITS = list_units()
AI_UNIT_IDS = [u["id"] for u in ai_units()]
OPEN_AI = {"b6_u02", "b6_u03", "b6_u04"}      # 디자인: 02~04는 AI 체험, 05~08은 수업 후 열림


# ---------------- 캐시 ----------------
@st.cache_data(show_spinner=False)
def tts(text: str, speaker: str = "wacky") -> bytes | None:
    return speech.synthesize(text, speaker=speaker)


@st.cache_data(show_spinner=False, max_entries=64)
def scene_jpg(scene: str, chars: tuple, stickers: tuple, magic: str | None) -> bytes:
    return render_scene(scene, list(chars), list(stickers), magic)


# ---------------- 상태 ----------------
def init():
    S.setdefault("screen", "shelf")
    S.setdefault("unit_id", "b6_u01")
    S.setdefault("seed_id", None)
    S.setdefault("library", [])
    S.setdefault("stories_today", 0)


def start_story(seed_id: str):
    ctx = retrieve(S.unit_id)
    seed = ctx.seed(seed_id)
    plan0 = seed["pages"][0]
    S.update(seed_id=seed["id"], screen="story", page_idx=0, pages=[], outputs=[], notes=[], n_sent=0, continued=False,
             q=plan0["q"], q_ko=plan0.get("q_ko", ""), q_audio=plan0.get("q_audio"), choices=list(plan0.get("choices", [])),
             scene=seed.get("scene") or ctx.unit.get("scene", "park"), stickers=[], magic=None, new_sticker=None,
             reaction={"who": seed["opening"]["speaker"], "en": seed["opening"]["en"], "ko": seed["opening"]["ko"]},
             last_child=None, pending=None, from_korean=False, saved=False)


init()

# ---------------- 사이드바 (설정 · 시연용 보기) ----------------
with st.sidebar:
    st.markdown(f"### {ui.icon(28)} 설정", unsafe_allow_html=True)
    child = st.text_input("아이 이름", value="민준", key="child")
    llm_ok = llm_available()
    use_llm = st.toggle("AI 이야기 생성 (LLM)", value=llm_ok, disabled=not llm_ok)
    use_tts = st.toggle("캐릭터 목소리 (TTS)", value=speech.tts_available(), disabled=not speech.tts_available())
    demo = st.toggle("🔍 시연용 보기 (AI 동작 보기)", value=False,
                     help="페이지마다 Wacky가 참고한 교재 내용, 적용한 지침, 검사 결과를 보여 줘요.")
    st.caption("엔진 상태")
    st.write(f"- 이야기: {'🤖 LLM 연결됨' if llm_ok else '📝 편집자 문장 (OPENAI_API_KEY 없음)'}")
    st.write(f"- 음성 인식: {'Whisper 사용 가능' if speech.stt_available() else '입력·버튼으로 대체'}")
    st.write(f"- 기준: 기본 {config.BASE_PAGES}페이지 · 최대 {config.MAX_PAGES}페이지 · 목표 {config.GOAL_SENTENCES}문장 · 하루 {config.DAILY_STORIES}편")
    if st.button("처음 화면으로", width="stretch"):
        S.screen = "shelf"
        st.rerun()

name_en = "Minjun" if child == "민준" else (child if child.isascii() else "Minjun")
ctx = retrieve(S.unit_id)
unit = ctx.unit
ai_on = use_llm and llm_ok


def brand(sub: str = "") -> str:
    return f'{ui.icon(42)}<b>Oh! My Story</b>{f"<span class=chip>{E(sub)}</span>" if sub else ""}'


def kid_chip() -> str:
    stars = 100 + sum(len(b.get("pages", [])) for b in S.library) * 2
    return f'<span class="chip">🙂 {E(child)} 작가님 · <span class="en" style="color:#A06A00">★ {stars}</span></span>'


# =====================================================================
# 1. 단원 책장
# =====================================================================
def screen_shelf():
    st.markdown(ui.header(brand("Oh! My Speaking 6"), kid_chip()), unsafe_allow_html=True)
    left, right = st.columns([1.05, 1], gap="large")
    with left:
        st.markdown(f"""<div class="hero"><span class="tag">오늘 배운 단원</span>
<div class="unit">Unit {unit['no']:02d}</div><h2>{E(unit['title'])}</h2>
<div style="color:#0F4A63;font-weight:700">{E(unit.get('theme_ko', ''))} 이야기</div>
<p>오늘 배운 표현으로<br>Wacky랑 나만의 동화책을 만들어 볼까?</p>
<span class="bubble">Beep! Let's make<br>a story!</span><img src="{ui.char_src('wacky')}" alt="Wacky"></div>""", unsafe_allow_html=True)
        st.write("")
        full = S.stories_today >= config.DAILY_STORIES
        locked = unit["id"] in AI_UNIT_IDS and not ai_on
        if st.button("📖 동화책 만들기", type="primary", width="stretch", disabled=full or locked):
            S.screen = "start"
            st.rerun()
        if full:
            st.caption(f"오늘은 동화책을 {config.DAILY_STORIES}편 만들었어요. 내일 또 만나요! 👋")
        elif locked:
            st.caption("이 단원은 AI가 연결되면 체험할 수 있어요 (사이드바에서 AI 켜기).")
    with right:
        with st.container(key="shelf_panel"):
            st.markdown('<b style="font-size:18px">6권 이야기 책장</b> <span class="muted" style="font-size:13px">· 단원마다 새 동화책이 열려요</span>',
                        unsafe_allow_html=True)
            cols = st.columns(4)
            for i, u in enumerate(UNITS):
                kind = "open" if u["id"] not in AI_UNIT_IDS else ("ai" if u["id"] in OPEN_AI else "lock")
                sel = u["id"] == S.unit_id
                tag = {"open": ("완성", "#5BC8F0", "#08384C"), "ai": ("AI 체험", "#FFF1C7", "#7A5200"),
                       "lock": ("수업 후 열려요", "#EEF0F4", "#5A6680")}[kind]
                border = "#5BC8F0" if sel else "#EFE7D6"
                with cols[i % 4]:
                    st.markdown(f"""<div class="tile" style="border-color:{border};background:{'#E6F6FD' if sel else '#fff'}">
<span class="no" style="color:#1E6E8E">Unit {u['no']:02d}</span><span class="t">{E(u['title'])}</span>
<span class="tg" style="background:{tag[1]};color:{tag[2]}">{tag[0]}</span></div>""", unsafe_allow_html=True)
                    can = kind == "open" or (kind == "ai" and ai_on)
                    if st.button("열기" if not sel else "선택됨", key=f"unit_{u['id']}", disabled=not can or sel, width="stretch"):
                        S.unit_id = u["id"]
                        st.rerun()
            if not ai_on:
                st.caption("AI 체험 단원(02~04)은 AI가 연결되면 열려요. 주요 표현만으로 AI가 이야기를 만들어요.")
        with st.container(key="start_panel"):
            st.markdown(f'<b style="font-size:18px">내가 만든 동화책</b> <span class="muted" style="font-size:13px">· 지금까지 {len(S.library)}권 · 표현 '
                        f'{sum(b["notes"] for b in S.library)}개</span>', unsafe_allow_html=True)
            if S.library:
                cols = st.columns(3)
                for i, b in enumerate(S.library[-3:]):
                    with cols[i]:
                        st.image(b["img"], width="stretch")
                        st.caption(b["title"])
            else:
                st.caption("아직 없어요. 오늘 첫 동화책을 만들어 볼까요?")


# =====================================================================
# 2. 오늘의 주요 표현 · 이야기 씨앗
# =====================================================================
def screen_start():
    st.markdown(ui.header(brand(f"Unit {unit['no']:02d} · {unit['title']}"),
                          f'<span class="chip">⭐ 오늘의 목표 · 영어 문장 {config.GOAL_SENTENCES}개 말하기</span>'), unsafe_allow_html=True)
    left, right = st.columns([0.9, 1.3], gap="large")
    with left:
        with st.container(key="start_panel"):
            st.markdown('<b style="color:#1E6E8E">오늘의 주요 표현</b><br><span class="muted">이 표현이 이야기 속 마법 주문이 될 거야!</span>',
                        unsafe_allow_html=True)
            for i, e in enumerate(ctx.key_expressions):
                bg = ["#E6F6FD", "#FFF1C7"][i % 2]
                st.markdown(f'<div class="expr" style="background:{bg}"><div class="e">{E(e["en"])}</div>'
                            f'<div style="color:#3C4763">{E(e.get("ko", ""))}</div></div>', unsafe_allow_html=True)
                p = tba.clip(S.unit_id, e.get("audio"))
                if p:
                    st.audio(str(p), format="audio/mp3")
            d_path, d_text = tba.dialogue(S.unit_id)
            if d_path:
                with st.expander("🎧 교재 대화문 다시 듣기 (Jack & Amy)"):
                    st.caption(d_text.replace(" / ", "  \n"))
                    st.audio(str(d_path), format="audio/mp3")
            st.markdown(f'<div class="msg"><img src="{ui.char_src("wacky")}" alt="Wacky" style="background:#EAF7FD">'
                        f'<div class="b" style="background:#EAF7FD"><div>이 표현으로 어떤 이야기를 만들어 볼까?</div></div></div>',
                        unsafe_allow_html=True)
    with right:
        st.markdown("### 이야기 씨앗을 골라요")
        seeds = ctx.seeds
        if not S.get("seed_pick") or S.seed_pick not in [s["id"] for s in seeds]:
            S.seed_pick = seeds[0]["id"]
        cols = st.columns(len(seeds))
        for c, sd in zip(cols, seeds):
            with c:
                on = sd["id"] == S.seed_pick
                st.markdown(f'<div class="seed{" on" if on else ""}"><img src="{ui.bg_src(sd.get("scene") or "park")}" alt="">'
                            f'<div class="t">{sd.get("emoji", "")} {E(sd["title"])}</div><div class="d">{E(sd["desc"])}</div></div>',
                            unsafe_allow_html=True)
                if st.button("✓ 골랐어요" if on else "이 씨앗 고르기", key=f"seed_{sd['id']}", width="stretch", disabled=on):
                    S.seed_pick = sd["id"]
                    st.rerun()
        with st.container(key="panel_right"):
            st.markdown('<b style="font-size:17px">단어 서랍</b> <span class="muted" style="font-size:13px">· 누르면 교재 원어민 발음 · '
                        '이야기에 넣으면 장면에 나타나요</span>', unsafe_allow_html=True)
            words = [w for w in unit["vocabulary"] if find_sticker(w)]
            tiles = "".join(f'<div><img src="{ui.b64(str(find_sticker(w)))}" alt="">{E(w)}</div>' for w in words)
            st.markdown(f'<div class="words">{tiles}</div>', unsafe_allow_html=True)
            pick = st.pills("발음 듣기", [w for w in words if tba.word(S.unit_id, w)], key="word_pick", label_visibility="collapsed")
            if pick:
                st.audio(str(tba.word(S.unit_id, pick)), format="audio/mp3", autoplay=True)
        b1, b2 = st.columns([1, 1])
        if b1.button("← 책장으로", width="stretch"):
            S.screen = "shelf"
            st.rerun()
        if b2.button("이 씨앗으로 시작하기", type="primary", width="stretch"):
            start_story(S.seed_pick)
            st.rerun()


# =====================================================================
# 3. 이야기 페이지
# =====================================================================
def history_lines() -> list[str]:
    out = []
    for p in S.pages:
        out += [f"Wacky: {p['q']}", f"{name_en}: {p['child']}", f"{p['speaker'].capitalize()}: {p['reply']}"]
    return out


def handle(text: str | None, audio: bytes | None = None, from_korean: bool = False):
    seed = ctx.seed(S.seed_id)
    idx = S.page_idx
    with st.spinner("Wacky가 다음 장면을 상상하는 중…"):
        out = run_page(ctx, seed, idx, S.q, text=text, audio=audio, history=history_lines(), child_name=name_en,
                       use_llm=ai_on, with_tts=use_tts)
    r = out.result
    if not r.child_text:
        st.toast("잘 들리지 않았어요. 다시 말하거나 써 주세요.")
        return
    S.outputs.append(out)
    sents = english_sentences(r.child_text)
    S.n_sent += len(sents)
    pills = []
    if r.expression_used:
        pills.append(("⭐ 오늘의 표현을 썼어요", "#FFF1C7", "#7A5200"))
    S.last_child = {"text": r.child_text, "korean": has_korean(r.child_text), "pills": pills}
    S.reaction = {"who": r.speaker, "en": r.reply_en, "ko": r.reply_ko, "audio": out.audio, "fb": r.feedback_ko,
                  "model": r.model_sentence, "idea": r.idea}

    if r.korean_to_english:                       # 한국어 → 영어: 따라 말하기 기다림
        S.pending = {"en": r.korean_to_english, "ko": r.child_text, "audio": tts(r.korean_to_english, "wacky") if use_tts else None}
        return
    if r.needs_english or r.safe_redirect:
        S.choices = r.choices or S.choices
        return
    S.pending = None
    # 내가 만든 표현 노트
    if sents:
        tag = "⭐ 오늘의 표현" if r.expression_used else ("한국어 → 영어" if from_korean else "내가 만든 문장")
        if r.expression_used or from_korean or len(r.child_text.split()) >= 3:
            S.notes.append({"en": r.child_text.strip(), "tag": tag})
            S.last_child["pills"].append(("내 표현 +1", "#E6F6FD", "#1E6E8E"))
    # 장면: 스티커 쌓기 + 마법 상자
    S.new_sticker = None
    for s in r.stickers:
        if s not in S.stickers and find_sticker(s):
            S.stickers.append(s)
            S.new_sticker = s
    if r.idea and not find_sticker(r.idea) and r.idea.lower() not in [w.lower() for w in unit["vocabulary"]] \
            and 1 <= len(r.idea.split()) <= 3 and r.idea.lower() not in ("it", "i", "me"):
        S.magic = r.idea
    if r.scene:
        S.scene = r.scene
    chars = (r.speaker,) + tuple(c for c in ("wacky", "amy", "jack") if c != r.speaker)[:1]
    img = scene_jpg(S.scene, chars, tuple(S.stickers), S.magic)
    S.pages.append({"q": S.q, "child": r.child_text, "speaker": r.speaker, "reply": r.reply_en, "reply_ko": r.reply_ko,
                    "page_en": r.page_en, "page_ko": r.page_ko.replace(f"{name_en}이(가)", f"{child}이(가)").replace(name_en, child), "img": img, "scene": S.scene, "chars": chars})
    # 다음 페이지로
    q, q_ko, ch = (r.next_q, r.next_q_ko, r.choices) if r.next_q else next_prompt(seed, idx)
    S.page_idx = idx + 1
    nxt_plan = seed["pages"][idx + 1] if idx + 1 < len(seed["pages"]) else {}
    S.q, S.q_ko, S.choices, S.q_audio = q, q_ko or nxt_plan.get("q_ko", ""), list(ch), nxt_plan.get("q_audio")
    if S.page_idx >= config.MAX_PAGES or not q:
        S.screen = "book"
    elif S.page_idx == config.BASE_PAGES and not S.continued:
        S.screen = "milestone"


def scene_html() -> str:
    seed = ctx.seed(S.seed_id)
    chars = S.pages[-1]["chars"] if S.pages else (seed["opening"]["speaker"], "amy")
    img = scene_jpg(S.scene, tuple(chars), tuple(S.stickers), S.magic)
    badge = f'<span class="badge">✨ 새 스티커: {E(S.new_sticker)}</span>' if S.new_sticker else ""
    if S.magic and not badge and S.pages:
        badge = f'<span class="badge" style="background:#6A4BD6;color:#fff;box-shadow:0 4px 0 #4A31A8">마법 상자: {E(S.magic)}</span>'
    return (f'<div class="scene"><img src="{ui.b64_bytes(img)}" alt="이야기 장면"><span class="where">'
            f'{E(SCENE_LABELS.get(S.scene, S.scene))}</span>{badge}</div>')


def screen_story():
    seed = ctx.seed(S.seed_id)
    total = config.BASE_PAGES if not S.continued else config.MAX_PAGES
    left_h = f'{ui.icon(38)}<b>{E(seed["title"])}</b><span class="chip">{S.page_idx + 1} / {total} 페이지</span>'
    st.markdown(ui.header(left_h, ui.progress(S.n_sent, config.GOAL_SENTENCES)), unsafe_allow_html=True)

    with st.container(key="book"):
        lc, rc = st.columns(2, gap="large")
        with lc:
            st.markdown(scene_html(), unsafe_allow_html=True)
            if S.pages and S.pages[-1]["page_en"]:
                p = S.pages[-1]
                st.markdown(f'<div class="pagetext">{E(p["page_en"])}</div><div class="muted" style="font-size:14px">{E(p["page_ko"])}</div>'
                            f'<div class="pageno">— {len(S.pages)} —</div>', unsafe_allow_html=True)
            else:
                o = seed["opening"]
                st.markdown(f'<div class="pagetext">{E(o["en"])}</div><div class="muted" style="font-size:14px">{E(o["ko"])}</div>'
                            f'<div class="pageno">— 시작 —</div>', unsafe_allow_html=True)
            if len(S.pages) > 1:
                with st.expander("📖 앞 페이지 다시 보기"):
                    for i, p in enumerate(S.pages[:-1], 1):
                        st.image(p["img"], caption=f"{i}페이지 · {p['page_en']}", width="stretch")
        with rc:
            rx = S.reaction
            if S.last_child:
                st.markdown(ui.me(S.last_child["text"], S.last_child["pills"], S.last_child["korean"]), unsafe_allow_html=True)
            if rx:
                st.markdown(ui.bubble(rx["who"], rx["en"], rx["ko"]), unsafe_allow_html=True)
                snd = rx.get("audio") or (tts(rx["en"], rx["who"]) if use_tts else None)
                if snd:
                    st.audio(snd, format="audio/mp3")
                if rx.get("model"):
                    st.caption(f"💡 이렇게도 말할 수 있어: **{rx['model']}**")
                    clips = tba.model_sentence(S.unit_id, rx.get("idea", ""), unit.get("frame", ""))
                    if clips:
                        st.audio(tba.join_mp3(clips), format="audio/mp3")
            if S.pending:                                  # 한국어 → 영어 카드
                pd = S.pending
                st.markdown(f'<div class="k2e"><b>🔄 Wacky가 영어로 바꿔 봤어!</b><div class="big">{E(pd["en"])}</div>'
                            f'<div class="steps"><span class="s" style="background:#E6F6FD;color:#1E6E8E">① 내가 한 말</span>→'
                            f'<span class="s" style="background:#FFF1C7;color:#7A5200">② 영어 문장</span>→'
                            f'<span class="s" style="background:#FFE3E3;color:#A33C3C">③ 따라 말하면 내 표현!</span></div></div>',
                            unsafe_allow_html=True)
                if pd.get("audio"):
                    st.audio(pd["audio"], format="audio/mp3")
                if st.button("🎤 따라 말했어요", type="primary", width="stretch", key=f"k2e_{len(S.outputs)}"):
                    S.pending = None
                    handle(pd["en"], from_korean=True)
                    st.rerun()
            else:
                st.markdown(ui.bubble("wacky", S.q, S.q_ko), unsafe_allow_html=True)
                if use_tts:
                    snd = tts(S.q, "wacky")
                    if snd:
                        st.audio(snd, format="audio/mp3")
                if S.q_audio and tba.clip(S.unit_id, S.q_audio):
                    st.caption("🎧 교재 원음으로 듣기")
                    st.audio(str(tba.clip(S.unit_id, S.q_audio)), format="audio/mp3")
                if S.choices:
                    cc = st.columns(len(S.choices))
                    for i, ch in enumerate(S.choices):
                        if cc[i].button(ch, key=f"choice_{len(S.outputs)}_{i}", width="stretch"):
                            handle(ch)
                            st.rerun()
                    st.caption("✏️ 고르지 않고 내가 정해도 돼! 아래에 말하거나 써 봐.")
            st.divider()
            st.markdown("**누르고 이야기해 봐!** <span class='muted' style='font-size:13px'>영어가 어려우면 한국어로 말해도 괜찮아. "
                        "Wacky가 영어 문장으로 바꿔 줄게.</span>", unsafe_allow_html=True)
            audio = st.audio_input("🎤 말하기", key=f"mic_{len(S.outputs)}") if speech.stt_available() else None
            with st.form(key=f"form_{len(S.outputs)}", clear_on_submit=True):
                typed = st.text_input("글자로 쓰기", placeholder="영어나 한국어로 써 보세요", label_visibility="collapsed")
                sent = st.form_submit_button("보내기")
            if sent and typed.strip():
                handle(typed)
                st.rerun()
            if audio:
                handle(None, audio=audio.getvalue())
                st.rerun()
            with st.popover("💡 도움 문장 보기", width="stretch"):
                st.markdown(f"오늘의 표현: **{' / '.join(e['en'] for e in ctx.key_expressions)}**")
                if unit.get("frame"):
                    st.markdown(f"예: *{unit['frame']}*")

    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("이야기 마치기 →", width="stretch", disabled=not S.pages):
            S.screen = "book"
            st.rerun()
    if demo:
        demo_panel()


def demo_panel():
    st.markdown("### 🔍 시연용 보기 · AI가 어떻게 동작했나")
    if not S.get("outputs"):
        st.caption("아이가 말하면 페이지마다 Wacky가 참고한 내용이 여기에 쌓여요.")
        return
    seed = ctx.seed(S.seed_id)
    for i, o in enumerate(S.outputs, 1):
        r = o.result
        eng = {"llm": "🤖 AI 생성" + (" (지침 검사 후 재생성)" if r.attempts > 1 else ""), "safety": "🛡️ 안전 필터"}.get(
            r.engine, "📝 편집자 문장 (AI 대체)" if r.error and ai_on else "📝 편집자 문장")
        with st.expander(f"{i}. \"{r.child_text[:30]}\" → {eng}"):
            st.markdown(f"- **교재(RAG)**: Unit {unit['no']:02d} 주요 표현 {' / '.join(e['en'] for e in ctx.key_expressions)} · 어휘 {len(unit['vocabulary'])}개"
                        + (f" · 배운 단원 {len(ctx.learned_units)}개" if ctx.learned_units else ""))
            st.markdown(f"- **이야기 씨앗**: {seed['title']} · 페이지 {min(i, config.MAX_PAGES)}")
            st.markdown("- **적용한 지침**: " + (", ".join(f"{k} {RULE_NAMES_KO.get(k, '')}" for k in r.rules_used) or "-"))
            st.markdown(f"- **검사**: {'통과' if not r.guard_issues else '1차 문제 → ' + ' / '.join(r.guard_issues)}"
                        + (f" · 참고: {', '.join(r.warnings)}" if r.warnings else ""))
            st.markdown(f"- **교재 밖 단어 비율** {o.off_unit_rate:.0%} · **생성 시간** {o.timings.get('generate', 0):.2f}초")
            if r.korean_to_english:
                st.markdown(f"- **한국어 → 영어**: {r.korean_to_english}")
            if r.error:
                st.caption(r.error)
    c1, c2, c3 = st.columns(3)
    c1.metric("영어로 말한 문장", S.n_sent)
    c2.metric("평균 생성 시간", f"{statistics.mean(o.timings.get('generate', 0) for o in S.outputs):.2f}초")
    c3.metric("내가 만든 표현", len(S.notes))


# =====================================================================
# 4. 오늘의 목표 달성 · 다음 페이지 쓰기
# =====================================================================
def screen_milestone():
    goal = S.n_sent >= config.GOAL_SENTENCES
    badge = f"⭐ 오늘의 목표 달성! 영어 문장 {S.n_sent}개" if goal else f"⭐ 목표까지 {config.GOAL_SENTENCES - S.n_sent}문장 남았어요"
    strip = "".join(f'<div><img src="{ui.b64_bytes(p["img"])}" alt=""><b>{i}</b></div>' for i, p in enumerate(S.pages, 1))
    strip += "".join(f'<div class="empty"><b style="background:transparent;color:#B49A6A">{i}</b></div>'
                     for i in range(len(S.pages) + 1, config.MAX_PAGES + 1))
    st.markdown(f"""<div class="cele"><img src="{ui.char_src('wacky')}" style="height:150px" alt="Wacky">
<div><span class="goal">{badge}</span></div><h1>기본 이야기 완성!</h1>
<div class="en" style="font-size:20px;color:#3C4763">“Beep! What happens next, {E(name_en)}?”</div>
<div class="strip">{strip}</div>
<div class="muted" style="font-size:13px">최대 {config.MAX_PAGES}페이지 · {config.MAX_PAGES}페이지가 되면 Wacky가 멋지게 마무리해 줘요</div></div>""",
                unsafe_allow_html=True)
    st.write("")
    _, a, b, _ = st.columns([0.5, 1, 1, 0.5])
    if a.button(f"✨ 다음 페이지 쓰기 ({config.MAX_PAGES - len(S.pages)}페이지 더)", type="primary", width="stretch"):
        S.continued = True
        S.screen = "story"
        st.rerun()
    if b.button("📖 동화책 완성하기", width="stretch"):
        S.screen = "book"
        st.rerun()
    st.markdown(f'<div style="text-align:center;margin-top:10px"><span class="chip">말한 문장 {S.n_sent}</span> '
                f'<span class="chip">내가 만든 표현 {len(S.notes)}</span> <span class="chip">모은 스티커 {len(S.stickers)}</span></div>',
                unsafe_allow_html=True)


# =====================================================================
# 5. 나의 동화책 완성 + 오늘의 이야기 기록
# =====================================================================
def screen_book():
    seed = ctx.seed(S.seed_id)
    title = f"{child}의 {seed['title']}"
    cover = scene_jpg(S.scene, tuple(S.pages[-1]["chars"]) if S.pages else ("wacky", "amy"), tuple(S.stickers), S.magic)
    stars = len(S.pages) * 2 + sum(1 for n in S.notes if n["tag"].startswith("⭐"))
    if not S.saved:
        S.saved = True
        S.stories_today += 1
        S.library.append({"title": title, "img": cover, "pages": S.pages, "notes": len(S.notes)})
    tab1, tab2 = st.tabs(["📖 나의 동화책", "📝 오늘의 이야기 기록"])
    with tab1:
        left, right = st.columns([0.95, 1.2], gap="large")
        with left:
            st.markdown(f"""<div class="cover"><span class="tg">Oh! My Story · Unit {unit['no']:02d}</span><h2>{E(title)}</h2>
<img src="{ui.b64_bytes(cover)}" alt="표지 장면"><div class="by">지은이 · {E(child)}<br>함께 쓴 친구 · Wacky</div></div>""",
                        unsafe_allow_html=True)
        with right:
            st.markdown(f'<div style="color:#A06A00;font-weight:700">{len(S.pages)}페이지 동화책이 완성됐어요!</div><h1 style="margin-top:0">나의 동화책 완성!</h1>',
                        unsafe_allow_html=True)
            st.markdown(f'<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px">'
                        f'<div class="stat"><b>{S.n_sent}</b><span>영어로 말한 문장</span></div>'
                        f'<div class="stat y"><b>{len(S.notes)}</b><span>내가 만든 표현</span></div>'
                        f'<div class="stat"><b>+{stars} ★</b><span>받은 별</span></div></div>', unsafe_allow_html=True)
            thumbs = "".join(f'<div><img src="{ui.b64_bytes(p["img"])}" alt=""><span>{E(p["page_en"])}</span></div>' for p in S.pages)
            st.markdown(f'<div class="card"><b>페이지 넘겨보기</b><div class="thumbs" style="margin-top:8px">{thumbs}</div></div>', unsafe_allow_html=True)
            notes = "".join(f'<div><span class="en">{E(n["en"])}</span><span class="muted">{E(n["tag"])}</span></div>' for n in S.notes) \
                or '<div class="muted">다음엔 표현을 더 모아 보자!</div>'
            st.markdown(f'<div class="card notes"><b>내가 만든 영어 표현</b>{notes}</div>', unsafe_allow_html=True)
            b1, b2, b3 = st.columns(3)
            page_html = record_page(child, unit, title, cover, S.pages, S.notes, S.n_sent)
            b1.download_button("기록 공유하기", page_html, file_name="ohmystory_record.html", mime="text/html", width="stretch")
            if b2.button("Wacky가 읽어 주기", width="stretch"):
                txt = " ".join(p["page_en"] for p in S.pages if p["page_en"])[:900]
                snd = tts(txt, "wacky") if use_tts else None
                st.audio(snd, format="audio/mp3") if snd else st.caption("음성을 만들 수 없어요 (TTS 꺼짐).")
            if b3.button("내 책장에 꽂기", type="primary", width="stretch"):
                S.screen = "shelf"
                st.rerun()
    with tab2:
        q = unit["useful_questions"][0] if unit.get("useful_questions") else ""
        used = [n["en"] for n in S.notes if n["tag"].startswith("⭐")]
        made = "".join(f'<div><span class="en">{E(n["en"])}</span><span class="muted">{E(n["tag"])}</span></div>' for n in S.notes)
        st.markdown(f"""<div class="rec"><h2>{E(child)}의 오늘의 이야기 기록</h2>
<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px">
<div class="stat"><b>{S.n_sent}</b><span>영어로 말한 문장</span></div><div class="stat y"><b>{len(S.notes)}</b><span>새로 만든 표현</span></div>
<div class="stat"><b>{len(S.pages)}p</b><span>완성한 동화책</span></div></div>
<div class="k"><b style="color:#1E6E8E">오늘 배운 표현</b><div class="en" style="font-size:18px">{' / '.join(E(k) for k in unit['key_patterns'])}</div>
<div class="muted" style="font-size:13px">이 표현으로 말한 문장: {E(' · '.join(used)) or '다음엔 한번 써 보자!'}</div></div>
<div class="card notes"><b>새로 만든 표현</b>{made or '<div class="muted">-</div>'}</div>
<div class="k"><b style="color:#1E6E8E">이 표현으로 이야기해 보세요</b><div class="en" style="font-size:17px">“{E(q)}”</div>
<div style="font-size:13px;color:#08384C">오늘 동화책에서 만든 문장으로 대답할 수 있어요.</div></div>
<p class="muted" style="font-size:12px">아이 목소리는 피드백에만 쓰고 일정 기간 뒤 자동 삭제돼요. 보호자 동의 후 이용할 수 있어요.</p></div>""",
                    unsafe_allow_html=True)
        with st.expander("공유 메시지 미리보기"):
            st.code(record_message(child, unit, title, S.n_sent, S.notes), language=None)


{"shelf": screen_shelf, "start": screen_start, "story": screen_story, "milestone": screen_milestone,
 "book": screen_book}.get(S.screen, screen_shelf)()
