def is_highlight_game(match_data, puid):
    participant = next(p for p in match_data['info']['participants'] if p['puuid'] == puid)
    
    # 1. Check for 3-Star 4+ Cost Units
    for unit in participant['units']:
        if unit['tier'] == 3 and unit['rarity'] >= 4: # rarity 4=4-cost, 5=5-cost+
            return True
            
    # 2. Check for Prismatic Traits
    for trait in participant['traits']:
        if trait['style'] == 4: # 'style' 4 typically represents Prismatic/Gold tier
            return True
            
    return False
