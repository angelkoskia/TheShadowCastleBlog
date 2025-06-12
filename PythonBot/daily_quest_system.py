import json
import random
from datetime import datetime, timedelta

def load_quests_data():
    """Load quest templates from data file"""
    return {
        "daily_templates": [
            {
                "id": "monster_hunt",
                "name": "Monster Hunter",
                "description": "Defeat {target} monsters",
                "type": "kill_monsters",
                "target_range": [8, 15],
                "reward_gold_range": [200, 400],
                "reward_exp_range": [100, 200]
            },
            {
                "id": "gate_clear",
                "name": "Gate Clearer",
                "description": "Clear {target} gates",
                "type": "clear_gates",
                "target_range": [2, 4],
                "reward_gold_range": [300, 600],
                "reward_exp_range": [150, 300]
            },
            {
                "id": "dungeon_explorer",
                "name": "Dungeon Explorer",
                "description": "Complete {target} dungeon floors",
                "type": "complete_floors",
                "target_range": [2, 4],
                "reward_gold_range": [400, 800],
                "reward_exp_range": [200, 400]
            },
            {
                "id": "equipment_master",
                "name": "Equipment Master",
                "description": "Equip {target} different items",
                "type": "equip_items",
                "target_range": [2, 4],
                "reward_gold_range": [150, 300],
                "reward_exp_range": [75, 150]
            },
            {
                "id": "gold_collector",
                "name": "Gold Collector",
                "description": "Earn {target} gold from battles",
                "type": "earn_gold",
                "target_range": [500, 1000],
                "reward_gold_range": [300, 500],
                "reward_exp_range": [100, 200]
            },
            {
                "id": "shop_customer",
                "name": "Shop Customer",
                "description": "Purchase {target} items from shop",
                "type": "buy_items",
                "target_range": [2, 3],
                "reward_gold_range": [150, 250],
                "reward_exp_range": [75, 125]
            }
        ],
        "weekly_templates": [
            {
                "id": "weekly_slayer",
                "name": "Weekly Monster Slayer",
                "description": "Defeat {target} monsters this week",
                "type": "kill_monsters",
                "target_range": [50, 80],
                "reward_gold_range": [2000, 3500],
                "reward_exp_range": [1000, 1800],
                "special_reward": "Enhancement Stone"
            },
            {
                "id": "weekly_explorer",
                "name": "Weekly Gate Explorer",
                "description": "Clear {target} gates this week",
                "type": "clear_gates",
                "target_range": [10, 18],
                "reward_gold_range": [2500, 4000],
                "reward_exp_range": [1200, 2000],
                "special_reward": "Epic Equipment Box"
            },
            {
                "id": "weekly_dungeon_master",
                "name": "Weekly Dungeon Master",
                "description": "Complete {target} dungeon floors this week",
                "type": "complete_floors",
                "target_range": [25, 40],
                "reward_gold_range": [3000, 5000],
                "reward_exp_range": [1500, 2500],
                "special_reward": "Master's Tome"
            },
            {
                "id": "weekly_merchant",
                "name": "Weekly Merchant",
                "description": "Purchase {target} items this week",
                "type": "buy_items",
                "target_range": [12, 20],
                "reward_gold_range": [1500, 2500],
                "reward_exp_range": [750, 1250],
                "special_reward": "Merchant's Token"
            }
        ],
        "special_templates": [
            {
                "id": "shadow_realm_conqueror",
                "name": "Shadow Realm Conqueror",
                "description": "Defeat the Shadow Monarch's lieutenant",
                "type": "special_boss",
                "required_key": "Shadow Realm Key",
                "reward_gold": 10000,
                "reward_exp": 5000,
                "special_reward": "Shadow Extraction Skill"
            },
            {
                "id": "demon_castle_infiltrator",
                "name": "Demon Castle Infiltrator",
                "description": "Infiltrate the Demon Castle and retrieve the artifact",
                "type": "special_infiltration",
                "required_key": "Demon Castle Key",
                "reward_gold": 15000,
                "reward_exp": 7500,
                "special_reward": "Demon Lord's Fragment"
            },
            {
                "id": "ice_monarch_challenger",
                "name": "Ice Monarch Challenger",
                "description": "Challenge the Ice Monarch in single combat",
                "type": "special_duel",
                "required_key": "Ice Monarch Key",
                "reward_gold": 20000,
                "reward_exp": 10000,
                "special_reward": "Frost King's Crown"
            }
        ]
    }

def generate_daily_quests(hunter_level=1):
    """Generate daily quests based on hunter level"""
    quest_data = load_quests_data()
    daily_quests = {}
    
    # Scale quest difficulty with hunter level
    level_multiplier = max(1, hunter_level // 5)
    
    # Select 3-4 daily quests, ensuring no PvP quests
    daily_templates = quest_data.get("daily_templates", [])
    selected_templates = random.sample(daily_templates, min(4, len(daily_templates)))
    
    for template in selected_templates:
        quest_id = template["id"]
        
        # Scale target and rewards based on level
        min_target, max_target = template["target_range"]
        target = random.randint(min_target, max_target) * level_multiplier
        
        min_gold, max_gold = template["reward_gold_range"]
        gold_reward = random.randint(min_gold, max_gold) * level_multiplier
        
        min_exp, max_exp = template["reward_exp_range"]
        exp_reward = random.randint(min_exp, max_exp) * level_multiplier
        
        daily_quests[quest_id] = {
            "name": template["name"],
            "description": template["description"].format(target=target),
            "type": template["type"],
            "target": target,
            "progress": 0,
            "completed": False,
            "claimed": False,
            "reward_gold": gold_reward,
            "reward_exp": exp_reward
        }
    
    return daily_quests

def generate_weekly_quests(hunter_level=1):
    """Generate weekly quests based on hunter level"""
    quest_data = load_quests_data()
    weekly_quests = {}
    
    # Scale quest difficulty with hunter level
    level_multiplier = max(1, hunter_level // 8)
    
    # Select 2-3 weekly quests
    weekly_templates = quest_data.get("weekly_templates", [])
    selected_templates = random.sample(weekly_templates, min(3, len(weekly_templates)))
    
    for template in selected_templates:
        quest_id = template["id"]
        
        # Scale target and rewards based on level
        min_target, max_target = template["target_range"]
        target = random.randint(min_target, max_target) * level_multiplier
        
        min_gold, max_gold = template["reward_gold_range"]
        gold_reward = random.randint(min_gold, max_gold) * level_multiplier
        
        min_exp, max_exp = template["reward_exp_range"]
        exp_reward = random.randint(min_exp, max_exp) * level_multiplier
        
        weekly_quests[quest_id] = {
            "name": template["name"],
            "description": template["description"].format(target=target),
            "type": template["type"],
            "target": target,
            "progress": 0,
            "completed": False,
            "claimed": False,
            "reward_gold": gold_reward,
            "reward_exp": exp_reward,
            "special_reward": template.get("special_reward", "Rare Item")
        }
    
    return weekly_quests

def get_available_special_quests(player_keys):
    """Get special quests that player can access with their keys"""
    quest_data = load_quests_data()
    available_quests = {}
    
    special_templates = quest_data.get("special_templates", [])
    
    for template in special_templates:
        required_key = template.get("required_key", "")
        if required_key in player_keys:
            quest_id = template["id"]
            available_quests[quest_id] = {
                "name": template["name"],
                "description": template["description"],
                "type": template["type"],
                "required_key": required_key,
                "reward_gold": template["reward_gold"],
                "reward_exp": template["reward_exp"],
                "special_reward": template["special_reward"],
                "completed": False,
                "claimed": False
            }
    
    return available_quests

def should_reset_daily_quests(last_reset_date):
    """Check if daily quests should be reset"""
    try:
        if not last_reset_date:
            return True
        
        last_reset = datetime.fromisoformat(last_reset_date)
        now = datetime.now()
        
        # Reset if it's a new day
        return last_reset.date() < now.date()
    except:
        return True

def should_reset_weekly_quests(last_reset_date):
    """Check if weekly quests should be reset (every Monday)"""
    try:
        if not last_reset_date:
            return True
        
        last_reset = datetime.fromisoformat(last_reset_date)
        now = datetime.now()
        
        # Calculate days since last Monday
        days_since_monday = now.weekday()
        last_monday = now - timedelta(days=days_since_monday)
        
        return last_reset.date() < last_monday.date()
    except:
        return True

def update_quest_progress(hunter_data, quest_type, amount=1):
    """Update quest progress for daily, weekly, and special quests"""
    quests = hunter_data.get('quests', {})
    
    # Update daily quests
    daily_quests = quests.get('daily', {})
    for quest_id, quest in daily_quests.items():
        if quest.get('type') == quest_type and not quest.get('completed', False):
            quest['progress'] = min(quest['progress'] + amount, quest['target'])
            if quest['progress'] >= quest['target']:
                quest['completed'] = True
    
    # Update weekly quests
    weekly_quests = quests.get('weekly', {})
    for quest_id, quest in weekly_quests.items():
        if quest.get('type') == quest_type and not quest.get('completed', False):
            quest['progress'] = min(quest['progress'] + amount, quest['target'])
            if quest['progress'] >= quest['target']:
                quest['completed'] = True
    
    # Update special quests
    special_quests = quests.get('special', {})
    for quest_id, quest in special_quests.items():
        if quest.get('type') == quest_type and not quest.get('completed', False):
            quest['completed'] = True

def get_quest_rewards(quest):
    """Get rewards for a completed quest"""
    rewards = {
        'gold': quest.get('reward_gold', 0),
        'exp': quest.get('reward_exp', 0),
        'special_reward': quest.get('special_reward', None)
    }
    return rewards

def add_dungeon_key_drop(hunter_data, hunter_rank):
    """Add chance for rare dungeon key drops based on hunter rank"""
    # Define available keys based on hunter rank
    rank_keys = {
        'E': ['Red Gate Key'],
        'D': ['Red Gate Key', 'Dungeon Key (Red)'],
        'C': ['Red Gate Key', 'Dungeon Key (Red)'],
        'B': ['Red Gate Key', 'Dungeon Key (Red)', 'Dungeon Key (Blue)'],
        'A': ['Red Gate Key', 'Dungeon Key (Red)', 'Dungeon Key (Blue)'],
        'S': ['Red Gate Key', 'Dungeon Key (Red)', 'Dungeon Key (Blue)', 'Dungeon Key (Gold)'],
        'National Level': ['Red Gate Key', 'Dungeon Key (Red)', 'Dungeon Key (Blue)', 'Dungeon Key (Gold)']
    }
    
    available_keys = rank_keys.get(hunter_rank, ['Red Gate Key'])
    
    # Very rare drop chance (2-5% based on rank)
    drop_chance = {
        'E': 0.02,    # 2%
        'D': 0.025,   # 2.5%
        'C': 0.03,    # 3%
        'B': 0.035,   # 3.5%
        'A': 0.04,    # 4%
        'S': 0.05,    # 5%
        'National Level': 0.06  # 6%
    }.get(hunter_rank, 0.02)
    
    if random.random() < drop_chance:
        key = random.choice(available_keys)
        inventory = hunter_data.get('inventory', {})
        
        # Ensure inventory is in dictionary format
        if isinstance(inventory, list):
            old_items = inventory
            inventory = {}
            for item in old_items:
                inventory[item] = inventory.get(item, 0) + 1
        
        inventory[key] = inventory.get(key, 0) + 1
        hunter_data['inventory'] = inventory
        return key
    
    return None