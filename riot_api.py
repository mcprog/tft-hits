import os
import requests
import time
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
API_KEY = os.environ.get("RIOT_API_KEY")
REGION = "americas"
BASE_URL = f"https://{REGION}.api.riotgames.com"

def debug(string):
    print(string, flush=True)

def make_request(url, headers, max_retries=3):
    """
    Makes a request and strictly obeys the 'Retry-After' header if a 429 is hit.
    """
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        
        if response.status_code == 429:
            # Riot sends 'Retry-After' in seconds (as a string)
            # Default to 10s if missing for safety
            retry_time = int(response.headers.get('Retry-After', 10))
            
            debug(f"[429] Rate Limit Hit. Sleeping for {retry_time}s (Attempt {attempt + 1})...")
            time.sleep(retry_time)
            continue  # Retry the loop
            
        # If 200, 403, 404, etc., return immediately to caller
        return response
    return response

def get_account(game_name, tag_line):
    if not API_KEY:
        return None
    endpoint = f"{BASE_URL}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    headers = { "X-Riot-Token": API_KEY }
    response = make_request(endpoint, headers)
    return response.json() if response.status_code == 200 else None

# UPDATED: Added 'start' parameter (defaults to 0)
def get_epic_matches(puuid, start=0, count=20):
    if not API_KEY or not puuid:
        return []

    headers = {"X-Riot-Token": API_KEY}
    # UPDATED: Pass 'start' to the Riot API URL
    match_ids_url = f"{BASE_URL}/tft/match/v1/matches/by-puuid/{puuid}/ids?start={start}&count={count}"
    
    match_ids_res = make_request(match_ids_url, headers)
    if match_ids_res.status_code != 200:
        debug(f"API Error (List): {match_ids_res.status_code} - {match_ids_res.text}")
        return []
    
    match_ids = match_ids_res.json()
    epic_games = []

    VALID_PRISMATICS = {
        "TFT16_Bilgewater": 10,
        "TFT16_Demacia": 11,
        "TFT16_Ionia": 10,
        "TFT16_Noxus": 10,
        "TFT16_Shurima": 4,
        "TFT16_Yordle": 10
    }
    ALLOWED_QUEUES = [1090, 1100]

    debug(f"Fetching matches {start} to {start+count}...")

    for match_id in match_ids:
        time.sleep(0.05)
        detail_res = make_request(f"{BASE_URL}/tft/match/v1/matches/{match_id}", headers)
        if detail_res.status_code != 200: continue
            
        match_data = detail_res.json()
        info = match_data.get('info', {})
        
        if info.get("tft_set_number") != 16 or info.get("queue_id") not in ALLOWED_QUEUES:
            continue

        participant = next((p for p in info.get('participants', []) if p['puuid'] == puuid), None)
        if not participant: continue

        active_prismatic_trait = None
        for trait in participant.get('traits', []):
            name = trait['name']
            if name in VALID_PRISMATICS and trait['num_units'] >= VALID_PRISMATICS[name]:
                active_prismatic_trait = name.split('_')[-1] 
                break

        # 3. Check for 3-Star 4/5 Costs (PRESERVED ATAKHAN RULE)
        high_cost_3stars = [
            u for u in participant.get('units', []) 
            if u['tier'] == 3 
            and u['rarity'] >= 4
            and "atakhan" not in u.get('character_id', '').lower() # Atakhan exclusion
        ]

        processed_units = []
        for u in participant.get('units', []):
            raw_id = u.get('character_id', '').lower()
            img_url = f"https://raw.communitydragon.org/latest/game/assets/ux/tft/championsplashes/patching/{raw_id}_square.tft_set16.png"
            
            processed_units.append({
                "character_id": u['character_id'].split('_')[-1],
                "tier": u['tier'],
                "image_url": img_url
            })

        if active_prismatic_trait or high_cost_3stars:
            epic_games.append({
                "match_id": match_id,
                "placement": participant['placement'],
                "timestamp": info['game_datetime'],
                "readable_date": datetime.fromtimestamp(info['game_datetime'] / 1000).strftime('%b %d, %Y'),
                "has_prismatic": active_prismatic_trait is not None,
                "prismatic_name": active_prismatic_trait,
                "has_high_cost_3star": len(high_cost_3stars) > 0,
                "all_units": processed_units
            })
            
    epic_games.sort(key=lambda x: x['timestamp'], reverse=True)               
    return epic_games