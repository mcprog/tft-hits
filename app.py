import os
from flask import Flask, render_template, request, jsonify, session, send_from_directory
import requests
import riot_api

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tft-tracker-default-dev-key")

# Centralized list of tracked players to dynamically build the lookup grid panels
QUICK_LOOKUPS = {
    "NA": [
        {"display_name": "Dishsoap", "riot_id": "ACAD Dishsoap#NA3"},
        {"display_name": "setsuko", "riot_id": "VIT setsuko#NA2"},
        {"display_name": "emillywang", "riot_id": "CTG emilyywang#1111"},
        {"display_name": "k3soju", "riot_id": "VIT k3soju#000"}
    ],
    "EUW": [
        {"display_name": "Sologesang", "riot_id": "Sologesang#EUW"},
        {"display_name": "Whyyoumadpro", "riot_id": "whyyoumadpro#EUW"},
        {"display_name": "ZBROJS0N", "riot_id": "ZBROJS0N#EUW"}
    ],
    "EUNE": [
        {"display_name": "Demacian Raptor", "riot_id": "Demacian Raptor#JAZZ"},
        {"display_name": "ZeulEnache", "riot_id": "ZeulEnache#8652"},
        {"display_name": "bukajeek", "riot_id": "bukajeek#2029"}
    ],
    "VN": [
        {"display_name": "YBY1", "riot_id": "YBY1#0615"},
        {"display_name": "A Long", "riot_id": "A Long#1102"}
    ],
    "KR": [
        {"display_name": "SanChess", "riot_id": "SanChess#king"},
        {"display_name": "Kanata", "riot_id": "Kanata#TFT"},
        {"display_name": "Souly", "riot_id": "Souly#KR2"}
    ]
}

@app.before_request
def restrict_regions():
    return None

@app.route('/')
def index():
    # Pass the data map directly to the index template launcher context
    return render_template('index.html', quick_lookups=QUICK_LOOKUPS)

@app.route('/games', methods=['GET', 'POST'])
def games():
    if request.method == 'GET':
        return render_template('games.html', error=None, username=None)
    
    full_username = request.form.get('username', '').strip()
    selected_region = request.form.get('region', 'NA').upper()
    
    session['selected_region'] = selected_region
    
    if not full_username or '#' not in full_username:
        return render_template('games.html', username=full_username, error="Invalid format. Use Name#Tag.")
    
    try:
        name, tag = full_username.split('#', 1)
        account_data = riot_api.get_account(name.strip(), tag.strip(), region=selected_region)
        
        if account_data:
            puuid = account_data.get('puuid')
            match_ids = riot_api.get_match_ids(puuid, count=90, region=selected_region)
            
            return render_template(
                'games.html', 
                username=full_username, 
                match_ids=match_ids, 
                puuid=puuid,
                error=None
            )
        else:
            return render_template('games.html', username=full_username, error=f"Account not found in region: {selected_region}")
    except Exception as e:
        return render_template('games.html', username=full_username, error=f"System Error: {str(e)}")

@app.route('/api/match_details/<match_id>')
def match_details(match_id):
    puuid = request.args.get('puuid')
    if not puuid:
        return jsonify({"error": "Missing PUUID"}), 400
    
    active_region = session.get('selected_region', 'NA')
    data = riot_api.get_single_match_detail(match_id, puuid, region=active_region)
    return jsonify(data)

@app.route('/api/get_more_ids')
def get_more_ids():
    puuid = request.args.get('puuid')
    start = int(request.args.get('start', 0))
    if not puuid:
        return jsonify({"error": "Missing PUUID"}), 400
        
    active_region = session.get('selected_region', 'NA')
    match_ids = riot_api.get_match_ids(puuid, count=90, start=start, region=active_region)
    return jsonify(match_ids)

@app.route('/region_error.html')
def manual_region_error():
    return render_template('region_error.html')

@app.route('/riot.txt')
def serve_riot_txt():
    return send_from_directory(app.root_path, 'riot.txt', mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)