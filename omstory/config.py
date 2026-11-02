"""
config.py — 이야기 분량·발화량 기준 (한 곳에서 조절)

- BASE_PAGES   : 기본 이야기 페이지 수 (오늘의 주요 표현으로 시작하는 '오늘의 미션')
- MAX_PAGES    : 한 편의 최대 페이지 수 (기본 + [다음 페이지 쓰기]로 이어 쓴 페이지)
- GOAL_SENTENCES: 오늘의 목표 — 아이가 영어로 말한 문장 수
- DAILY_STORIES: 하루에 만들 수 있는 동화책 수 (과몰입·비용 관리)
- WACKY_MAX_SENTENCES / WACKY_MAX_WORDS: 캐릭터 한 번 대사 길이 (아이가 더 많이 말하도록)
"""
BASE_PAGES = 3
MAX_PAGES = 8
GOAL_SENTENCES = 5
DAILY_STORIES = 3
WACKY_MAX_SENTENCES = 3
WACKY_MAX_WORDS = 9
