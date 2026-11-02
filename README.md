# Oh! My Story

**아이의 상상이 이야기가 되는 초등 맞춤형 AI 스피킹 스토리**
*Oh! My Speaking 교재 연계형 AI 말하기 짝 서비스 — 작동 데모 (Oh! My Speaking 6 · Unit 01 "I like swimming best.")*

단원을 마친 아이가 오늘 배운 표현으로 **Wacky와 한 페이지씩 동화책을 써요.**
Wacky는 선생님이 아니라 **공동 작가**예요. 아이 말을 받아 이야기를 잇고, 다음 질문과 고를 거리를 줘요.
교재 표현은 채점 기준이 아니라 **이야기 재료**예요. 한국어로 말해도 영어 문장으로 바꿔 주고, 따라 말하면 **내가 만든 표현**으로 쌓여요.

> ⚠️ 이 저장소에는 쎄듀 교재 자료(TG 내용, 교재 MP3)가 들어 있어요. **반드시 비공개(Private) 저장소**로 올리고,
> 외부 AI 서비스(OpenAI 등)를 쓰기 전에 회사 승인을 받으세요. AI에 보내는 것은 표현·단어 텍스트뿐이고, MP3는 보내지 않아요.

## 화면 흐름 (디자인 캔버스 "Oh! My Story 앱 디자인"과 같은 순서)

| # | 화면 | 내용 |
|---|---|---|
| 1 | 단원 책장 | 오늘 배운 단원, 6권 8개 단원 책장 (01 완성 · 02~04 AI 체험 · 05~08 수업 후 열림), 내가 만든 동화책 |
| 2 | 오늘의 주요 표현 · 이야기 씨앗 | "I enjoy ~ / I like ~ best" 카드(교재 원음), 씨앗 3개 중 고르기, 단어 서랍(발음 듣기) |
| 3 | 이야기 페이지 | 왼쪽: 살아 있는 장면(배경+캐릭터+쌓이는 스티커+마법 상자)과 동화책 문장 · 오른쪽: 캐릭터 반응, Wacky 질문, 고를 거리, 말하기·쓰기 |
| 3-1 | 한국어로 말해도 OK | 내 말 → 영어 문장 → 따라 말하기 → 내가 만든 표현 |
| 4 | 오늘의 목표 달성 | 기본 3페이지 완성 → [다음 페이지 쓰기](최대 8페이지) 또는 [동화책 완성하기] |
| 5 | 나의 동화책 완성 · 오늘의 이야기 기록 | 표지, 말한 문장 수, 내가 만든 표현, 페이지 넘겨보기 / 누구나 보는 중립적인 기록 + 공유 |

사이드바의 **🔍 시연용 보기**를 켜면 페이지마다 Wacky가 참고한 교재 내용, 적용한 지침(T1~T7), 검사 결과가 보여요.

## 빠른 시작

```bash
pip install -r requirements.txt
streamlit run app.py
```

- 키가 없어도 Unit 01은 끝까지 동작해요 (편집자 문장 = 규칙 기반 모드).
- 실제 AI를 켜려면 `OPENAI_API_KEY`를 설정하세요 (Streamlit Cloud는 앱 설정 Secrets). AI가 켜지면 Unit 02~04 "AI 체험"도 열려요.
- 마이크 입력은 `faster-whisper`가 설치돼 있으면 나타나요. 시연 때는 고를 거리 버튼이나 쓰기 입력을 기본으로 쓰는 걸 권해요.

## 핵심 설계

| 구성 | 내용 | 위치 |
|---|---|---|
| **지침 가이드 프롬프트** | 공동 작가 역할 + 이야기 끌어내기(Yes-and, 고를 거리, 궁금증) + TG Teaching Tips T1~T7 + 한국어 처리 + 출력 형식 + 예시 | [`prompts/wacky_tutor_system.md`](prompts/wacky_tutor_system.md) · 설명 [`docs/PROMPT_GUIDE.md`](docs/PROMPT_GUIDE.md) |
| **분량·발화량 기준** | 기본 3페이지 · 최대 8페이지 · 목표 영어 문장 5개 · 하루 3편 | `omstory/config.py` |
| **RAG** | Unit ID로 교재 내용(주요 표현·어휘·Useful Q/E) 조회 + 배운 단원 | `kb/units.json`, `omstory/rag.py` |
| **이야기 씨앗** | 단원별 편집자 계획(3개 씨앗 × 기본 3페이지) | `kb/units.json` → `seeds` |
| **생성 → 검사 → 재생성** | 지침 위반 시 1회 재생성, 그래도 안 되면 편집자 문장으로 대체 | `omstory/story.py`, `omstory/guard.py` |
| **한국어 → 영어** | AI가 아이 말 그대로 영어로 / 키 없으면 Word List 한글 뜻 사전 | `omstory/korean.py` |
| **안전 필터** | 위험한 말 → 다정한 이야기로, 같은 질문 다시 | `omstory/guard.py` |
| **살아 있는 장면** | 매 페이지 배경+캐릭터+스티커+마법 상자 합성 (AI 그림 없음) | `omstory/scene_render.py` |
| **교재 원음 · 캐릭터 목소리** | 주요 표현·단어·질문은 교재 원음, 캐릭터 대사는 캐릭터별 TTS | `kb/audio/b6_u01/`, `omstory/textbook_audio.py`, `omstory/speech.py` |
| **화면** | 디자인 캔버스 색·글꼴·카드를 CSS로 옮김 | `app.py`, `omstory/ui.py` |

## 테스트와 평가

```bash
pip install -r requirements-dev.txt
python -m pytest -q          # 이야기 흐름·한국어 전환·안전 필터·검사→재생성 (가짜 AI, 키 필요 없음)
python eval_poc.py --rule    # 품질 지표 → results/eval_rule.md
python eval_poc.py           # OPENAI_API_KEY가 있으면 실제 AI로 평가
```

현재 결과(편집자 문장, 이야기 3편 · 입력 27회): 지침 통과 100%, 다음 질문+고를 거리 100%, 한국어 전환 100%, 안전 필터 100%,
이야기 1편당 아이 영어 문장 6.0개 → [`results/eval_rule.md`](results/eval_rule.md). 실제 판단은 AI 모드와 아이 녹음으로 해야 해요.

## 폴더 구조

```
ohmystory/
├── app.py                      # Streamlit 화면 (책장 → 주요 표현·씨앗 → 이야기 → 목표 달성 → 동화책·기록)
├── eval_poc.py                 # 품질 지표 자동 측정 → results/
├── prompts/wacky_tutor_system.md  # ★ Wacky 지침 가이드 (AI에 그대로 전달)
├── omstory/
│   ├── story.py                # ★ 한 페이지: 안전 필터 → 한국어 전환 → AI 생성 → 검사 → 재생성 → 대체
│   ├── prompting.py            # 지침 + RAG + 씨앗·페이지 정보로 메시지 만들기
│   ├── guard.py                # 안전 필터, AI 결과 검사
│   ├── korean.py               # 한국어 → 영어 (키 없을 때)
│   ├── config.py               # 분량·발화량 기준
│   ├── rag.py                  # 교재 지식베이스 조회, 씨앗
│   ├── analysis.py             # 아이디어 추출, 주요 표현 감지, 발화량
│   ├── scene_render.py         # 살아 있는 장면 합성
│   ├── ui.py                   # 디자인 CSS·HTML 조각
│   ├── textbook_audio.py       # 대사 ID → 교재 원음
│   ├── speech.py               # STT(faster-whisper), 캐릭터별 TTS(edge-tts)
│   ├── scenes.py / card.py / share.py / pipeline.py
├── kb/units.json               # 6권 8개 단원 (Unit 01: 씨앗·한글 뜻·한국어 사전 포함)
├── kb/audio/b6_u01/            # 교재 원음 (대화문 + 문장 클립 39개 + index.json)
├── assets/                     # 캐릭터, 배경, 스티커 (교재 원화로 같은 이름 교체 가능)
├── tools/                      # split_audio.py(교재 MP3 분할), draw_assets.py(그림 생성)
├── tests/test_story.py
└── docs/                       # PROMPT_GUIDE.md, 사용 흐름도, 구조도
```

## 교재 자료 출처

| 자료 | 쓰인 곳 |
|---|---|
| Teacher's Guide p.4–5 Scope & Sequence | 6권 8개 단원 지식베이스 |
| Teacher's Guide p.6–7 Teaching Tips | 지침 가이드 T1~T7 |
| Teacher's Guide p.9–16 Unit 01 | 주요 표현, Useful Q/E, 대화문, 트랙 순서 |
| Word List | 어휘 한글 뜻, 한국어 → 영어 사전 |
| Flashcards, Worksheet A/B | 어휘 목록 확인, 스티커 항목 |
| 교재 MP3 Track 01–06 | 교재 원음 클립 (Track 07–09는 교재 Step 4 평가용이라 사용 안 함) |

## 알려진 한계

- **교재 원음 클립**은 무음 구간으로 자동 분할했어요. 서비스 전에 사람이 들어보고 확인해야 해요 (`kb/audio/b6_u01/index.json`).
- **키 없는 한국어 전환**은 교재 단어 범위 안에서만 돼요 (예: "모래성에 꽃게 가족" → 모래성만 인식). 교재 밖 상상은 AI가 있어야 해요.
- **안전 필터**는 PoC용 최소 목록이에요. 실제 서비스는 아동용 금칙어 사전과 분류 모델이 필요해요.
- **실제 AI 품질**은 이 저장소에서 측정하지 않았어요 (키 없음). 흐름은 가짜 AI 테스트로 확인했어요.
- 디자인 글꼴(Jua·Nunito)은 Google Fonts에서 불러와요. 인터넷이 막힌 환경에서는 기본 글꼴로 보여요.
- 캐릭터 TTS 목소리는 교재 성우와 같은 목소리가 아니에요. edge-tts는 PoC용이에요.
