from flask import Flask, render_template, request, jsonify
import riot_api

app = Flask(__name__)

@app.before_request
def restrict_regions():
    # Bypass regional checking for static files or if the endpoint is not resolved
    if not request.endpoint or request.endpoint == 'static':
        return None
        
    # Explicitly bypass our manual error page route so it can be previewed/tested
    if request.endpoint == 'manual_region_error':
        return None
        
    # Railway forwards public requests through an edge proxy that injects the CF-IPCountry header
    country = request.headers.get('CF-IPCountry', '').upper()
    
    # Allowed North American country codes
    allowed_countries = ['US', 'CA', 'MX']
    
    # Block the request if a country code is detected and it is outside North America
    if country and country not in allowed_countries:
        return render_template('region_error.html'), 403

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

# Dedicated debugging route to view the region restriction page manually
@app.route('/region_error.html')
def manual_region_error():
    return render_template('region_error.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)