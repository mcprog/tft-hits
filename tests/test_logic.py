import pytest
import os
import time
import js2py
from unittest.mock import patch, MagicMock

import app
import riot_api

from riot_api import (
    VALID_PRISMATICS,
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
    
    # Test your specific Set 17 overrides
    assert format_name('Galio') == 'The Mighty Mech'
    assert format_name('IvernMinion') == 'Meepsie'
    
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

def test_prismatic_thresholds():
    assert VALID_PRISMATICS["TFT17_Trait_DarkStar"] == 9
    assert VALID_PRISMATICS["TFT17_Trait_Meeple"] == 10
    assert VALID_PRISMATICS["TFT17_Trait_SpaceGroove"] == 10
    assert VALID_PRISMATICS["TFT17_Trait_Stargazer"] == 11

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
            "tft_set_number": 17,
            "game_datetime": 1716300000000,
            "participants": [{
                "puuid": "player-1",
                "placement": 1,
                "traits": [{
                    "name": "TFT17_Trait_DarkStar",
                    "num_units": 9
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

@patch('riot_api.make_request')
def test_get_single_match_detail_excluded_mode(mock_make_request):
    """Verify that unmapped queues (like Tocker's Trials) return False."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "info": {
            "queue_id": 1190, # Tocker Trials standard mode
            "tft_set_number": 17,
            "participants": []
        }
    }
    mock_make_request.return_value = mock_response
    
    result = get_single_match_detail("NA_1", "player-1")
    assert result["is_epic"] is False  

@patch('requests.get')
def test_get_single_match_detail_missing_participant(mock_get):
    mock_match_payload = {
        "info": {"tft_set_number": 17, "queue_id": 1100, "participants": [{"puuid": "some-other-player"}]}
    }
    mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_match_payload)
    res = riot_api.get_single_match_detail("NA1_999", "target-puuid")
    assert res["is_epic"] is False

@patch('requests.get')
def test_get_single_match_detail_bardfollower_override(mock_get):
    mock_match_payload = {
        "info": {
            "tft_set_number": 17,
            "queue_id": 1100,
            "game_datetime": 1714483200000,
            "participants": [{
                "puuid": "target-puuid",
                "placement": 1,
                "traits": [],
                "units": [{"character_id": "TFT17_BardFollower", "tier": 4, "itemNames": []}]
            }]
        }
    }
    mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_match_payload)
    res = riot_api.get_single_match_detail("NA1_999", "target-puuid")
    assert res["is_epic"] is True
    assert res["prismatic_name"] == "Meeple"  