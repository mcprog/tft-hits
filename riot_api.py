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