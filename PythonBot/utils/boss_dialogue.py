import json
import random
from typing import Dict, List, Optional

class BossDialogueManager:
    """Manages authentic Solo Leveling boss conversations and turn-based combat dialogue"""
    
    def __init__(self):
        self.dialogues = self.load_boss_dialogues()
    
    def load_boss_dialogues(self) -> Dict:
        """Load boss dialogue data from JSON file"""
        try:
            with open('data/boss_dialogues.json', 'r') as f:
                data = json.load(f)
                return data.get('boss_dialogues', {})
        except FileNotFoundError:
            return {}
    
    def get_encounter_intro(self, boss_id: str) -> str:
        """Get random encounter introduction dialogue"""
        if boss_id not in self.dialogues:
            return "A powerful enemy stands before you, radiating immense magical energy."
        
        intros = self.dialogues[boss_id].get('encounter_intro', [])
        return random.choice(intros) if intros else "The boss eyes you with interest."
    
    def get_combat_start(self, boss_id: str) -> str:
        """Get combat start dialogue"""
        if boss_id not in self.dialogues:
            return "Let the battle begin!"
        
        return self.dialogues[boss_id].get('combat_start', "Prepare yourself for battle!")
    
    def get_player_action_response(self, boss_id: str, action: str) -> str:
        """Get boss response to player action"""
        if boss_id not in self.dialogues:
            return "The boss reacts to your action."
        
        responses = self.dialogues[boss_id].get(f'player_{action}', [])
        return random.choice(responses) if responses else f"The boss acknowledges your {action}."
    
    def get_boss_attack_dialogue(self, boss_id: str) -> str:
        """Get boss attack dialogue"""
        if boss_id not in self.dialogues:
            return "The boss launches a devastating attack!"
        
        attacks = self.dialogues[boss_id].get('boss_attack', [])
        return random.choice(attacks) if attacks else "The boss strikes with overwhelming force!"
    
    def get_low_health_dialogue(self, boss_id: str) -> str:
        """Get dialogue when boss is at low health"""
        if boss_id not in self.dialogues:
            return "The boss seems weakened but still dangerous."
        
        low_health = self.dialogues[boss_id].get('low_health', [])
        return random.choice(low_health) if low_health else "The boss's power wavers..."
    
    def get_victory_dialogue(self, boss_id: str, player_won: bool) -> str:
        """Get victory/defeat dialogue"""
        if boss_id not in self.dialogues:
            if player_won:
                return "You have achieved victory against a formidable opponent."
            else:
                return "The boss stands victorious over your fallen form."
        
        dialogue_key = 'victory_player' if player_won else 'victory_boss'
        victory_lines = self.dialogues[boss_id].get(dialogue_key, [])
        
        if victory_lines:
            return random.choice(victory_lines)
        else:
            return "The battle concludes with honor on both sides." if player_won else "Defeat teaches valuable lessons."
    
    def get_contextual_dialogue(self, boss_id: str, context: str, **kwargs) -> str:
        """Get contextual dialogue based on combat situation"""
        boss_hp_percent = kwargs.get('boss_hp_percent', 100)
        player_hp_percent = kwargs.get('player_hp_percent', 100)
        turn_count = kwargs.get('turn_count', 1)
        
        # Low health dialogue
        if boss_hp_percent <= 25:
            return self.get_low_health_dialogue(boss_id)
        
        # Regular action responses
        if context in ['attack', 'defend', 'flee']:
            return self.get_player_action_response(boss_id, context)
        
        # Boss attack
        if context == 'boss_attack':
            return self.get_boss_attack_dialogue(boss_id)
        
        # Default fallback
        return self.get_encounter_intro(boss_id)

# Global instance for easy access
dialogue_manager = BossDialogueManager()