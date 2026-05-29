import pytest
from playwright.sync_api import Page, expect

def test_homepage_loads(page: Page):
    # Ensure your app is running at http://localhost:5000
    page.goto("http://localhost:5000")
    
    # Check if the title is correct
    expect(page).to_have_title("TFT Hits")
    
    # Check if the search input is visible
    search_input = page.locator('input[name="username"]')
    expect(search_input).to_be_visible()

def test_invalid_user_search(page: Page):
    page.goto("http://localhost:5000")
    page.fill('input[name="username"]', "InvalidUserNoTag")
    page.click('button[type="submit"]')
    
    # Check if the error message appears
    expect(page.locator("text=Invalid format. Use Name#Tag.")).to_be_visible()

def test_quick_lookup_panel_interaction(page: Page):
    page.goto("http://localhost:5000")
    
    # Click on the Dishsoap card profile item
    page.click("button:has-text('Dishsoap')")
    
    # Verify the input automatically populated and focused
    search_input = page.locator('input[name="username"]')
    expect(search_input).to_have_value("ACAD Dishsoap#NA3")

def test_riot_verification_text_route(page: Page):
    """Cover the custom raw static verification router path required by Riot."""
    response = page.goto("http://localhost:5000/riot.txt")
    
    # Confirm it returns a success response code and reads raw plain text assets
    assert response.status == 200
    assert "text/plain" in response.headers["content-type"]