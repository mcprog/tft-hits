import os
import re
import requests
import time
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
API_KEY = os.environ.get("RIOT_API_KEY")

# The TFT set this tracker processes. Matches from any other set are ignored.
CURRENT_SET = 18

CDRAGON_GAME_BASE = "https://raw.communitydragon.org/latest/game/"

# --- Community Dragon Item and Champion Mapping ---
# We fetch the official TFT data dictionary on startup to dynamically map apiNames to exact asset URLs.
ITEM_URL_MAP = {}
# Champion portraits keyed by exact apiName (e.g. DA_18_Ahri)
CHAMPION_URL_MAP = {}
# Champion portraits keyed by cleaned lowercase name (e.g. ahri), used when the match apiName differs from CDragon
CHAMPION_URL_BY_NAME = {}

# Matches internal apiName tokens that carry no champion or trait identity (DA, TFT18, Set18, Trait, 18)
SET_PREFIX_TOKEN = re.compile(r'^(?:da|tft\d*|set\d+|trait|\d+)$', re.IGNORECASE)


def clean_api_name(api_name):
    """Strips Set 18 internal prefixes and variant suffixes from a trait or unit apiName.

    DA_18_Elderwood -> Elderwood, DA_Vi18 -> Vi, DA_18_MasterYi_AD -> MasterYi,
    DA_Lux18_Blossom -> Lux, TFT18_Trait_Blossom -> Blossom
    """
    if not api_name:
        return ''

    set_suffix = str(CURRENT_SET)
    for token in api_name.split('_'):
        if not token or SET_PREFIX_TOKEN.match(token):
            continue
        # Set 18 units often carry the set number as a suffix (DA_Vi18, DA_KogMaw18_AD)
        if token.endswith(set_suffix) and len(token) > len(set_suffix):
            token = token[:-len(set_suffix)]
        # The first identifying token is the name; later tokens are variants (_AD, _AP, _Blossom)
        return token

    return api_name


def cdragon_asset_url(icon_path):
    """Converts a CDragon internal asset path (.tex/.dds) into a public .png URL."""
    # CDragon internal paths look like: ASSETS/Maps/TFT/.../TFT_Item_BlueBuff.TFT_Set13.dds
    # We lowercase it and replace the .dds extension with .png for the web asset.
    clean_path = icon_path.lower().replace(".dds", ".png").replace(".tex", ".png")

    if clean_path.startswith('/'):
        clean_path = clean_path[1:]

    return f"{CDRAGON_GAME_BASE}{clean_path}"


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
                    ITEM_URL_MAP[api_name] = cdragon_asset_url(icon_path)
            print(f"[INIT] Loaded {len(ITEM_URL_MAP)} item URLs successfully.", flush=True)

            # Champion portraits for the current set come from the same dictionary
            current_set = data.get("sets", {}).get(str(CURRENT_SET), {})
            for champ in current_set.get("champions", []):
                api_name = champ.get("apiName")
                icon_path = champ.get("squareIcon") or champ.get("tileIcon")
                if api_name and icon_path:
                    champ_url = cdragon_asset_url(icon_path)
                    CHAMPION_URL_MAP[api_name] = champ_url
                    CHAMPION_URL_BY_NAME.setdefault(clean_api_name(api_name).lower(), champ_url)
            print(f"[INIT] Loaded {len(CHAMPION_URL_MAP)} Set {CURRENT_SET} champion URLs successfully.", flush=True)
        else:
            print("[INIT] Failed to load Community Dragon item map.", flush=True)
    except Exception as e:
        print(f"[INIT] Error loading item map: {e}", flush=True)

# Run once on server boot
initialize_item_map()


def get_champion_image_url(character_id):
    """Resolves a unit's portrait from the CDragon champion map, falling back to the team planner splash."""
    if character_id in CHAMPION_URL_MAP:
        return CHAMPION_URL_MAP[character_id]

    clean_id = clean_api_name(character_id).lower()
    if clean_id in CHAMPION_URL_BY_NAME:
        return CHAMPION_URL_BY_NAME[clean_id]

    return f"{CDRAGON_GAME_BASE}assets/ux/tft/championsplashes/patching/tft{CURRENT_SET}_{clean_id}_teamplanner_splash.png"


# Set 18 Prismatic Trait Thresholds (CDragon apiName -> units required for the Prismatic tier)
VALID_PRISMATICS = {
    "DA_18_Blossom": 11,
    "DA_18_Elderwood": 11
}

# Thresholds keyed by cleaned lowercase trait name, so prefix variants still match
PRISMATIC_THRESHOLDS = {clean_api_name(name).lower(): units for name, units in VALID_PRISMATICS.items()}

# Minimum match API rarity that counts as a 4-cost or 5-cost unit.
# Set 18 reports rarity as cost minus one (4-cost = 3, 5-cost = 4). Older sets used 4 and 6, which also pass.
HIGH_COST_MIN_RARITY = 3

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
    """Processes match details against Set 18 high-roll performance criteria."""
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

    if info.get("tft_set_number") != CURRENT_SET or queue_id in EXCLUDED_QUEUES:
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
        trait_name = clean_api_name(t.get('name', ''))
        threshold = PRISMATIC_THRESHOLDS.get(trait_name.lower())
        if threshold and t.get('num_units', 0) >= threshold:
            active_p = trait_name
            break

    # 2. Epic 3-Star Check (Strictly exclude generic sub-summons as high-roll triggers)
    valid_3stars = [
        u for u in participant.get('units', [])
        if u['tier'] == 3 and u['rarity'] >= HIGH_COST_MIN_RARITY
        and "summon" not in u.get('character_id', '').lower()
    ]

    # Only continue if the game meets true epic high-roll criteria
    if active_p or valid_3stars:
        processed_units = []
        for u in participant.get('units', []):
            character_id = u.get('character_id', '')
            raw_id = character_id.lower()
            img_url = get_champion_image_url(character_id)

            # Utilize the initialized map to guarantee correct item paths
            item_urls = []
            for item_name in u.get('itemNames', []):
                item_url = ITEM_URL_MAP.get(item_name)
                if item_url:
                    item_urls.append(item_url)

            processed_units.append({
                "character_id": clean_api_name(character_id),
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
            "high_cost_units": [clean_api_name(u['character_id']) for u in valid_3stars],
            "units": processed_units,
            "is_epic": True
        }

    return {"is_epic": False}
