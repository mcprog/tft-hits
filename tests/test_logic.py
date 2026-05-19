import pytest
import os
import js2py
from riot_api import VALID_PRISMATICS

def load_js_function(function_name):
    # Resolve absolute path to games.js inside the static assets directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    js_path = os.path.join(base_dir, 'static', 'js', 'games.js')
    
    with open(js_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the bounds of the requested function or arrow function definition
    # This acts as a lightweight linker to isolate logic without modifying production code
    start_idx = content.find(f"const {function_name}")
    if start_idx == -1:
        start_idx = content.find(f"function {function_name}")
        
    if start_idx == -1:
        raise ValueError(f"Could not locate function '{function_name}' in games.js")

    # Extract the code from the definition point to the end of the file
    snippet = content[start_idx:]
    
    # Trace bracket matching to safely capture the exact boundary of the function block
    bracket_count = 0
    end_idx = 0
    found_start = False
    
    for i, char in enumerate(snippet):
        if char == '{':
            bracket_count += 1
            found_start = True
        elif char == '}':
            bracket_count -= 1
        
        if found_start and bracket_count == 0:
            end_idx = i + 1
            break
            
    final_js_code = snippet[:end_idx]
    
    # Compile the isolated JavaScript code string into an executable Python object
    return js2py.eval_js(final_js_code)

def test_name_formatting():
    format_name = load_js_function('formatName')
    
    # Test your specific Set 17 overrides
    assert format_name('Galio') == 'The Mighty Mech'
    assert format_name('IvernMinion') == 'Meepsie'
    
    # Test standard backup naming behavior
    assert format_name('Gnar') == 'Gnar'
    assert format_name('Lux') == 'Lux'

    assert format_name('') == ''
    assert format_name('UnknownChampion') == 'UnknownChampion'

def test_get_stars():
    get_stars = load_js_function('getStars')

    raw_html = get_stars(3)
    assert raw_html.count('★') == 3
    raw_html = get_stars(2)
    assert raw_html.count('★') == 2
    raw_html = get_stars(1)
    assert raw_html.count('★') == 1
    raw_html = get_stars(0)
    assert raw_html.count('★') == 0


def test_prismatic_thresholds():
    assert VALID_PRISMATICS["TFT17_Trait_DarkStar"] == 9
    assert VALID_PRISMATICS["TFT17_Trait_Meeple"] == 10
    assert VALID_PRISMATICS["TFT17_Trait_SpaceGroove"] == 10
    assert VALID_PRISMATICS["TFT17_Trait_Stargazer"] == 11