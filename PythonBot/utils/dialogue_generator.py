"""
Dynamic dialogue generation system for boss encounters and narrative events.
Generates thousands of unique conversations by combining predefined line sets.
"""

import random
from typing import List, Dict, Any

# Boss dialogue lines for dynamic generation
BOSS_OPENINGS = [
    "You dare step into my domain, mortal?",
    "Your journey ends here, hunter.",
    "So you think you can steal my power?",
    "Your light flickers weakly in this endless night.",
    "You've grown strong, but still lack the edge.",
    "Another pawn sent to die for the glory of man.",
    "Your soul reeks of fear.",
    "You chase shadows, but you cannot escape your fate.",
    "I've crushed heroes far greater than you.",
    "Your courage is misplaced.",
    "The shadows whisper of your approach, little hunter.",
    "You stand before a being of pure malice.",
    "Your power is nothing compared to mine.",
    "This realm belongs to me alone.",
    "You seek death so eagerly?",
    "I am the nightmare that haunts your kind.",
    "Your weapons cannot pierce my darkness.",
    "Foolish mortal, you know not what you face."
]

BOSS_RESPONSES = [
    "Your arrogance will be your undoing.",
    "I will savor your final gasp.",
    "You are nothing but a stepping stone on my path.",
    "Burn all you want. The darkness always wins.",
    "We'll see if your steel holds in the face of true power.",
    "Your fate is already written in blood.",
    "Fear is the shackles that will bind you forever.",
    "Hunters die, shadows endure.",
    "Then show me what greatness looks like.",
    "Fighting is futile.",
    "Your defiance only delays the inevitable.",
    "I have devoured stronger souls than yours.",
    "Power without wisdom is meaningless.",
    "You cannot comprehend my true nature.",
    "Your hope is but an illusion I will shatter.",
    "I am beyond your understanding.",
    "Your strength means nothing in my domain.",
    "You mistake desperation for courage."
]

BOSS_TAUNTS = [
    "Let's see if you can survive the storm of my wrath!",
    "I will break your spirit before your body.",
    "Very well. Let the dance of death begin!",
    "Prepare to be consumed by eternal darkness.",
    "Prove your strength to me!",
    "Your defiance is amusing.",
    "We shall see who emerges victorious.",
    "Bold words for a dying soul.",
    "So be it. Face your doom!",
    "Then prepare to face oblivion.",
    "Let the shadows claim you!",
    "Your end approaches swiftly.",
    "I shall enjoy breaking you.",
    "Feel the weight of true despair!",
    "Your light shall be extinguished!",
    "Come then, meet your fate!",
    "The abyss calls your name!",
    "Embrace the darkness that awaits!"
]

PLAYER_REPLIES = [
    "I'm not afraid of you. I've faced worse.",
    "Not while I still draw breath.",
    "I'll take whatever it takes to become stronger.",
    "Then I'll be the flame that burns through your darkness.",
    "Strength is forged in battle, and I'm ready.",
    "I'm no pawn. I make my own destiny.",
    "Fear keeps me sharp.",
    "I'm the hunter now.",
    "I've come too far to turn back now.",
    "Courage is what keeps me fighting.",
    "I won't let you hurt anyone else.",
    "My resolve is stronger than your darkness.",
    "I carry the hopes of those who believe in me.",
    "Every battle makes me stronger.",
    "I refuse to bow to fear.",
    "Your threats mean nothing to me.",
    "I've trained for this moment.",
    "Justice will prevail over evil."
]

PLAYER_CHALLENGES = [
    "Then prepare to be crushed.",
    "I'll make sure it's my victory you taste instead.",
    "Then I'll make sure I'm the last stone you step on.",
    "Not today.",
    "I've survived worse than you.",
    "Then I'll write my own ending.",
    "Then I'll break those chains.",
    "Then I'll become the shadow you fear.",
    "By taking you down.",
    "Then I'll fight until the end.",
    "Your reign of terror ends here!",
    "I'll be the light that pierces your darkness!",
    "Then let's settle this once and for all!",
    "I'll show you the power of human determination!",
    "Your dark age is over!",
    "I'll forge my own path through your shadows!",
    "Then witness the strength of my conviction!",
    "I'll prove that hope conquers fear!"
]

# Rank-specific dialogue modifiers
RANK_MODIFIERS = {
    "E": {
        "boss_prefix": "pathetic",
        "player_confidence": "nervous but determined"
    },
    "D": {
        "boss_prefix": "weak",
        "player_confidence": "growing confident"
    },
    "C": {
        "boss_prefix": "adequate",
        "player_confidence": "steady and focused"
    },
    "B": {
        "boss_prefix": "competent",
        "player_confidence": "bold and ready"
    },
    "A": {
        "boss_prefix": "formidable",
        "player_confidence": "experienced and calm"
    },
    "S": {
        "boss_prefix": "dangerous",
        "player_confidence": "supremely confident"
    },
    "National Level Hunter": {
        "boss_prefix": "truly threatening",
        "player_confidence": "elite and unwavering"
    },
    "Monarch": {
        "boss_prefix": "worthy",
        "player_confidence": "legendary and fearless"
    }
}

def generate_boss_conversation(player_rank: str = "E") -> List[str]:
    """Generate a dynamic 5-line boss conversation based on player rank"""
    
    # Select random lines
    opening = random.choice(BOSS_OPENINGS)
    player_reply = random.choice(PLAYER_REPLIES)
    boss_response = random.choice(BOSS_RESPONSES)
    player_challenge = random.choice(PLAYER_CHALLENGES)
    boss_taunt = random.choice(BOSS_TAUNTS)
    
    # Apply rank modifiers for immersion
    modifier = RANK_MODIFIERS.get(player_rank, RANK_MODIFIERS["E"])
    
    # Sometimes add rank-specific flavor
    if random.random() < 0.3:  # 30% chance to add rank flavor
        if player_rank in ["S", "National Level Hunter", "Monarch"]:
            opening = f"Interesting... a {player_rank} hunter. {opening}"
        elif player_rank in ["E", "D"]:
            opening = f"Another {modifier['boss_prefix']} {player_rank} rank? {opening}"
    
    conversation = [
        f"Boss: \"{opening}\"",
        f"Player: \"{player_reply}\"",
        f"Boss: \"{boss_response}\"",
        f"Player: \"{player_challenge}\"",
        f"Boss: \"{boss_taunt}\""
    ]
    
    return conversation

def generate_encounter_dialogue(encounter_type: str, monster_name: str = "") -> Dict[str, Any]:
    """Generate contextual dialogue for different encounter types"""
    
    dialogues = {
        "mysterious_meeting": {
            "openings": [
                f"A strange {monster_name} regards you with unusual intelligence...",
                f"The {monster_name} speaks in broken common tongue...",
                f"This {monster_name} seems different from the others...",
                f"You sense no immediate hostility from this {monster_name}..."
            ],
            "responses": [
                "What brings a hunter to these cursed lands?",
                "You... different from other hunters. Why?",
                "I sense great power within you, mortal.",
                "Perhaps we need not be enemies this day."
            ]
        },
        "territorial_warning": {
            "openings": [
                f"The {monster_name} blocks your path, growling menacingly...",
                f"A massive {monster_name} emerges, marking its territory...",
                f"The {monster_name} rears up, displaying dominance...",
                f"Warning snarls echo as the {monster_name} approaches..."
            ],
            "responses": [
                "This is MY domain! Leave or face the consequences!",
                "Turn back, hunter, while you still draw breath!",
                "You dare trespass in my hunting grounds?",
                "One step closer and I'll tear you apart!"
            ]
        },
        "desperate_plea": {
            "openings": [
                f"A wounded {monster_name} collapses before you...",
                f"The {monster_name} whimpers, clearly in distress...",
                f"This {monster_name} seems to be asking for help...",
                f"The {monster_name} gestures weakly toward something..."
            ],
            "responses": [
                "Please... help... young ones trapped...",
                "Hunter... not all monsters... evil...",
                "Help me... and I share... ancient secret...",
                "My pack... dying... need hunter's aid..."
            ]
        }
    }
    
    selected = dialogues.get(encounter_type, dialogues["mysterious_meeting"])
    
    return {
        "opening": random.choice(selected["openings"]),
        "response": random.choice(selected["responses"])
    }

def generate_combat_taunts(monster_rank: str, turn_number: int) -> str:
    """Generate dynamic combat taunts based on monster rank and battle progress"""
    
    early_taunts = [
        "You think you can defeat me so easily?",
        "I'm just getting started, hunter!",
        "Feel the power of my rage!",
        "Your attacks are pathetic!"
    ]
    
    mid_taunts = [
        "Impressive, but not enough!",
        "You're stronger than I expected...",
        "Now I'm getting serious!",
        "Let's see how you handle THIS!"
    ]
    
    late_taunts = [
        "Impossible! How are you still standing?",
        "I won't be defeated by a mere hunter!",
        "This cannot be happening!",
        "You... you're no ordinary hunter..."
    ]
    
    if turn_number <= 2:
        taunts = early_taunts
    elif turn_number <= 4:
        taunts = mid_taunts
    else:
        taunts = late_taunts
    
    # Add rank-specific intensity
    rank_intensity = {
        "E": "",
        "D": " (The monster's eyes glow with fury)",
        "C": " (Dark energy radiates from the creature)",
        "B": " (The air itself seems to tremble)",
        "A": " (Reality warps around the monster)",
        "S": " (The very fabric of space distorts)"
    }
    
    taunt = random.choice(taunts)
    intensity = rank_intensity.get(monster_rank, "")
    
    return f"{taunt}{intensity}"