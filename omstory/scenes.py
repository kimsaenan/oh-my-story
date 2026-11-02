"""
scenes.py — 아이 말에 따라 바뀌는 배경(장면) 고르기

단원 기본 배경(교실, 방 등)에서 시작하고, 아이가 상상한 장소가 나오면 그 배경으로 바꾼다.
예) "It's a rocket." → 우주 / "They're fish." → 바닷속 / "There's a candy lamp." → 사탕 나라
LLM이 연결돼 있으면 LLM이 고른 장면을 쓰고, 없으면 아래 키워드로 고른다.
"""
from __future__ import annotations

import re

SCENE_LABELS = {
    "classroom": "교실", "toyroom": "장난감 방", "picnic": "소풍", "park": "공원", "home": "집",
    "zoo": "동물원", "petshop": "펫 가게", "room": "내 방",
    "space": "우주", "underwater": "바닷속", "candy": "사탕 나라", "beach": "바닷가",
    "castle": "성", "forest": "숲", "snow": "눈 나라", "sky": "구름 위",
}

# 상상 장면 키워드 (단어 경계로 찾음). 'rainbow crayon'처럼 물건을 꾸미는 말에 반응하지 않도록 장소·상징어 위주
KEYWORDS = {
    "space": ["moon", "space", "star", "stars", "planet", "rocket", "mars", "galaxy", "alien", "astronaut", "spaceship"],
    "underwater": ["sea", "ocean", "underwater", "diving", "snorkeling", "dive", "snorkel", "fish", "shark", "sharks", "whale", "whales", "mermaid", "octopus", "dolphin", "dolphins", "turtle", "turtles"],
    "candy": ["candy", "chocolate", "lollipop", "cookie", "jelly", "sweet", "sweets"],
    "beach": ["beach", "sand", "sandcastle", "sandcastles", "seashell", "seashells", "volleyball", "sunbathing", "surf", "surfing", "surfboard", "swim", "swimming", "island", "summer"],
    "castle": ["castle", "princess", "prince", "king", "queen", "knight", "dragon", "palace"],
    "forest": ["forest", "jungle", "woods", "mushroom", "treehouse", "fairy"],
    "snow": ["snow", "snowman", "snowmen", "snowball", "snowballs", "ski", "skiing", "snowboard", "snowboarding", "skating", "winter", "penguin", "polar"],
    "sky": ["sky", "cloud", "clouds", "balloon", "airplane", "plane"],
}
FANTASY_SCENES = list(KEYWORDS)


def detect_scene(*texts: str) -> str:
    """아이 말·아이디어에서 상상 장면을 찾는다. 없으면 빈 문자열."""
    joined = " ".join(t for t in texts if t).lower()
    best, pos = "", -1
    for scene, words in KEYWORDS.items():
        for w in words:
            for m in re.finditer(rf"\b{re.escape(w)}\b", joined):
                if m.start() > pos:  # 가장 마지막에 나온 장소를 우선 (이야기가 이동한 곳)
                    best, pos = scene, m.start()
    return best
