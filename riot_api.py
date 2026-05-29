import os
import requests
import time
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
API_KEY = os.environ.get("RIOT_API_KEY")

# --- Community Dragon Item Mapping ---
# We fetch the official TFT item dictionary on startup to dynamically map apiNames to exact asset URLs.
ITEM_URL_MAP = {}

def initialize_item_map():
    print("[INIT] Fetching Community Dragon TFT Item Map...", flush=True)
    try:
        url = "https://raw.communitydragon.org/latest/cdragon/tft/en_us.json"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            for item in data.get("items", []):
                api_name = item.get("apiName")
                icon_path = item.get("icon")
                if api_name and icon_path:
                    # CDragon internal paths look like: ASSETS/Maps/TFT/.../TFT_Item_BlueBuff.TFT_Set13.dds
                    # We lowercase it and replace the .dds extension with .png for the web asset.
                    clean_path = icon_path.lower().replace(".dds", ".png").replace(".tex", ".png")
                    
                    if clean_path.startswith('/'):
                        clean_path = clean_path[1:]
                        
                    ITEM_URL_MAP[api_name] = f"https://raw.communitydragon.org/latest/game/{clean_path}"
            print(f"[INIT] Loaded {len(ITEM_URL_MAP)} item URLs successfully.", flush=True)
        else:
            print("[INIT] Failed to load Community Dragon item map.", flush=True)
    except Exception as e:
        print(f"[INIT] Error loading item map: {e}", flush=True)

# Run once on server boot
initialize_item_map()


# Set 17 Prismatic Trait Thresholds
VALID_PRISMATICS = {
    "TFT17_Trait_DarkStar": 9,
    "TFT17_Trait_Meeple": 10,
    "TFT17_Trait_SpaceGroove": 10,
    "TFT17_Trait_Stargazer": 11
}

# Strict mapping of standard game modes allowed to process
QUEUE_MAP = {
    1090: "Normal",
    1100: "Ranked",
    1150: "Double Up",
    1160: "Double Up"
}

# Explicitly exclude Hyper Roll, Choncc's Treasure, Set Revivals, and Tocker's Trials variants
EXCLUDED_QUEUES = [1130, 1170, 1180, 1190, 1200]

# Maps frontend dropdown options to Riot's regional routing endpoints
REGION_TO_ROUTE = {
    "NA": "americas",
    "BR": "americas",
    "LAN": "americas",
    "LAS": "americas",
    "EUW": "europe",
    "EUNE": "europe",
    "TR": "europe",
    "RU": "europe",
    "KR": "asia",
    "JP": "asia",
    "OCE": "sea",
    "VN": "sea"
}

# Maps Match ID platform prefixes directly to their corresponding regional servers
MATCH_PREFIX_TO_ROUTE = {
    "NA1": "americas", "BR1": "americas", "LA1": "americas", "LA2": "americas",
    "EUW1": "europe", "EUNE1": "europe", "TR1": "europe", "RU1": "europe",
    "KR": "asia", "JP1": "asia",
    "OC1": "sea", "PH2": "sea", "SG2": "sea", "TH2": "sea", "TW2": "sea", "VN2": "sea"
}

# Tracks independent rate limit backoff expirations per regional route
ROUTE_BACKOFFS = {}

def get_route_for_region(region):
    """Returns the routing value tier for a given platform region code."""
    return REGION_TO_ROUTE.get(region.upper(), "americas")

def make_request(url, headers, max_retries=3):
    """Executes HTTP requests with region-specific, independent rate limit isolation and clean logging."""
    route = "americas"
    for r in list(REGION_TO_ROUTE.values()):
        if f"//{r}." in url:
            route = r
            break

    for attempt in range(max_retries):
        current_time = time.time()
        if route in ROUTE_BACKOFFS and current_time < ROUTE_BACKOFFS[route]:
            sleep_duration = ROUTE_BACKOFFS[route] - current_time
            print(f"[RATE LIMIT] Route '{route}' is cooling down. Pausing for {sleep_duration:.2f}s...", flush=True)
            time.sleep(sleep_duration)

        try:
            response = requests.get(url, headers=headers)
        except Exception:
            return None
        
        if response.status_code == 429:
            retry_time = int(response.headers.get('Retry-After', 10))
            print(f"[RATE LIMIT] 429 Hit on route '{route}'. Backing off for {retry_time}s.", flush=True)
            ROUTE_BACKOFFS[route] = time.time() + retry_time
            time.sleep(retry_time)
            continue
            
        return response
        
    return None

def get_account(name, tag, region="NA"):
    """Fetches account PUUID data and logs production search details."""
    print(f"[SEARCH] Player searched: {name}#{tag} in region: {region.upper()}", flush=True)
    
    route = get_route_for_region(region)
    if route == "sea":
        route = "asia"
        
    url = f"https://{route}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
    headers = {"X-Riot-Token": API_KEY}
    res = make_request(url, headers)
    
    if res and res.status_code == 200:
        return res.json()
    return None

def get_match_ids(puuid, count=20, start=0, region="NA"):
    """Collects recent match IDs for a player within their regional cluster."""
    route = get_route_for_region(region)
    url = f"https://{route}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?start={start}&count={count}"
    headers = {"X-Riot-Token": API_KEY}
    res = make_request(url, headers)
    
    if res and res.status_code == 200:
        return res.json()
    return []

def get_single_match_detail(match_id, target_puuid, region="NA"):
    """Processes match details against Set 17 high-roll performance criteria."""
    prefix = match_id.split('_')[0].upper()
    route = MATCH_PREFIX_TO_ROUTE.get(prefix, get_route_for_region(region))

    url = f"https://{route}.api.riotgames.com/tft/match/v1/matches/{match_id}"
    headers = {"X-Riot-Token": API_KEY}
    res = make_request(url, headers)
    
    if not res or res.status_code != 200:
        return {"is_epic": False}

    match_data = res.json()
    info = match_data.get("info", {})
    queue_id = info.get("queue_id")
    
    if info.get("tft_set_number") != 17 or queue_id in EXCLUDED_QUEUES:
        return {"is_epic": False}

    if queue_id not in QUEUE_MAP:
        return {"is_epic": False}

    participants = info.get('participants', [])
    participant = next((p for p in participants if p.get('puuid') == target_puuid), None)
    if not participant:
        return {"is_epic": False}

    # 1. Prismatic Trait Check
    active_p = None
    for t in participant.get('traits', []):
        t_name = t.get('name', '')
        if t_name in VALID_PRISMATICS and t.get('num_units', 0) >= VALID_PRISMATICS[t_name]:
            active_p = t_name.replace("TFT17_Trait_", "")
            break

    # Bugfix Override: Check for Bardfollower summon data components.
    if not active_p:
        for u in participant.get('units', []):
            if "bardfollower" in u.get('character_id', '').lower():
                active_p = "Meeple"
                break

    # 2. Epic 3-Star Check (Strictly exclude generic sub-summons as high-roll triggers)
    valid_3stars = [
        u for u in participant.get('units', []) 
        if u['tier'] == 3 and u['rarity'] >= 4 
        and "summon" not in u.get('character_id', '').lower()
    ]

    # Only continue if the game meets true epic high-roll criteria
    if active_p or valid_3stars:
        processed_units = []
        for u in participant.get('units', []):
            raw_id = u.get('character_id', '').lower()
            
            # Inject custom trait icon if the unit is a Meeple spawn
            if "bardfollower" in raw_id:
                img_url = "https://raw.communitydragon.org/latest/game/assets/ux/traiticons/trait_icon_17_astronaut.tft_set17.png"
            else:
                img_url = f"https://raw.communitydragon.org/latest/game/assets/ux/tft/championsplashes/patching/{raw_id}_teamplanner_splash.tft_set17.png"
            
            # Utilize the initialized map to guarantee correct item paths
            item_urls = []
            for item_name in u.get('itemNames', []):
                item_url = ITEM_URL_MAP.get(item_name)
                if item_url:
                    item_urls.append(item_url)
            
            processed_units.append({
                "character_id": u['character_id'].split('_')[-1],
                "tier": u['tier'],
                "image_url": img_url,
                "items": item_urls,
                "is_summon": "summon" in raw_id or "follower" in raw_id
            })

        return {
            "match_id": match_id,
            "placement": participant['placement'],
            "game_mode": QUEUE_MAP[queue_id],
            "readable_date": datetime.fromtimestamp(info['game_datetime'] / 1000).strftime('%b %d, %Y'),
            "has_prismatic": active_p is not None,
            "prismatic_name": active_p,
            "has_high_cost_3star": len(valid_3stars) > 0,
            "high_cost_units": [u['character_id'].split('_')[-1] for u in valid_3stars],
            "units": processed_units,
            "is_epic": True
        }

    return {"is_epic": False}