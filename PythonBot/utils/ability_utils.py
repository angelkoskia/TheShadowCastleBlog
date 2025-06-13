import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional

def load_abilities_data() -> Dict[str, Any]:
    """Load abilities data from JSON file"""
    try:
        with open('data/abilities.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def get_ability_data(ability_id: str) -> Optional[Dict[str, Any]]:
    """Get data for a specific ability"""
    abilities = load_abilities_data()
    return abilities.get(ability_id)

def calculate_cooldown_end(turns_cooldown: int) -> str:
    """Calculate when an ability cooldown ends (in seconds for real-time)"""
    cooldown_seconds = turns_cooldown * 10  # 10 seconds per turn
    return (datetime.now() + timedelta(seconds=cooldown_seconds)).isoformat()

def is_ability_on_cooldown(hunter: Dict[str, Any], ability_id: str) -> bool:
    """Check if an ability is currently on cooldown"""
    active_cooldowns = hunter.get('active_cooldowns', {})
    if ability_id in active_cooldowns:
        cooldown_end_str = active_cooldowns[ability_id]
        try:
            cooldown_end_time = datetime.fromisoformat(cooldown_end_str)
            return datetime.now() < cooldown_end_time
        except ValueError:
            # Invalid datetime format, remove it
            del active_cooldowns[ability_id]
    return False

def get_remaining_cooldown(hunter: Dict[str, Any], ability_id: str) -> Optional[str]:
    """Get remaining cooldown time as a formatted string"""
    active_cooldowns = hunter.get('active_cooldowns', {})
    if ability_id in active_cooldowns:
        cooldown_end_str = active_cooldowns[ability_id]
        try:
            cooldown_end_time = datetime.fromisoformat(cooldown_end_str)
            remaining = cooldown_end_time - datetime.now()
            if remaining.total_seconds() > 0:
                minutes, seconds = divmod(remaining.total_seconds(), 60)
                if minutes > 0:
                    return f"{int(minutes)}m {int(seconds)}s"
                else:
                    return f"{int(seconds)}s"
        except ValueError:
            pass
    return None

def apply_ability_effect(hunter: Dict[str, Any], monster: Dict[str, Any], ability_id: str) -> Tuple[str, bool]:
    """Apply an ability's effect and return result message and success status"""
    ability_data = get_ability_data(ability_id)
    if not ability_data:
        return "Unknown ability.", False

    # Check mana cost
    if hunter.get('mana', 0) < ability_data['mana_cost']:
        return "Not enough mana!", False

    # Check cooldown
    if is_ability_on_cooldown(hunter, ability_id):
        remaining_cd = get_remaining_cooldown(hunter, ability_id)
        return f"{ability_data['name']} is on cooldown. {remaining_cd} remaining.", False

    # Deduct mana and set cooldown
    hunter['mana'] = max(0, hunter.get('mana', 0) - ability_data['mana_cost'])
    hunter.setdefault('active_cooldowns', {})[ability_id] = calculate_cooldown_end(ability_data['cooldown_turns'])

    damage_dealt = 0
    healing_done = 0
    message = ""

    ability_type = ability_data.get('type', 'attack')
    
    if ability_type == "attack":
        base_attack = hunter.get('strength', 10)
        damage_multiplier = ability_data.get('damage_multiplier', 1.0)
        effective_attack = int(base_attack * damage_multiplier)
        damage_dealt = max(1, effective_attack - monster.get('defense', 0))
        monster['hp'] = max(0, monster.get('hp', 1) - damage_dealt)
        message = f"You used **{ability_data['name']}**! It dealt {damage_dealt} damage to the {monster.get('name', 'enemy')}."
        
        # Apply special effects
        effect = ability_data.get('effect', 'none')
        if effect == 'mana_drain' and 'mana' in monster:
            mana_drain = damage_dealt // 2
            monster['mana'] = max(0, monster.get('mana', 0) - mana_drain)
            message += f" Drained {mana_drain} mana!"
        elif effect == 'freeze_chance':
            import random
            if random.random() < 0.3:  # 30% chance to freeze
                monster['frozen_turns'] = 1
                message += " The enemy is frozen!"
    
    elif ability_type == "magic":
        base_intelligence = hunter.get('intelligence', 10)
        damage_multiplier = ability_data.get('damage_multiplier', 1.0)
        effective_attack = int(base_intelligence * damage_multiplier)
        damage_dealt = max(1, effective_attack - monster.get('magic_defense', monster.get('defense', 0) // 2))
        monster['hp'] = max(0, monster.get('hp', 1) - damage_dealt)
        message = f"You cast **{ability_data['name']}**! It dealt {damage_dealt} magical damage."
        
        # Apply magic effects
        effect = ability_data.get('effect', 'none')
        if effect == 'freeze_chance':
            import random
            if random.random() < 0.4:  # 40% chance for magic freeze
                monster['frozen_turns'] = 2
                message += " The enemy is frozen solid!"
    
    elif ability_type == "support":
        healing_amount = ability_data.get('healing_amount', 0)
        if healing_amount > 0:
            old_hp = hunter.get('hp', 0)
            max_hp = hunter.get('max_hp', 100)
            hunter['hp'] = min(max_hp, old_hp + healing_amount)
            healing_done = hunter['hp'] - old_hp
            message = f"You used **{ability_data['name']}**! Restored {healing_done} HP."
    
    elif ability_type == "buff":
        effect = ability_data.get('effect', 'none')
        duration = ability_data.get('duration', 3)
        buff_amount = ability_data.get('buff_amount', 10)
        
        if effect == 'attack_buff':
            hunter.setdefault('temp_buffs', {})['attack_buff'] = {
                'amount': buff_amount,
                'duration': duration,
                'turns_left': duration
            }
            message = f"You used **{ability_data['name']}**! Attack power increased by {buff_amount} for {duration} turns."
    
    elif ability_type == "utility":
        effect = ability_data.get('effect', 'none')
        if effect == 'evade_next_attack':
            hunter.setdefault('temp_buffs', {})['evasion'] = {
                'turns_left': 1
            }
            message = f"You used **{ability_data['name']}**! You will evade the next attack."

    # Clean up expired cooldowns
    cleanup_expired_cooldowns(hunter)
    
    return message, True

def cleanup_expired_cooldowns(hunter: Dict[str, Any]) -> None:
    """Remove expired cooldowns from hunter data"""
    active_cooldowns = hunter.get('active_cooldowns', {})
    expired_abilities = []
    
    for ability_id, cooldown_end_str in active_cooldowns.items():
        try:
            cooldown_end_time = datetime.fromisoformat(cooldown_end_str)
            if datetime.now() > cooldown_end_time:
                expired_abilities.append(ability_id)
        except ValueError:
            expired_abilities.append(ability_id)
    
    for ability_id in expired_abilities:
        del active_cooldowns[ability_id]

def process_turn_effects(hunter: Dict[str, Any]) -> str:
    """Process turn-based effects like buffs and debuffs"""
    messages = []
    temp_buffs = hunter.get('temp_buffs', {})
    expired_buffs = []
    
    for buff_name, buff_data in temp_buffs.items():
        turns_left = buff_data.get('turns_left', 0)
        if turns_left <= 1:
            expired_buffs.append(buff_name)
            if buff_name == 'attack_buff':
                messages.append("Your attack boost has worn off.")
            elif buff_name == 'evasion':
                messages.append("Your evasion boost has worn off.")
        else:
            buff_data['turns_left'] = turns_left - 1
    
    for buff_name in expired_buffs:
        del temp_buffs[buff_name]
    
    return " ".join(messages)

def get_effective_stats(hunter: Dict[str, Any]) -> Dict[str, int]:
    """Get hunter's effective stats including temporary buffs"""
    base_stats = {
        'strength': hunter.get('strength', 10),
        'agility': hunter.get('agility', 10),
        'intelligence': hunter.get('intelligence', 10),
        'defense': hunter.get('defense', 5)
    }
    
    temp_buffs = hunter.get('temp_buffs', {})
    
    # Apply attack buff
    if 'attack_buff' in temp_buffs:
        buff_amount = temp_buffs['attack_buff'].get('amount', 0)
        base_stats['strength'] += buff_amount
    
    return base_stats

def initialize_hunter_abilities(hunter: Dict[str, Any]) -> None:
    """Initialize hunter with mana and basic abilities if not present"""
    hunter.setdefault('mana', 100)
    hunter.setdefault('max_mana', 100)
    hunter.setdefault('abilities', ['power_strike', 'heal'])
    hunter.setdefault('active_cooldowns', {})
    hunter.setdefault('temp_buffs', {})

def get_hunter_abilities_by_level(level: int) -> list:
    """Get abilities a hunter should have based on their level"""
    base_abilities = ['power_strike', 'heal']
    
    if level >= 10:
        base_abilities.append('shadow_step')
    if level >= 15:
        base_abilities.append('mana_burn')
    if level >= 25:
        base_abilities.append('berserker_rage')
    if level >= 35:
        base_abilities.append('ice_spike')
    
    return base_abilities