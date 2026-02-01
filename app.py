from flask import Flask, render_template, request, redirect, url_for
import riot_api  # Keeps Pattern B: Loads env vars on import

app = Flask(__name__)

# --- ROUTE 1: The Home Page ---
@app.route('/')
def index():
    # Renders the landing page (e.g., separate index.html)
    return render_template('index.html')

# --- ROUTE 2: The Tool Page ---
@app.route('/games', methods=['GET', 'POST'])
def games():
    # GET: User just arrived at the page. Show empty form.
    if request.method == 'GET':
        return render_template('games.html', error=None, username=None, data=None)

    # POST: User submitted the form.
    full_username = request.form.get('username')

    # --- VALIDATION LOGIC ---
    # Checks if empty or missing '#'
    if not full_username or '#' not in full_username:
        error_text = "Error: please enter a valid username. Use Name#Tag format"
        # Stays on /games, re-renders with error message
        return render_template('games.html', username=full_username or "Unknown", error=error_text)
    
    # --- API LOGIC ---
    try:
        name, tag = full_username.split('#', 1)
        account_data = riot_api.get_account(name, tag)

        if account_data:
            puuid = account_data.get('puuid')
            games_list = riot_api.get_epic_matches(puuid, count=70)
            return render_template('games.html', username=full_username, games=games_list, error=None)
        else:
            return render_template('games.html', username=full_username, error="Summoner not found.")
            
    except Exception as e:
        # Catch-all for unexpected errors
        return render_template('games.html', username=full_username, error=f"System Error: {str(e)}")

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)