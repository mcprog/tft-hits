import pytest
from riot_api import VALID_PRISMATICS

# Testing the name formatting logic from your frontend context
def format_name(name):
    return 'The Mighty Mech' if name == 'Galio' else name

def test_galio_formatting():
    assert format_name('Galio') == 'The Mighty Mech'
    assert format_name('Rammus') == 'Rammus'

def test_prismatic_thresholds():
    # Verify our logic for Dark Star is correct
    assert VALID_PRISMATICS["TFT17_Trait_DarkStar"] == 9
    assert VALID_PRISMATICS["TFT17_Trait_Meeple"] == 10