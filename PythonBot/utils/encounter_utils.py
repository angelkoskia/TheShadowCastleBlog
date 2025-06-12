"""
Utility functions for encounter system and daily hunt tracking.
"""

import json
from datetime import datetime, date
from typing import Dict, Any

def load_hunters_data():
    """Load hunter data from JSON file"""
    try:
        with open('hunters_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_hunters_data(data):
    """Save hunter data to JSON file"""
    try:
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving hunters data: {e}")

def check_and_reset_daily_hunts(hunter: Dict[str, Any]) -> bool:
    """Check if daily hunts should be reset and reset if needed"""
    today_str = datetime.now().date().isoformat()
    
    # Get last reset date
    last_reset = hunter.get('last_daily_reset', today_str)
    if isinstance(last_reset, str):
        try:
            last_reset_date_str = datetime.fromisoformat(last_reset).date().isoformat()
        except:
            last_reset_date_str = today_str
    else:
        last_reset_date_str = today_str

    # Reset if it's a new day
    if today_str != last_reset_date_str:
        hunter['hunts_done_today'] = 0
        hunter['last_daily_reset'] = datetime.now().isoformat()
        return True
    return False

def initialize_hunter_encounter_data(hunter: Dict[str, Any]) -> None:
    """Initialize encounter-related fields for a hunter"""
    # Daily hunt tracking
    hunter.setdefault('hunts_done_today', 0)
    hunter.setdefault('last_daily_reset', datetime.now().isoformat())
    
    # Monster kill counts for lore progression
    hunter.setdefault('monster_kills', {})
    
    # Current encounter state
    hunter.setdefault('current_encounter', None)
    
    # Encounter buffs
    hunter.setdefault('encounter_buffs', {})

def update_monster_kill_count(hunter: Dict[str, Any], monster_id: str) -> int:
    """Update and return the kill count for a specific monster"""
    if 'monster_kills' not in hunter:
        hunter['monster_kills'] = {}
    
    hunter['monster_kills'][monster_id] = hunter['monster_kills'].get(monster_id, 0) + 1
    return hunter['monster_kills'][monster_id]

def apply_encounter_reward(hunter: Dict[str, Any], reward_data: Dict[str, Any]) -> str:
    """Apply encounter reward to hunter and return success message"""
    messages = []
    
    # Gold reward
    if 'gold' in reward_data:
        gold_change = reward_data['gold']
        if gold_change > 0:
            hunter['gold'] = hunter.get('gold', 0) + gold_change
            messages.append(f"Gained {gold_change} gold!")
        elif gold_change < 0:
            current_gold = hunter.get('gold', 0)
            if current_gold >= abs(gold_change):
                hunter['gold'] = current_gold + gold_change  # gold_change is negative
                messages.append(f"Spent {abs(gold_change)} gold.")
            else:
                return "You don't have enough gold for this!"
    
    # EXP reward
    if 'exp' in reward_data:
        exp_gain = reward_data['exp']
        from utils.leveling_system import award_exp
        # This will be handled by the main hunt command
        messages.append(f"Gained {exp_gain} EXP!")
    
    # Item reward
    if 'item' in reward_data:
        item_name = reward_data['item']
        from data.encounter_data import ENCOUNTER_ITEMS
        
        if item_name in ENCOUNTER_ITEMS:
            item_data = ENCOUNTER_ITEMS[item_name]
            if 'inventory' not in hunter:
                hunter['inventory'] = {}
            
            if item_data.get('stackable', False):
                hunter['inventory'][item_name] = hunter['inventory'].get(item_name, 0) + 1
            else:
                # For non-stackable items, create unique keys if needed
                base_name = item_name
                counter = 1
                unique_name = base_name
                while unique_name in hunter['inventory']:
                    unique_name = f"{base_name}_{counter}"
                    counter += 1
                hunter['inventory'][unique_name] = item_data
            
            messages.append(f"Received {item_data['name']}!")
    
    # Buff reward
    if 'buff' in reward_data:
        buff_name = reward_data['buff']
        from data.encounter_data import ENCOUNTER_BUFFS
        
        if buff_name in ENCOUNTER_BUFFS:
            buff_data = ENCOUNTER_BUFFS[buff_name]
            if 'encounter_buffs' not in hunter:
                hunter['encounter_buffs'] = {}
            
            hunter['encounter_buffs'][buff_name] = {
                'duration': buff_data['duration'],
                'data': buff_data
            }
            messages.append(f"Gained {buff_data['name']} buff!")
    
    return " ".join(messages)

def get_active_encounter_buffs(hunter: Dict[str, Any]) -> Dict[str, Any]:
    """Get all active encounter buffs and their effects"""
    active_buffs = {}
    encounter_buffs = hunter.get('encounter_buffs', {})
    
    # Remove expired buffs
    expired_buffs = []
    for buff_name, buff_info in encounter_buffs.items():
        if buff_info['duration'] <= 0:
            expired_buffs.append(buff_name)
        else:
            active_buffs[buff_name] = buff_info['data']
    
    # Clean up expired buffs
    for buff_name in expired_buffs:
        del encounter_buffs[buff_name]
    
    return active_buffs

def reduce_encounter_buff_duration(hunter: Dict[str, Any]) -> None:
    """Reduce duration of all encounter buffs by 1 (call after each battle)"""
    encounter_buffs = hunter.get('encounter_buffs', {})
    
    for buff_name, buff_info in encounter_buffs.items():
        buff_info['duration'] = max(0, buff_info['duration'] - 1)