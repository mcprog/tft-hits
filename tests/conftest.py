import threading
import time
import pytest
from app import app

def run_server():
    # Force development mode and disable the reloader so it doesn't spawn duplicate threads
    app.config['TESTING'] = True
    app.run(host='0.0.0.0', port=5000, use_reloader=False)

@pytest.fixture(scope="session", autouse=True)
def autostart_flask_server():
    """Starts the Flask application in a background thread for E2E browser tests."""
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Give the Flask server a brief moment (500ms) to initialize and bind to port 5000
    time.sleep(0.5)
    
    yield
    # The daemon thread will automatically clean up and terminate when the pytest session completes