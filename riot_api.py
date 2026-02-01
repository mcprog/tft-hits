import os
import requests
from dotenv import load_dotenv

# Pattern B: Load config immediately upon import
load_dotenv()
API_KEY = os.environ.get("RIOT_API_KEY")

# Constants
REGION = "americas"
BASE_URL = f"https://{REGION}.api.riotgames.com"

def get_account(game_name, tag_line):
    """
    Fetches account data. Returns JSON dict if found, None if failed.
    """
    if not API_KEY:
        print("Error: API Key missing.")
        return None

    endpoint = f"{BASE_URL}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    headers = { "X-Riot-Token": API_KEY }

    response = requests.get(endpoint, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        # Log error to console for debugging, but return None to the app
        print(f"API Error {response.status_code}: {response.text}")
        return None

def get_epic_matches(puuid, count=20):
    if not API_KEY or not puuid:
        return []

    headers = {"X-Riot-Token": API_KEY}
    match_ids_url = f"{BASE_URL}/tft/match/v1/matches/by-puuid/{puuid}/ids?count={count}"
    
    match_ids_res = requests.get(match_ids_url, headers=headers)
    if match_ids_res.status_code != 200:
        return []
    
    match_ids = match_ids_res.json()
    epic_games = []

    # Strict Set 16 Prismatic definitions
    VALID_PRISMATICS = {
        "TFT16_Bilgewater": 10,
        "TFT16_Demacia": 11,
        "TFT16_Ionia": 10,
        "TFT16_Noxus": 10,
        "TFT16_Shurima": 4, # Specific Set 16 high-tier
        "TFT16_Yordle": 10
    }
    ALLOWED_QUEUES = [1090, 1100] # Normal, Ranked

    for match_id in match_ids:
        detail_res = requests.get(f"{BASE_URL}/tft/match/v1/matches/{match_id}", headers=headers)
        if detail_res.status_code != 200: continue
            
        match_data = detail_res.json()
        info = match_data.get('info', {})
        
        # 1. Filter: Set 16 and Normal/Ranked only
        if info.get("tft_set_number") != 16 or info.get("queue_id") not in ALLOWED_QUEUES:
            continue

        participant = next((p for p in info.get('participants', []) if p['puuid'] == puuid), None)
        if not participant: continue

        # 2. Identify specific Prismatic Trait (if any)
        active_prismatic_trait = None
        for trait in participant.get('traits', []):
            name = trait['name']
            if name in VALID_PRISMATICS and trait['num_units'] >= VALID_PRISMATICS[name]:
                # Special check: If it's Noxus, we MUST see the 4-star Atakhan to call it Prismatic
                if name == "TFT16_Noxus":
                    is_noxus_10 = any(u['tier'] == 4 for u in participant.get('units', []) if "Atakhan" in u['character_id'])
                    if not is_noxus_10:
                        continue 
                
                active_prismatic_trait = name.split('_')[-1] 
                break

        # 3. Check for 3-Star 4/5 Costs
        high_cost_3stars = [
            u for u in participant.get('units', []) 
            if u['tier'] == 3 
            and u['rarity'] >= 4 
            and "Atakhan" not in u.get('character_id', '')
        ]

        # 3.5 add images to units
        processed_units = []
        for u in participant.get('units', []):
            # character_id is often "TFT16_Amumu", we need the lowercased version for the URL
            raw_id = u.get('character_id', '').lower()
            
            # Community Dragon usually expects the filename without set prefix for some assets, 
            # but for Set 16 splashes, the full ID is often required.
            img_url = f"https://raw.communitydragon.org/latest/game/assets/ux/tft/championsplashes/patching/{raw_id}_square.tft_set16.png"
            
            processed_units.append({
                "character_id": u['character_id'].split('_')[-1], # e.g., "Amumu"
                "tier": u['tier'],
                "image_url": img_url
            })

        # 4. If either condition is met, add to list
        if active_prismatic_trait or high_cost_3stars:
            epic_games.append({
                "match_id": match_id,
                "placement": participant['placement'],
                "has_prismatic": active_prismatic_trait is not None,
                "prismatic_name": active_prismatic_trait,
                "has_high_cost_3star": len(high_cost_3stars) > 0,
                # Store all units for the final board display
                "all_units": processed_units
            })
                    
    return epic_games
