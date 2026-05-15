import os
import requests
import time
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
API_KEY = os.environ.get("RIOT_API_KEY")
REGION = "americas"
BASE_URL = f"https://{REGION}.api.riotgames.com"

VALID_PRISMATICS = {
    "TFT17_Trait_DarkStar": 9,
    "TFT17_Trait_Meeple": 10,
    "TFT17_Trait_SpaceGroove": 10,
    "TFT17_Trait_Anima": 6,
    "TFT17_Trait_Mecha": 6,
    "TFT17_Trait_Shepherd": 7,
    "TFT17_Trait_Stargazer": 7
}

QUEUE_MAP = {1090: "Normal", 1100: "Ranked", 1150: "Double Up", 1160: "Double Up"}
EXCLUDED_QUEUES = [1130, 1170, 1180, 1190]

def make_request(url, headers, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        if response.status_code == 429:
            retry_time = int(response.headers.get('Retry-After', 10))
            time.sleep(retry_time)
            continue
        return response
    return response

def get_account(game_name, tag_line):
    endpoint = f"{BASE_URL}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    headers = {"X-Riot-Token": API_KEY}
    res = make_request(endpoint, headers)
    return res.json() if res.status_code == 200 else None

def get_match_ids(puuid, count=90, start=0):
    endpoint = f"{BASE_URL}/tft/match/v1/matches/by-puuid/{puuid}/ids?start={start}&count={count}"
    headers = {"X-Riot-Token": API_KEY}
    res = make_request(endpoint, headers)
    return res.json() if res.status_code == 200 else []

def get_single_match_detail(match_id, puuid):
    match_url = f"{BASE_URL}/tft/match/v1/matches/{match_id}"
    headers = {"X-Riot-Token": API_KEY}
    res = make_request(match_url, headers)
    if res.status_code != 200: return None

    info = res.json().get('info', {})
    if info.get("queue_id") in EXCLUDED_QUEUES or info.get("tft_set_number") != 17:
        return {"is_epic": False}

    participant = next((p for p in info.get('participants', []) if p['puuid'] == puuid), None)
    if not participant: return {"is_epic": False}

    # 1. Prismatic Check
    active_p = None
    for t in participant.get('traits', []):
        if t['name'] in VALID_PRISMATICS and t['num_units'] >= VALID_PRISMATICS[t['name']]:
            active_p = t['name'].replace("TFT17_Trait_", "")
            break

    # 2. Epic 3-Star Check (Strictly exclude summons as a trigger)
    valid_3stars = [
        u for u in participant.get('units', []) 
        if u['tier'] == 3 and u['rarity'] >= 4 
        and "summon" not in u.get('character_id', '').lower()
    ]

    # Only continue if the game is Epic by OTHER criteria
    if active_p or valid_3stars:
        processed_units = []
        for u in participant.get('units', []):
            raw_id = u.get('character_id', '').lower()
            # We include summons here so they show on the board
            img_url = f"https://raw.communitydragon.org/latest/game/assets/ux/tft/championsplashes/patching/{raw_id}_teamplanner_splash.tft_set17.png"
            
            processed_units.append({
                "character_id": u['character_id'].split('_')[-1],
                "tier": u['tier'],
                "image_url": img_url,
                "is_summon": "summon" in raw_id
            })

        return {
            "match_id": match_id,
            "placement": participant['placement'],
            "game_mode": QUEUE_MAP.get(info.get("queue_id"), "Other"),
            "readable_date": datetime.fromtimestamp(info['game_datetime'] / 1000).strftime('%b %d, %Y'),
            "has_prismatic": active_p is not None,
            "prismatic_name": active_p,
            "has_high_cost_3star": len(valid_3stars) > 0,
            "high_cost_units": [u['character_id'].split('_')[-1] for u in valid_3stars],
            "units": processed_units,
            "is_epic": True
        }
    return {"is_epic": False}