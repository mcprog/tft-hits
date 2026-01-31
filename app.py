from flask import Flask, render_template, request
#import riot_api

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/highlights', methods=['POST'])
def highlights():
    username = request.form.get('username')
    # 1. Get PUUID from Riot API
    # 2. Get recent Match IDs
    # 3. Filter matches using is_highlight_game()
    highlight_games = [] # list of filtered match data
    return render_template('games.html', games=highlight_games, user=username)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
