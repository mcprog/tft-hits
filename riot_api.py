import os
import requests
import time
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
API_KEY = os.environ.get("RIOT_API_KEY")
REGION = "americas"
BASE_URL = f"https://{REGION}.api.riotgames.com"

# Set 17 Prismatic Trait Thresholds
VALID_PRISMATICS = {
    "TFT17_Trait_DarkStar": 9,
    "TFT17_Trait_Meeple": 10,
    "TFT17_Trait_SpaceGroove": 10,
    "TFT17_Trait_Anima": 6,
    "TFT17_Trait_Mecha": 6,
    "TFT17_Trait_Shepherd": 7,
    "TFT17_Trait_Stargazer": 7
}

def debug(string):
    print(string, flush=True)

def make_request(url, headers, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        if response.status_code == 429:
            retry_time = int(response.headers.get('Retry-After', 10))
            debug(f"[429] Rate Limit Hit. Sleeping for {retry_time}s...")
            time.sleep(retry_time)
            continue
        return response
    return response

def get_account(game_name, tag_line):
    if not API_KEY:
        return None
    endpoint = f"{BASE_URL}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    headers = {"X-Riot-Token": API_KEY}
    response = make_request(endpoint, headers)
    if response.status_code == 200:
        return response.json()
    return None

def get_match_ids(puuid, count=90):
    if not API_KEY:
        return []
    endpoint = f"{BASE_URL}/tft/match/v1/matches/by-puuid/{puuid}/ids?start=0&count={count}"
    headers = {"X-Riot-Token": API_KEY}
    response = make_request(endpoint, headers)
    if response.status_code == 200:
        return response.json()
    return []

def get_single_match_detail(match_id, puuid):
    if not API_KEY:
        return None
    match_url = f"{BASE_URL}/tft/match/v1/matches/{match_id}"
    headers = {"X-Riot-Token": API_KEY}
    m_res = make_request(match_url, headers)
    if m_res.status_code != 200:
        return None
    data = m_res.json()
    info = data.get('info', {})
    if info.get("tft_set_number") != 17:
        return {"is_epic": False}
    participant = next((p for p in info.get('participants', []) if p['puuid'] == puuid), None)
    if not participant:
        return {"is_epic": False}
    
    active_prismatic_trait = None
    for trait in participant.get('traits', []):
        t_name = trait['name']
        if t_name in VALID_PRISMATICS and trait['num_units'] >= VALID_PRISMATICS[t_name]:
            active_prismatic_trait = t_name.replace("TFT17_Trait_", "")
            break

    summons_to_exclude = ["bia", "bayin", "swarmling", "meep", "meeplord"]
    high_cost_3stars = [
        u for u in participant.get('units', []) 
        if u['tier'] == 3 
        and u['rarity'] >= 4
        and not any(s in u.get('character_id', '').lower() for s in summons_to_exclude)
    ]

    if active_prismatic_trait or high_cost_3stars:
        processed_units = []
        for u in participant.get('units', []):
            raw_id = u.get('character_id', '').lower()
            img_url = f"https://raw.communitydragon.org/latest/game/assets/ux/tft/championsplashes/patching/{raw_id}_teamplanner_splash.tft_set17.png"
            processed_units.append({
                "character_id": u['character_id'].split('_')[-1],
                "tier": u['tier'],
                "image_url": img_url
            })
        return {
            "match_id": match_id,
            "placement": participant['placement'],
            "timestamp": info['game_datetime'],
            "readable_date": datetime.fromtimestamp(info['game_datetime'] / 1000).strftime('%b %d, %Y'),
            "has_prismatic": active_prismatic_trait is not None,
            "prismatic_name": active_prismatic_trait,
            "has_high_cost_3star": len(high_cost_3stars) > 0,
            "high_cost_units": [u['character_id'].split('_')[-1] for u in high_cost_3stars],
            "units": processed_units,
            "is_epic": True
        }
    return {"is_epic": False}