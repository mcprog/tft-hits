from flask import Flask, render_template, request, jsonify
import riot_api

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

# --- ROUTE 2: Main UI (Initial Load) ---
@app.route('/games', methods=['GET', 'POST'])
def games():
    if request.method == 'GET':
        return render_template('games.html', error=None, username=None, data=None)

    full_username = request.form.get('username')

    if not full_username or '#' not in full_username:
        return render_template('games.html', username=full_username or "Unknown", error="Error: Invalid format.")
    
    try:
        name, tag = full_username.split('#', 1)
        account_data = riot_api.get_account(name, tag)

        if account_data:
            puuid = account_data.get('puuid')
            # Batch 1: Fetch first 100 games (Start 0)
            games_list = riot_api.get_epic_matches(puuid, start=0, count=100)
            
            # Render with Batch 1 AND pass 'puuid' for JS to use later
            return render_template(
                'games.html', 
                username=full_username, 
                games=games_list, 
                puuid=puuid,  # <--- Crucial for background fetches
                error=None
            )
        else:
            return render_template('games.html', username=full_username, error="Account not found.")
            
    except Exception as e:
        return render_template('games.html', username=full_username, error=f"System Error: {str(e)}")

# --- ROUTE 3: Background API for Pagination ---
@app.route('/api/fetch_matches')
def fetch_matches_api():
    # JavaScript will call this: /api/fetch_matches?puuid=...&start=100
    puuid = request.args.get('puuid')
    start = int(request.args.get('start', 0))
    count = int(request.args.get('count', 100))
    
    if not puuid:
        return jsonify({"error": "Missing PUUID"}), 400
        
    # Fetch the next batch
    new_games = riot_api.get_epic_matches(puuid, start=start, count=count)
    print(new_games, flush=True)
    
    # Return pure JSON data
    return jsonify(new_games)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)