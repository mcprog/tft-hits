from flask import Flask, render_template, request, jsonify
import riot_api
import json

app = Flask(__name__)

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
            # Request 90 match IDs to stay within the 100/2min limit
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
    
    # Fetch the next batch of 90
    match_ids = riot_api.get_match_ids(puuid, count=90, start=start)
    return jsonify(match_ids)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)