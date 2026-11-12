import pytest
import os
import time
import js2py
from unittest.mock import patch, MagicMock

import app
import riot_api

from riot_api import (
    CURRENT_SET,
    VALID_PRISMATICS,
    clean_api_name,
    get_champion_image_url,
    get_account,
    get_match_ids,
    get_single_match_detail,
    make_request
)

# Flask Endpoints

@pytest.fixture
def client():
    app.app.config['TESTING'] = True
    app.app.secret_key = 'test_secret'
    with app.app.test_client() as client:
        yield client

def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Dishsoap" in response.data

def test_games_get_route(client):
    response = client.get('/games')
    assert response.status_code == 200

def test_games_post_invalid_format(client):
    response = client.post('/games', data={'username': 'InvalidUser', 'region': 'NA'})
    assert response.status_code == 200
    assert b"Invalid format" in response.data

@patch('riot_api.get_account')
def test_games_post_valid_redirect(mock_get_account, client):
    response = client.post('/games', data={'username': 'Dishsoap#NA3', 'region': 'NA'})
    assert response.status_code == 302
    assert "games/Dishsoap-NA3" in response.headers['Location']

@patch('riot_api.get_account')
@patch('riot_api.get_match_ids')
def test_games_user_route_success(mock_get_match_ids, mock_get_account, client):
    mock_get_account.return_value = {'puuid': 'mock-puuid-123'}
    mock_get_match_ids.return_value = ['NA1_12345', 'NA1_67890']
    response = client.get('/games/Dishsoap-NA3?region=NA')
    assert response.status_code == 200
    assert b"mock-puuid-123" in response.data

def test_games_user_route_invalid_format(client):
    response = client.get('/games/InvalidFormatNoDash')
    assert response.status_code == 200
    assert b"Invalid URL format" in response.data

@patch('riot_api.get_account')
def test_games_user_route_not_found(mock_get_account, client):
    mock_get_account.return_value = None
    response = client.get('/games/NoPlayer-TAG?region=NA')
    assert response.status_code == 200
    assert b"Account not found" in response.data

@patch('riot_api.get_account')
def test_games_user_route_system_error(mock_get_account, client):
    mock_get_account.side_effect = Exception("Database Down")
    response = client.get('/games/Dishsoap-NA3?region=NA')
    assert response.status_code == 200
    assert b"System Error: Database Down" in response.data

def test_api_match_details_missing_puuid(client):
    response = client.get('/api/match_details/NA1_123')
    assert response.status_code == 400

@patch('riot_api.get_single_match_detail')
def test_api_match_details_success(mock_get_detail, client):
    mock_get_detail.return_value = {'is_epic': True, 'placement': 1}
    response = client.get('/api/match_details/NA1_123?puuid=test-puuid')
    assert response.status_code == 200
    assert response.json['placement'] == 1

def test_api_get_more_ids_missing_puuid(client):
    response = client.get('/api/get_more_ids')
    assert response.status_code == 400

@patch('riot_api.get_match_ids')
def test_api_get_more_ids_success(mock_get_ids, client):
    mock_get_ids.return_value = ['ID1', 'ID2']
    response = client.get('/api/get_more_ids?puuid=test-puuid&start=90')
    assert response.status_code == 200


# JS Parsing Tests

def load_js_function(function_name):
    # Resolve absolute path to games.js inside the static assets directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    js_path = os.path.join(base_dir, 'static', 'js', 'games.js')
    
    with open(js_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the bounds of the requested function or arrow function definition
    # This acts as a lightweight linker to isolate logic without modifying production code
    start_idx = content.find(f"const {function_name}")
    if start_idx == -1:
        start_idx = content.find(f"function {function_name}")
        
    if start_idx == -1:
        raise ValueError(f"Could not locate function '{function_name}' in games.js")

    # Extract the code from the definition point to the end of the file
    snippet = content[start_idx:]
    
    # Trace bracket matching to safely capture the exact boundary of the function block
    bracket_count = 0
    end_idx = 0
    found_start = False
    
    for i, char in enumerate(snippet):
        if char == '{':
            bracket_count += 1
            found_start = True
        elif char == '}':
            bracket_count -= 1
        
        if found_start and bracket_count == 0:
            end_idx = i + 1
            break
            
    final_js_code = snippet[:end_idx]
    
    # Compile the isolated JavaScript code string into an executable Python object
    return js2py.eval_js(final_js_code)

def test_name_formatting():
    format_name = load_js_function('formatName')

    # Set 17 overrides are retired and now pass through untouched
    assert format_name('Galio') == 'Galio'
    assert format_name('IvernMinion') == 'IvernMinion'
    assert format_name('BardFollower') == 'BardFollower'

    # Retained exact-match typographical formatting
    assert format_name('Belveth') == "Bel'Veth"
    assert format_name('Kaisa') == "Kai'Sa"
    assert format_name('AurelionSol') == 'Aurelion Sol'
    assert format_name('MasterYi') == 'Master Yi'
    assert format_name('TwistedFate') == 'Twisted Fate'

    # Set 18 display names that differ from their internal apiName
    assert format_name('KhaZix') == "Kha'Zix"
    assert format_name('RekSai') == "Rek'Sai"
    assert format_name('KogMaw') == "Kog'Maw"
    assert format_name('GnarSmall') == 'Gnar'
    assert format_name('Sentry') == 'Pebbles'
    assert format_name('CrimsonRaptor') == 'Mama Beak'

    # Test standard backup naming behavior
    assert format_name('Gnar') == 'Gnar'
    assert format_name('Lux') == 'Lux'

    assert format_name('') == ''
    assert format_name('UnknownChampion') == 'UnknownChampion'

def test_get_stars():
    get_stars = load_js_function('getStars')

    raw_html = get_stars(3)
    assert raw_html.count('★') == 3
    raw_html = get_stars(2)
    assert raw_html.count('★') == 2
    raw_html = get_stars(1)
    assert raw_html.count('★') == 1
    raw_html = get_stars(0)
    assert raw_html.count('★') == 0

# Riot API Tests

def test_current_set():
    assert CURRENT_SET == 18

def test_prismatic_thresholds():
    assert VALID_PRISMATICS == {
        "DA_18_Blossom": 11,
        "DA_18_Elderwood": 11
    }

def test_clean_api_name():
    # Trait prefixes
    assert clean_api_name("DA_18_Elderwood") == "Elderwood"
    assert clean_api_name("DA_18_Blossom") == "Blossom"
    assert clean_api_name("TFT18_Trait_Blossom") == "Blossom"
    assert clean_api_name("DA_Riftbeast18") == "Riftbeast"

    # Unit prefixes, set suffixes, and variant suffixes
    assert clean_api_name("DA_18_Ahri") == "Ahri"
    assert clean_api_name("DA_Vi18") == "Vi"
    assert clean_api_name("DA_18_MasterYi_AD") == "MasterYi"
    assert clean_api_name("DA_KogMaw18_AD") == "KogMaw"
    assert clean_api_name("DA_Lux18_Blossom") == "Lux"
    assert clean_api_name("DA_18_Lux_Coven") == "Lux"
    assert clean_api_name("TFT18_Belveth") == "Belveth"

    assert clean_api_name("") == ""
    assert clean_api_name(None) == ""
    assert clean_api_name("DA_18") == "DA_18"

@patch('requests.get')
def test_initialize_item_map_failure(mock_get):
    mock_get.return_value = MagicMock(status_code=404)
    with patch('builtins.print') as mock_print:
        riot_api.initialize_item_map()
        mock_print.assert_any_call("[INIT] Failed to load Community Dragon item map.", flush=True)

@patch('requests.get')
def test_initialize_item_map_exception(mock_get):
    mock_get.side_effect = Exception("Timeout")
    with patch('builtins.print') as mock_print:
        riot_api.initialize_item_map()
        assert any("Error loading item map:" in str(call) for call in mock_print.call_args_list)

@patch('requests.get')
def test_initialize_item_map_loads_items_and_champions(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: {
        "items": [{"apiName": "TFT_Item_BlueBuff", "icon": "/ASSETS/Maps/TFT/Icons/Items/TFT_Item_BlueBuff.TFT_Set13.tex"}],
        "sets": {
            "17": {"champions": [{"apiName": "TFT17_Galio", "squareIcon": "ASSETS/Characters/TFT17_Galio/galio.tex"}]},
            "18": {"champions": [
                {"apiName": "DA_18_Ahri", "squareIcon": "ASSETS/Characters/TFT18_Ahri/Skins/Base/Images/TFT18_Ahri_Splash_Tile_27.tex"},
                {"apiName": "DA_Lux18_Base", "squareIcon": "ASSETS/Characters/TFT18_Lux/lux_base.tex"},
                {"apiName": "DA_Lux18_Blossom", "squareIcon": "ASSETS/Characters/TFT18_Lux/lux_blossom.tex"},
                {"apiName": "DA_18_NoIcon"}
            ]}
        }
    })
    with patch.dict(riot_api.ITEM_URL_MAP, clear=True), \
         patch.dict(riot_api.CHAMPION_URL_MAP, clear=True), \
         patch.dict(riot_api.CHAMPION_URL_BY_NAME, clear=True):
        riot_api.initialize_item_map()

        assert riot_api.ITEM_URL_MAP["TFT_Item_BlueBuff"] == \
            "https://raw.communitydragon.org/latest/game/assets/maps/tft/icons/items/tft_item_bluebuff.tft_set13.png"
        assert riot_api.CHAMPION_URL_MAP["DA_18_Ahri"] == \
            "https://raw.communitydragon.org/latest/game/assets/characters/tft18_ahri/skins/base/images/tft18_ahri_splash_tile_27.png"

        # Only the current set is mapped, and icon-less entries are skipped
        assert "TFT17_Galio" not in riot_api.CHAMPION_URL_MAP
        assert "DA_18_NoIcon" not in riot_api.CHAMPION_URL_MAP

        # The cleaned-name index keeps the first (base) form of multi-form units
        assert riot_api.CHAMPION_URL_BY_NAME["lux"].endswith("lux_base.png")
        assert riot_api.CHAMPION_URL_MAP["DA_Lux18_Blossom"].endswith("lux_blossom.png")

def test_get_champion_image_url_resolution():
    with patch.dict(riot_api.CHAMPION_URL_MAP, {"DA_18_Ahri": "https://cdn/ahri.png"}, clear=True), \
         patch.dict(riot_api.CHAMPION_URL_BY_NAME, {"ahri": "https://cdn/ahri.png", "vi": "https://cdn/vi.png"}, clear=True):
        # Exact apiName match
        assert get_champion_image_url("DA_18_Ahri") == "https://cdn/ahri.png"
        # Prefix variant falls back to the cleaned-name index
        assert get_champion_image_url("TFT18_Vi") == "https://cdn/vi.png"
        # Unknown units fall back to the Set 18 team planner splash
        assert get_champion_image_url("DA_18_Neeko") == \
            "https://raw.communitydragon.org/latest/game/assets/ux/tft/championsplashes/patching/tft18_neeko_teamplanner_splash.png"

@patch('riot_api.requests.get')
def test_make_request_rate_limit(mock_get):
    mock_429 = MagicMock()

    mock_429.status_code = 429
    mock_429.headers = {'Retry-After': '0'}
    
    mock_200 = MagicMock()
    mock_200.status_code = 200
    
    mock_get.side_effect = [mock_429, mock_200]

    with patch('time.sleep') as mock_sleep:
        response = make_request("http://dummy-url", {"X-Riot-Token": "test"})
        assert response.status_code == 200
        assert mock_get.call_count == 2
        mock_sleep.assert_called_with(0)

@patch('requests.get')
def test_make_request_active_backoff_cooldown(mock_get):
    riot_api.ROUTE_BACKOFFS["americas"] = time.time() + 100
    mock_get.return_value = MagicMock(status_code=200)
    with patch('time.sleep') as mock_sleep:
        riot_api.make_request("https://americas.api.riotgames.com/test", headers={})
        mock_sleep.assert_called_once()
    del riot_api.ROUTE_BACKOFFS["americas"]

@patch('requests.get')
def test_make_request_exception(mock_get):
    mock_get.side_effect = Exception("Connection Reset")
    res = riot_api.make_request("https://americas.api.riotgames.com/test", headers={})
    assert res is None

@patch('riot_api.make_request')
def test_get_account(mock_make_req):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"puuid": "mock-puuid-123"}
    mock_make_req.return_value = mock_response

    data = get_account("Dishsoap", "NA3")
    assert data["puuid"] == "mock-puuid-123"
    
    # Case 2: Server failure or wrong tag
    mock_response.status_code = 404
    assert get_account("FakeUser", "0000") is None

@patch('requests.get')
def test_get_account_sea_routing_override(mock_get):
    mock_get.return_value = MagicMock(status_code=200)
    riot_api.get_account("YBY1", "0615", region="VN")
    assert "asia.api.riotgames.com" in mock_get.call_args[0][0]

@patch('riot_api.make_request')
def test_get_match_ids(mock_make_request):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = ["NA_1", "NA_2"]
    mock_make_request.return_value = mock_response
    
    match_ids = get_match_ids("mock-puuid")
    assert len(match_ids) == 2
    assert match_ids[0] == "NA_1"

@patch('riot_api.make_request')
def test_get_single_match_detail_epic_prismatic(mock_make_request):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "info": {
            "queue_id": 1100, # Ranked
            "tft_set_number": 18,
            "game_datetime": 1716300000000,
            "participants": [{
                "puuid": "player-1",
                "placement": 1,
                "traits": [{
                    "name": "DA_18_Elderwood",
                    "num_units": 11
                }],
                "units": []
            }]
        }
    }
    mock_make_request.return_value = mock_response
    
    result = get_single_match_detail("NA_1", "player-1")
    assert result["is_epic"] is True
    assert result["game_mode"] == "Ranked"
    assert result["has_prismatic"] is True
    assert result["prismatic_name"] == "Elderwood"

@patch('riot_api.make_request')
def test_get_single_match_detail_excluded_mode(mock_make_request):
    """Verify that unmapped queues (like Tocker's Trials) return False."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "info": {
            "queue_id": 1190, # Tocker Trials standard mode
            "tft_set_number": 18,
            "participants": []
        }
    }
    mock_make_request.return_value = mock_response
    
    result = get_single_match_detail("NA_1", "player-1")
    assert result["is_epic"] is False  

@patch('requests.get')
def test_get_single_match_detail_missing_participant(mock_get):
    mock_match_payload = {
        "info": {"tft_set_number": 18, "queue_id": 1100, "participants": [{"puuid": "some-other-player"}]}
    }
    mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_match_payload)
    res = riot_api.get_single_match_detail("NA1_999", "target-puuid")
    assert res["is_epic"] is False

def build_match_payload(traits=None, units=None, set_number=18, queue_id=1100, placement=1):
    return {
        "info": {
            "tft_set_number": set_number,
            "queue_id": queue_id,
            "game_datetime": 1714483200000,
            "participants": [{
                "puuid": "target-puuid",
                "placement": placement,
                "traits": traits or [],
                "units": units or []
            }]
        }
    }

@patch('requests.get')
def test_get_single_match_detail_rejects_set_17(mock_get):
    payload = build_match_payload(
        traits=[{"name": "DA_18_Elderwood", "num_units": 11}],
        set_number=17
    )
    mock_get.return_value = MagicMock(status_code=200, json=lambda: payload)
    res = riot_api.get_single_match_detail("NA1_999", "target-puuid")
    assert res["is_epic"] is False

@patch('requests.get')
def test_get_single_match_detail_bardfollower_no_longer_prismatic(mock_get):
    """The Set 17 Meeple summon injection is removed, so a Bard follower is just a regular unit."""
    payload = build_match_payload(
        units=[{"character_id": "TFT17_BardFollower", "tier": 4, "rarity": 0, "itemNames": []}]
    )
    mock_get.return_value = MagicMock(status_code=200, json=lambda: payload)
    res = riot_api.get_single_match_detail("NA1_999", "target-puuid")
    assert res["is_epic"] is False

@patch('requests.get')
def test_get_single_match_detail_prismatic_below_threshold(mock_get):
    payload = build_match_payload(traits=[{"name": "DA_18_Blossom", "num_units": 10}])
    mock_get.return_value = MagicMock(status_code=200, json=lambda: payload)
    res = riot_api.get_single_match_detail("NA1_999", "target-puuid")
    assert res["is_epic"] is False

@patch('requests.get')
def test_get_single_match_detail_prismatic_prefix_variant(mock_get):
    payload = build_match_payload(traits=[
        {"name": "DA_Riftbeast18", "num_units": 10},
        {"name": "TFT18_Trait_Blossom", "num_units": 11}
    ])
    mock_get.return_value = MagicMock(status_code=200, json=lambda: payload)
    res = riot_api.get_single_match_detail("NA1_999", "target-puuid")
    assert res["is_epic"] is True
    assert res["prismatic_name"] == "Blossom"

@patch('requests.get')
def test_get_single_match_detail_high_cost_3star(mock_get):
    payload = build_match_payload(
        units=[
            {"character_id": "DA_18_Ahri", "tier": 3, "rarity": 3, "itemNames": ["TFT_Item_BlueBuff", "TFT_Item_Unknown"]},
            {"character_id": "DA_18_MasterYi_AD", "tier": 2, "rarity": 2, "itemNames": []},
            {"character_id": "DA_Vi18", "tier": 3, "rarity": 2, "itemNames": []},
            {"character_id": "DA_18_FakeSummon", "tier": 3, "rarity": 4, "itemNames": []}
        ],
        queue_id=1160,
        placement=3
    )
    mock_get.return_value = MagicMock(status_code=200, json=lambda: payload)

    with patch.dict(riot_api.ITEM_URL_MAP, {"TFT_Item_BlueBuff": "https://cdn/bluebuff.png"}, clear=True), \
         patch.dict(riot_api.CHAMPION_URL_MAP, {"DA_18_Ahri": "https://cdn/ahri.png"}, clear=True), \
         patch.dict(riot_api.CHAMPION_URL_BY_NAME, {"ahri": "https://cdn/ahri.png"}, clear=True):
        res = riot_api.get_single_match_detail("NA1_999", "target-puuid")

    assert res["is_epic"] is True
    assert res["has_prismatic"] is False
    assert res["game_mode"] == "Double Up"
    # Backend sends the individual placement; the frontend converts it with Math.ceil(placement / 2)
    assert res["placement"] == 3

    # Only true 4/5-cost 3-stars count, and summons are excluded
    assert res["high_cost_units"] == ["Ahri"]

    units = {u["character_id"]: u for u in res["units"]}
    assert set(units) == {"Ahri", "MasterYi", "Vi", "FakeSummon"}
    assert units["Ahri"]["image_url"] == "https://cdn/ahri.png"
    assert units["Ahri"]["items"] == ["https://cdn/bluebuff.png"]
    assert units["Vi"]["image_url"].endswith("/tft18_vi_teamplanner_splash.png")
    assert units["FakeSummon"]["is_summon"] is True
    assert units["Ahri"]["is_summon"] is False

@patch('requests.get')
def test_get_single_match_detail_set_18_rarity_scale(mock_get):
    """Set 18 reports rarity as cost minus one, so a 4-cost is rarity 3 and a 5-cost is rarity 4."""
    def verdict(units):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: build_match_payload(units=units))
        return riot_api.get_single_match_detail("NA1_999", "target-puuid")

    # Real board shape from a 3-star Morgana (4-cost) Double Up game
    res = verdict([
        {"character_id": "DA_Taric18", "tier": 2, "rarity": 4, "itemNames": []},
        {"character_id": "DA_18_Morgana", "tier": 3, "rarity": 3, "itemNames": []},
        {"character_id": "DA_18_Hecarim", "tier": 2, "rarity": 2, "itemNames": []}
    ])
    assert res["is_epic"] is True
    assert res["high_cost_units"] == ["Morgana"]

    # 3-star 5-cost
    res = verdict([{"character_id": "DA_18_GnarSmall", "tier": 3, "rarity": 4, "itemNames": []}])
    assert res["high_cost_units"] == ["GnarSmall"]

    # 3-star 1, 2, and 3-cost units are not high-rolls
    res = verdict([
        {"character_id": "DA_18_Sentry", "tier": 3, "rarity": 0, "itemNames": []},
        {"character_id": "DA_18_Teemo", "tier": 3, "rarity": 1, "itemNames": []},
        {"character_id": "DA_Krug18", "tier": 3, "rarity": 2, "itemNames": []}
    ])
    assert res["is_epic"] is False

    # 2-star 4 and 5-cost units are not high-rolls
    res = verdict([
        {"character_id": "DA_18_Morgana", "tier": 2, "rarity": 3, "itemNames": []},
        {"character_id": "DA_Taric18", "tier": 2, "rarity": 4, "itemNames": []}
    ])
    assert res["is_epic"] is False
