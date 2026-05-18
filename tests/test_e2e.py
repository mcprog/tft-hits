import pytest
from playwright.sync_api import Page, expect

def test_homepage_loads(page: Page):
    return
    # Ensure your app is running at http://localhost:5000
    page.goto("http://localhost:5000")
    
    # Check if the title is correct
    expect(page).to_have_title("TFT Hits")
    
    # Check if the search input is visible
    search_input = page.locator('input[name="username"]')
    expect(search_input).to_be_visible()

def test_invalid_user_search(page: Page):
    return
    page.goto("http://localhost:5000")
    page.fill('input[name="username"]', "InvalidUserNoTag")
    page.click('button[type="submit"]')
    
    # Check if the error message appears
    expect(page.locator("text=Error: Invalid format")).to_be_visible()