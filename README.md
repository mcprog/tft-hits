# TFT Set 17 Epic Match Tracker

## Purpose
This web application automatically filters a player's Teamfight Tactics match history to find high-roll games from Set 17 (Space Gods). It identifies matches where the user achieved a Prismatic Trait or a 3-star 4-cost or 5-cost unit.

## Tech Stack
* Backend: Python, Flask
* API Integration: Riot Games API
* Frontend: HTML, JavaScript, Tailwind CSS
* Testing: pytest, pytest-playwright
* Containerization: Docker (Multi-stage build)

## Production Environment

### Build Production Image
By default, building the Dockerfile builds the full clean production stage.
```bash
docker build -t tft-tracker .
```

### Run Production Container
Ensure you have a .env file containing your RIOT_API_KEY in the root directory.
```bash
docker run -p 5000:5000 --env-file .env tft-tracker
```

## Development and Testing Environment

### Build Dev Environment Image
To build the environment with development tools, test frameworks, and headless browsers, target the test stage:
```bash
docker build --target test -t tft-tracker-dev .
```

### Run Automated Tests
This executes the complete unit and end-to-end test suites using pytest and Playwright:
```bash
docker run --rm tft-tracker-dev
```

### Run Web Server from Dev Image
To run the active web server within the development layer for debugging or feature testing:
```bash
docker run --rm -p 5000:5000 --env-file .env tft-tracker-dev python app.py
```
