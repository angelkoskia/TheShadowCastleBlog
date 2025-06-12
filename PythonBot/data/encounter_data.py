"""
Encounter system data for narrative events, dialogue choices, and monster lore progression.
Solo Leveling themed encounters with branching dialogue paths.
"""

# Enhanced monster data with progressive lore system
MONSTERS_LORE = {
    "goblin": {
        "name": "Goblin",
        "hp": 50, "attack": 10, "defense": 5,
        "exp_reward": 25, "gold_reward": 15,
        "rank": "E",
        "lore": [
            {
                "hunts_needed": 0, 
                "description": "A small, green-skinned humanoid creature commonly found in E-rank gates. Known for their crude weapons and cowardly nature when alone."
            },
            {
                "hunts_needed": 5, 
                "description": "After observing multiple goblins, you've noticed they communicate through guttural sounds and rely on pack tactics. Their agility compensates for their small stature, and they show surprising cunning when cornered."
            },
            {
                "hunts_needed": 15, 
                "description": "Through extensive encounters, you understand that goblins serve as scouts for larger magical beasts. Their primitive social structure revolves around dominance hierarchies, and they possess basic tool-making abilities. Some carry enchanted trinkets stolen from fallen hunters."
            }
        ]
    },
    "orc": {
        "name": "Orc",
        "hp": 120, "attack": 25, "defense": 15,
        "exp_reward": 60, "gold_reward": 35,
        "rank": "D",
        "lore": [
            {
                "hunts_needed": 0,
                "description": "A brutish, powerful humanoid with thick green skin. Orcs are larger and more aggressive than goblins, wielding heavy weapons with devastating force."
            },
            {
                "hunts_needed": 3,
                "description": "Orcs possess remarkable endurance and thick hides that can deflect basic attacks. Their fighting style is direct and relies on overwhelming strength, but they're vulnerable to magic and swift hit-and-run tactics."
            },
            {
                "hunts_needed": 10,
                "description": "You've learned that orcs have a tribal warrior culture that values strength above all else. They craft crude but effective armor from monster hides and bones. Elder orcs can enter berserker states that double their combat effectiveness."
            }
        ]
    },
    "dire_wolf": {
        "name": "Dire Wolf",
        "hp": 80, "attack": 30, "defense": 8,
        "exp_reward": 45, "gold_reward": 25,
        "rank": "D",
        "lore": [
            {
                "hunts_needed": 0,
                "description": "A massive wolf with glowing red eyes and shadowy fur. These creatures hunt in coordinated packs and are known for their lightning-fast strikes."
            },
            {
                "hunts_needed": 4,
                "description": "Dire wolves exhibit supernatural intelligence and can phase through shadows for brief moments. They communicate through howls that can disorient their prey and coordinate complex pack maneuvers."
            },
            {
                "hunts_needed": 12,
                "description": "These apex predators are actually magical beasts touched by shadow magic. Alpha dire wolves can command lesser wolves and possess regenerative abilities. Their howls can induce fear effects that paralyze weaker hunters."
            }
        ]
    },
    "shadow_assassin": {
        "name": "Shadow Assassin",
        "hp": 100, "attack": 45, "defense": 12,
        "exp_reward": 85, "gold_reward": 50,
        "rank": "C",
        "lore": [
            {
                "hunts_needed": 0,
                "description": "A humanoid figure wreathed in dark energy, wielding twin daggers. Shadow Assassins move with supernatural speed and can blend into darkness."
            },
            {
                "hunts_needed": 2,
                "description": "These creatures were once human hunters who were corrupted by shadow magic. They retain their combat training but are driven by an insatiable hunger for magical energy."
            },
            {
                "hunts_needed": 8,
                "description": "Shadow Assassins are created through forbidden rituals performed in the deepest levels of high-rank dungeons. They can phase between dimensions for short periods and their weapons are infused with soul-draining magic."
            }
        ]
    }
}

# Dialogue node system for narrative encounters
DIALOGUE_NODES = {
    "lost_merchant_start": {
        "text": "A frightened merchant emerges from behind a boulder, clutching a damaged briefcase. 'Hunter! Thank the system you're here! I was ambushed by monsters and my escort fled. Can you help me reach the gate exit?'",
        "image_url": None,
        "choices": [
            {"label": "Offer to escort him safely", "next_node": "merchant_escort", "outcome_type": "dialogue"},
            {"label": "Ask about his cargo first", "next_node": "merchant_cargo", "outcome_type": "dialogue"},
            {"label": "Demand payment upfront", "next_node": "merchant_payment", "outcome_type": "dialogue"},
            {"label": "Ignore and continue hunting", "outcome_type": "end", "text": "You walk past the merchant, focused on your own mission. His desperate calls fade behind you."}
        ]
    },
    "merchant_escort": {
        "text": "The merchant's face lights up with relief. 'You're truly a noble hunter! I'll make sure the Association hears of your kindness.' He pulls out a small healing potion. 'Please, take this as a token of my gratitude.'",
        "choices": [
            {"label": "Accept the potion graciously", "outcome_type": "reward", "item": "health_potion", "text": "You gained a Health Potion! Your reputation with merchants increases."},
            {"label": "Refuse and escort for free", "outcome_type": "reward", "exp": 50, "text": "Your selfless act earns you 50 bonus EXP and increases your karma rating."}
        ]
    },
    "merchant_cargo": {
        "text": "The merchant hesitates, then opens his briefcase slightly. You glimpse magical crystals inside. 'Mana stones... I'm transporting them to the city for processing. Very valuable, which is why the monsters targeted me.'",
        "choices": [
            {"label": "Offer protection for a crystal", "next_node": "merchant_negotiate", "outcome_type": "dialogue"},
            {"label": "Warn him about carrying valuables alone", "next_node": "merchant_escort", "outcome_type": "dialogue"},
            {"label": "Suggest he hides here while you clear the area", "outcome_type": "reward", "gold": 100, "text": "You clear the surrounding monsters. The grateful merchant pays you 100 gold."}
        ]
    },
    "merchant_payment": {
        "text": "The merchant frowns. 'I... I understand hunters need compensation, but I've already lost most of my goods to the ambush. I can offer 75 gold, it's all I have left.'",
        "choices": [
            {"label": "Accept the payment", "outcome_type": "reward", "gold": 75, "text": "You gained 75 gold. The merchant seems relieved but wary."},
            {"label": "Reduce your fee to 50 gold", "outcome_type": "reward", "gold": 50, "text": "Your reasonable approach earns you 50 gold and the merchant's genuine gratitude."},
            {"label": "Demand more or no deal", "outcome_type": "end", "text": "The merchant sadly shakes his head. 'I understand...' He retreats back behind the boulder."}
        ]
    },
    "merchant_negotiate": {
        "text": "The merchant considers your proposal. 'One small mana crystal for safe escort... it's expensive, but my life is worth more. Agreed, but please be careful - these stones are unstable if mishandled.'",
        "choices": [
            {"label": "Accept the deal", "outcome_type": "reward", "item": "mana_crystal", "text": "You gained a Mana Crystal! This valuable item can enhance magical abilities."}
        ]
    },
    
    "mysterious_shrine_start": {
        "text": "You discover an ancient shrine covered in glowing runes. The air hums with magical energy, and you feel drawn to touch the central crystal. The runes seem to pulse in rhythm with your heartbeat.",
        "choices": [
            {"label": "Touch the crystal carefully", "next_node": "shrine_blessing", "outcome_type": "dialogue"},
            {"label": "Study the runes first", "next_node": "shrine_study", "outcome_type": "dialogue"},
            {"label": "Leave immediately", "outcome_type": "end", "text": "You sense danger and retreat. Sometimes wisdom is knowing when not to act."}
        ]
    },
    "shrine_blessing": {
        "text": "As your hand touches the crystal, warm energy flows through you. The shrine recognizes you as a worthy hunter. You feel temporarily strengthened.",
        "choices": [
            {"label": "Accept the blessing", "outcome_type": "reward", "buff": "shrine_blessing", "text": "You gained Shrine Blessing! +5 to all stats for your next 3 battles."}
        ]
    },
    "shrine_study": {
        "text": "The runes tell the story of an ancient hunter who made a great sacrifice here. You understand the shrine's purpose - to test the worthiness of those who seek power.",
        "choices": [
            {"label": "Offer a small tribute", "outcome_type": "reward", "exp": 75, "text": "Your respectful offering earns you 75 EXP and ancient knowledge."},
            {"label": "Touch the crystal with understanding", "next_node": "shrine_blessing", "outcome_type": "dialogue"}
        ]
    },

    "goblin_trader_start": {
        "text": "A unique goblin wearing a merchant's vest approaches you cautiously. Unlike its aggressive kin, this one carries a small cart of goods. 'Hunter-friend! Me trader, not fighter! Want to see special items?'",
        "choices": [
            {"label": "Browse the trader's wares", "next_node": "goblin_shop", "outcome_type": "dialogue"},
            {"label": "Ask how he learned to trade", "next_node": "goblin_story", "outcome_type": "dialogue"},
            {"label": "Attack the goblin", "outcome_type": "combat", "monster_id": "goblin", "text": "The trader goblin squeaks in fear before defending itself!"}
        ]
    },
    "goblin_shop": {
        "text": "The goblin displays his wares: a rusty but sharp dagger, a small healing herb, and a strange glowing pebble. 'Very good prices for hunter-friend! Choose wisely!'",
        "choices": [
            {"label": "Buy the dagger (30 gold)", "outcome_type": "reward", "item": "goblin_dagger", "gold": -30, "text": "You purchased a Goblin Dagger! It's crude but surprisingly effective."},
            {"label": "Buy the herb (15 gold)", "outcome_type": "reward", "item": "healing_herb", "gold": -15, "text": "You gained a Healing Herb! Restores 25 HP when used."},
            {"label": "Buy the pebble (50 gold)", "outcome_type": "reward", "item": "luck_stone", "gold": -50, "text": "You gained a Luck Stone! This mysterious item might bring fortune."},
            {"label": "Just browse and leave", "outcome_type": "end", "text": "The goblin waves goodbye. 'Come back anytime, hunter-friend!'"}
        ]
    },
    "goblin_story": {
        "text": "'Me different! Me learn from watching human traders at gate entrance. Violence bad for business, trade good for everyone!' The goblin's eyes sparkle with entrepreneurial spirit.",
        "choices": [
            {"label": "Encourage his peaceful ways", "next_node": "goblin_shop", "outcome_type": "dialogue"},
            {"label": "Give him business advice", "outcome_type": "reward", "exp": 40, "text": "Your wisdom earns you 40 EXP and a grateful goblin ally."}
        ]
    }
}

# Encounter probability system
ENCOUNTERS = {
    "combat_goblin": {"type": "combat", "monster_id": "goblin", "chance": 40},
    "combat_orc": {"type": "combat", "monster_id": "orc", "chance": 25},
    "combat_dire_wolf": {"type": "combat", "monster_id": "dire_wolf", "chance": 20},
    "combat_shadow_assassin": {"type": "combat", "monster_id": "shadow_assassin", "chance": 5},
    "dialogue_merchant": {"type": "dialogue", "start_node": "lost_merchant_start", "chance": 4},
    "dialogue_shrine": {"type": "dialogue", "start_node": "mysterious_shrine_start", "chance": 3},
    "dialogue_goblin_trader": {"type": "dialogue", "start_node": "goblin_trader_start", "chance": 3}
}

# Special encounter rewards and items
ENCOUNTER_ITEMS = {
    "health_potion": {
        "name": "Health Potion",
        "description": "Restores 50 HP when consumed",
        "heal_amount": 50,
        "stackable": True,
        "value": 25
    },
    "mana_crystal": {
        "name": "Mana Crystal",
        "description": "A crystallized form of pure mana energy",
        "mana_restore": 30,
        "stackable": True,
        "value": 75
    },
    "goblin_dagger": {
        "name": "Goblin Dagger",
        "description": "A crude but effective weapon crafted by goblin traders",
        "attack": 8,
        "type": "weapon",
        "stackable": False,
        "value": 40
    },
    "healing_herb": {
        "name": "Healing Herb",
        "description": "A natural remedy that restores health",
        "heal_amount": 25,
        "stackable": True,
        "value": 20
    },
    "luck_stone": {
        "name": "Luck Stone",
        "description": "A mysterious pebble that seems to shimmer with good fortune",
        "effect": "luck_boost",
        "stackable": False,
        "value": 60
    }
}

# Temporary buffs from encounters
ENCOUNTER_BUFFS = {
    "shrine_blessing": {
        "name": "Shrine Blessing",
        "description": "+5 to all stats for next 3 battles",
        "strength_bonus": 5,
        "agility_bonus": 5,
        "intelligence_bonus": 5,
        "duration": 3
    }
}

def get_monster_lore(monster_id: str, kills_done: int) -> str:
    """Get the most detailed monster lore unlocked based on kill count"""
    monster_data = MONSTERS_LORE.get(monster_id)
    if not monster_data or 'lore' not in monster_data:
        return None

    unlocked_lore = None
    for lore_entry in monster_data['lore']:
        if kills_done >= lore_entry['hunts_needed']:
            unlocked_lore = lore_entry['description']
        else:
            break
    
    return unlocked_lore

def get_encounter_by_chance() -> dict:
    """Randomly select an encounter based on probability weights"""
    import random
    
    total_chance = sum(encounter["chance"] for encounter in ENCOUNTERS.values())
    rand_num = random.uniform(0, total_chance)
    
    cumulative_chance = 0
    for encounter_id, encounter_data in ENCOUNTERS.items():
        cumulative_chance += encounter_data["chance"]
        if rand_num <= cumulative_chance:
            return encounter_data
    
    # Fallback to basic goblin combat
    return ENCOUNTERS["combat_goblin"]