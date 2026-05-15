# TFT Set 17 Epic Match Tracker

## Purpose
This web application automatically filters a player's Teamfight Tactics match history to find high-roll games from Set 17 (Space Gods). It specifically identifies matches where the user achieved a Prismatic Trait or a 3-star 4-cost or 5-cost unit. The app utilizes asynchronous loading to bypass Riot API rate limits and provide a fast user experience.

## Tech Stack
* Backend: Python, Flask
* API Integration: Riot Games API
* Frontend: HTML, JavaScript, Tailwind CSS
* Containerization: Docker

## Setup and Local Run
1. Create a .env file in the root directory.
2. Add your Riot API key to the file: RIOT_API_KEY=your_key_here
3. Install dependencies:
   pip install -r requirements.txt
4. Start the server:
   python app.py
5. Access the app at http://localhost:5000

## Docker Build and Run
1. Build the image:
   docker build -t tft-tracker .
2. Run the container using the .env file:
   docker run -p 5000:5000 --env-file .env tft-tracker
