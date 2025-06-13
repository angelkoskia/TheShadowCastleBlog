#!/usr/bin/env python3
import json
import sys
import os

# Add the current directory to the path to import the leveling system
sys.path.append('.')
from utils.leveling_system import LevelingSystem

def load_hunters_data():
    try:
        with open('hunters_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_hunters_data(data):
    with open('hunters_data.json', 'w') as f:
        json.dump(data, f, indent=2)

# Initialize leveling system
leveling_system = LevelingSystem()

# Load current data
hunters_data = load_hunters_data()

# User configurations: user_id -> level
users_to_set = {
    '299559754756521985': 16,
    '562670505782542366': 24,
    '1266802308055044149': 14
}

for user_id, level in users_to_set.items():
    print(f"Setting user {user_id} to level {level}")
    
    # Initialize hunter if they don't exist
    if user_id not in hunters_data:
        hunters_data[user_id] = {
            'level': 1,
            'exp': 0,
            'rank': 'E Rank',
            'hp': 100,
            'mp': 50,
            'max_hp': 100,
            'max_mp': 50,
            'strength': 10,
            'agility': 10,
            'intelligence': 10,
            'defense': 5,
            'gold': 0,
            'inventory': [],
            'equipment': {'weapon': None, 'armor': None, 'accessory': None},
            'theme': 'default'
        }
    
    hunter = hunters_data[user_id]
    old_level = hunter.get('level', 1)
    
    # Set new level and calculate appropriate EXP
    hunter['level'] = level
    hunter['exp'] = leveling_system._exp_table.get(level, 0)
    hunter['rank'] = leveling_system.get_rank_for_level(level)
    
    # Calculate level-appropriate stats
    levels_gained = level - 1  # From level 1 base
    hp_gain = levels_gained * 25
    mp_gain = levels_gained * 15
    stat_gain = levels_gained * 2
    
    # Update stats based on level
    hunter['max_hp'] = 100 + hp_gain
    hunter['max_mp'] = 50 + mp_gain
    hunter['hp'] = hunter['max_hp']  # Full heal
    hunter['mp'] = hunter['max_mp']  # Full mana
    
    # Update base stats
    hunter['strength'] = hunter.get('base_strength', 10) + stat_gain
    hunter['agility'] = hunter.get('base_agility', 10) + stat_gain
    hunter['intelligence'] = hunter.get('base_intelligence', 10) + stat_gain
    hunter['defense'] = hunter.get('base_defense', 5) + stat_gain
    
    print(f"✅ Set user {user_id} to Level {level} ({hunter['rank']})")
    print(f"   HP: {hunter['max_hp']} • MP: {hunter['max_mp']}")
    print(f"   Stats: {hunter['strength']} STR • {hunter['agility']} AGI • {hunter['intelligence']} INT • {hunter['defense']} DEF")
    print()

# Save updated data
save_hunters_data(hunters_data)
print("All levels set successfully!")