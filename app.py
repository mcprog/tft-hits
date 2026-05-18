import os
from flask import Flask, render_template, request, jsonify, session, send_from_directory
import requests
import riot_api

app = Flask(__name__)
# Encrypts session cookies. Pulls from Railway variables or falls back locally
app.secret_key = os.environ.get("SECRET_KEY", "tft-tracker-default-dev-key")

@app.before_request
def restrict_regions():
    # REGION LOCK DISABLED FOR NOW
    # Remove or comment out this return line when you are ready to re-enforce region locking live.
    return None

    # Bypass regional checking for static assets or unresolved routes
    if not request.endpoint or request.endpoint == 'static':
        return None
        
    # Bypass checks for the manual error page and Riot's verification crawler
    if request.endpoint in ['manual_region_error', 'serve_riot_txt']:
        return None

    # 1. Session Cache Check: If we already verified this user, use the saved result
    if 'is_allowed_region' in session:
        if not session['is_allowed_region']:
            return render_template('region_error.html'), 403
        return None

    allowed_countries = ['US', 'CA', 'MX']

    # 2. Cloudflare Ingress Fallback: Check if traffic comes through a custom proxied domain
    cloudflare_country = request.headers.get('CF-IPCountry', '').upper()
    if cloudflare_country:
        is_allowed = cloudflare_country in allowed_countries
        session['is_allowed_region'] = is_allowed
        if not is_allowed:
            return render_template('region_error.html'), 403
        return None

    # 3. Default Railway Ingress: Extract the client IP from the routing proxy chain
    ip_header = request.headers.get('X-Forwarded-For', '')
    client_ip = ip_header.split(',')[0].strip() if ip_header else request.remote_addr

    # Safeguard: Do not isolate or block local development loopbacks
    if not client_ip or client_ip in ['127.0.0.1', 'localhost', '::1']:
        session['is_allowed_region'] = True
        return None

    # 4. Live API Geolocation Verification
    try:
        geo_response = requests.get(f"http://ip-api.com/json/{client_ip}", timeout=2)
        if geo_response.status_code == 200:
            geo_data = geo_response.json()
            
            if geo_data.get('status') == 'fail':
                session['is_allowed_region'] = True
                return None
                
            resolved_country = geo_data.get('countryCode', '').upper()
            is_allowed = resolved_country in allowed_countries
            session['is_allowed_region'] = is_allowed
            
            if not is_allowed:
                return render_template('region_error.html'), 403
        else:
            return None
    except Exception:
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/games', methods=['GET', 'POST'])
def games():
    if request.method == 'GET':
        return render_template('games.html', error=None, username=None)
    
    full_username = request.form.get('username', '').strip()
    if not full_username or '#' not in full_username:
        return render_template('games.html', username=full_username, error="Invalid format. Use Name#Tag.")
    
    try:
        name, tag = full_username.split('#', 1)
        account_data = riot_api.get_account(name.strip(), tag.strip())
        
        if account_data:
            puuid = account_data.get('puuid')
            match_ids = riot_api.get_match_ids(puuid, count=90)
            
            return render_template(
                'games.html', 
                username=full_username, 
                match_ids=match_ids, 
                puuid=puuid,
                error=None
            )
        else:
            return render_template('games.html', username=full_username, error="Account not found.")
    except Exception as e:
        return render_template('games.html', username=full_username, error=f"System Error: {str(e)}")

@app.route('/api/match_details/<match_id>')
def match_details(match_id):
    puuid = request.args.get('puuid')
    if not puuid:
        return jsonify({"error": "Missing PUUID"}), 400
    data = riot_api.get_single_match_detail(match_id, puuid)
    return jsonify(data)

@app.route('/api/get_more_ids')
def get_more_ids():
    puuid = request.args.get('puuid')
    start = int(request.args.get('start', 0))
    if not puuid:
        return jsonify({"error": "Missing PUUID"}), 400
    match_ids = riot_api.get_match_ids(puuid, count=90, start=start)
    return jsonify(match_ids)

@app.route('/region_error.html')
def manual_region_error():
    return render_template('region_error.html')

@app.route('/riot.txt')
def serve_riot_txt():
    return send_from_directory(app.root_path, 'riot.txt', mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)