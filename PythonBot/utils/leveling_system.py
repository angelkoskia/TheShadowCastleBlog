"""Leveling system and rank utilities for the Solo Leveling RPG bot."""

import json
import discord
from typing import Dict, Tuple, Optional
import os

# Rank role mapping for Discord role management - Solo Leveling Lore Accurate
RANK_ROLES = {
    range(1, 11): "E Rank",
    range(11, 21): "D Rank",
    range(21, 31): "C Rank",
    range(31, 41): "B Rank",
    range(41, 51): "A Rank",
    range(51, 61): "S Rank",
    range(61, 101): "National Level Hunter",
    range(101, 1000): "Monarch"
}

def get_rank_role_name(level: int) -> str:
    """Return the rank role name based on player level."""
    for rank_range, role_name in RANK_ROLES.items():
        if level in rank_range:
            return role_name
    return "Monarch"  # Default for very high levels

class LevelingSystem:
    """Handles experience, leveling, and rank logic for players."""
    def __init__(self):
        # EXP requirements for each level range
        self.level_ranges = {
            (1, 10): (100, 300),      # 100-300 EXP per level
            (11, 20): (500, 1000),    # 500-1000 EXP per level
            (21, 30): (1500, 2500),   # 1500-2500 EXP per level
            (31, 40): (3000, 4500),   # 3000-4500 EXP per level
            (41, 50): (5000, 7000),   # 5000-7000 EXP per level
            (51, 60): (8000, 10000),  # 8000-10000 EXP per level
            (61, 70): (12000, 15000), # 12000-15000 EXP per level
            (71, 80): (18000, 25000), # 18000-25000 EXP per level
            (81, 90): (30000, 40000), # 30000-40000 EXP per level
            (91, 100): (50000, 100000) # 50000-100000 EXP per level
        }
        
        # Rank mappings based on level - Solo Leveling Lore Accurate
        self.rank_mappings = {
            (1, 10): 'E Rank',
            (11, 20): 'D Rank',
            (21, 30): 'C Rank',
            (31, 40): 'B Rank',
            (41, 50): 'A Rank',
            (51, 60): 'S Rank',
            (61, 100): 'National Level Hunter',
            (101, 999): 'Monarch'
        }
        
        # Pre-calculated EXP requirements for each level
        self._exp_table = self._generate_exp_table()
    
    def _generate_exp_table(self) -> Dict[int, int]:
        """Generate a table of total EXP required to START each level"""
        exp_table = {1: 0}  # Level 1 starts at 0 EXP
        
        total_exp = 0
        for level in range(2, 101):  # Calculate up to level 100
            # EXP needed to go from previous level to this level
            exp_for_this_level = self._get_exp_for_level(level)
            total_exp += exp_for_this_level
            exp_table[level] = total_exp
        
        # For levels above 100, use the highest range
        for level in range(101, 200):
            exp_for_this_level = 100000  # Max from 91-100 range
            total_exp += exp_for_this_level
            exp_table[level] = total_exp
            
        return exp_table
    
    def _get_exp_for_level(self, level: int) -> int:
        """Get EXP required to reach a specific level from the previous level"""
        for (min_level, max_level), (min_exp, max_exp) in self.level_ranges.items():
            if min_level <= level <= max_level:
                # Scale EXP within the range
                progress = (level - min_level) / (max_level - min_level)
                return int(min_exp + (max_exp - min_exp) * progress)
        
        # For levels above 100, use max EXP from highest range
        return 100000
    
    def get_level_from_exp(self, total_exp: int) -> int:
        """Calculate level based on total EXP"""
        for level in range(1, len(self._exp_table) + 1):
            if total_exp < self._exp_table.get(level, float('inf')):
                return level - 1
        return len(self._exp_table)
    
    def get_exp_for_next_level(self, current_level: int) -> int:
        """Get EXP required to reach the next level"""
        if current_level >= 200:
            return 100000  # Cap at max EXP requirement
        return self._exp_table.get(current_level + 1, 0) - self._exp_table.get(current_level, 0)
    
    def get_exp_progress(self, total_exp: int, current_level: int) -> Tuple[int, int]:
        """Get current EXP progress toward next level"""
        # Get the EXP required to START the current level
        current_level_start_exp = self._exp_table.get(current_level, 0)
        
        # Calculate EXP within current level
        exp_in_current_level = total_exp - current_level_start_exp
        exp_needed_for_next = self.get_exp_for_next_level(current_level)
        
        # Ensure we don't show negative values
        if exp_in_current_level < 0:
            exp_in_current_level = 0
        
        # Ensure progress doesn't exceed what's needed for next level
        if exp_in_current_level > exp_needed_for_next:
            exp_in_current_level = exp_needed_for_next
        
        return exp_in_current_level, exp_needed_for_next
    
    def get_rank_for_level(self, level: int) -> str:
        """Get rank name based on level"""
        for (min_level, max_level), rank in self.rank_mappings.items():
            if min_level <= level <= max_level:
                return rank
        return 'Monarch'  # Default for very high levels
    
    def calculate_exp_gain(self, action_type: str, enemy_rank: str = None, difficulty: str = "normal") -> int:
        """Calculate EXP gain based on action type and difficulty"""
        base_exp = {
            'hunt': 25,
            'gate_clear': 100,
            'dungeon_clear': 150,
            'boss_kill': 200,
            'quest_complete': 50,
            'daily_quest': 30,
            'weekly_quest': 100,
            'special_quest': 300
        }
        
        exp = base_exp.get(action_type, 10)
        
        # Scale by enemy rank - Solo Leveling canon only
        if enemy_rank:
            rank_multipliers = {
                'E': 1.0,
                'D': 1.2,
                'C': 1.5,
                'B': 1.8,
                'A': 2.2,
                'S': 2.7,
                'National': 3.5,
                'Monarch': 5.0
            }
            exp *= rank_multipliers.get(enemy_rank, 1.0)
        
        # Scale by difficulty
        difficulty_multipliers = {
            'easy': 0.8,
            'normal': 1.0,
            'hard': 1.3,
            'nightmare': 1.6,
            'hell': 2.0
        }
        exp *= difficulty_multipliers.get(difficulty, 1.0)
        
        return int(exp)

# Global instance
leveling_system = LevelingSystem()

def load_hunters_data():
    """Load hunter data from JSON file"""
    try:
        with open('hunters_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_hunters_data(data):
    """Save hunter data to JSON file"""
    with open('hunters_data.json', 'w') as f:
        json.dump(data, f, indent=4)

async def update_user_rank_role(member: discord.Member, new_level: int):
    """Update user's rank role based on their new level"""
    print(f"[DEBUG] Starting role update for {member} (Level {new_level})")
    
    guild = member.guild
    new_rank_name = get_rank_role_name(new_level)
    print(f"[DEBUG] Target rank role: {new_rank_name}")
    
    # Debug: List all guild roles
    print(f"[DEBUG] Guild roles available: {[role.name for role in guild.roles]}")
    
    new_rank_role = discord.utils.get(guild.roles, name=new_rank_name)
    print(f"[DEBUG] Found existing role: {new_rank_role is not None}")

    # Create role if it doesn't exist
    if new_rank_role is None:
        print(f"[DEBUG] Role '{new_rank_name}' not found, attempting to create...")
        try:
            new_rank_role = await guild.create_role(
                name=new_rank_name,
                reason="Auto-created rank role for leveling system"
            )
            print(f"[DEBUG] ✅ Created new role: {new_rank_name}")
        except discord.Forbidden as e:
            print(f"[ERROR] ❌ Bot lacks permission to create role '{new_rank_name}': {e}")
            return
        except Exception as e:
            print(f"[ERROR] ❗ Error creating role '{new_rank_name}': {e}")
            return

    # Remove all existing rank roles from user
    rank_names = list(RANK_ROLES.values())
    roles_to_remove = [r for r in member.roles if r.name in rank_names]
    print(f"[DEBUG] Removing old roles: {[r.name for r in roles_to_remove]}")

    try:
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove, reason="Rank update")
            print(f"[DEBUG] 🗑️ Removed old rank roles from {member.display_name}")

        # Assign new role
        print(f"[DEBUG] Adding new role: {new_rank_role.name}")
        await member.add_roles(new_rank_role, reason="Rank promotion")
        print(f"[DEBUG] 🎖️ Assigned {new_rank_name} role to {member.display_name}")
        
        # Send DM notification
        try:
            await member.send(f"🎉 Congratulations! You've been promoted to **{new_rank_name}** (Level {new_level})!")
            print(f"[DEBUG] 📧 Sent promotion DM to {member.display_name}")
        except discord.Forbidden:
            print(f"[DEBUG] 📭 Could not DM {member.display_name} about rank promotion")
            
    except discord.Forbidden as e:
        print(f"[ERROR] ❌ Bot lacks permission to manage roles for {member.display_name}: {e}")
    except Exception as e:
        print(f"[ERROR] ❗ Error updating role for {member.display_name}: {e}")
        import traceback
        traceback.print_exc()

async def award_exp(user_id: str, exp_amount: int, bot, action_type: str = "action") -> Dict:
    """Award EXP to a user and handle level ups"""
    hunters_data = load_hunters_data()
    
    if user_id not in hunters_data:
        return {"error": "User not found"}
    
    hunter = hunters_data[user_id]
    
    # Get current stats
    old_level = hunter.get('level', 1)
    old_exp = hunter.get('exp', 0)
    old_rank = hunter.get('rank', 'E')
    
    # Add EXP
    new_total_exp = old_exp + exp_amount
    new_level = leveling_system.get_level_from_exp(new_total_exp)
    new_rank = leveling_system.get_rank_for_level(new_level)
    
    # Update hunter data
    print(f"[DEBUG] Before EXP update - User: {user_id}, Old EXP: {old_exp}, Old Level: {old_level}, Old Rank: {old_rank}")
    hunter['exp'] = new_total_exp
    hunter['level'] = new_level
    hunter['rank'] = new_rank
    print(f"[DEBUG] After EXP update - User: {user_id}, New EXP: {new_total_exp}, New Level: {new_level}, New Rank: {new_rank}")
    
    # Calculate stat bonuses for level up
    levels_gained = new_level - old_level
    if levels_gained > 0:
        # Award stat points for each level gained
        stat_points_per_level = 3
        bonus_stats = levels_gained * stat_points_per_level
        
        # Distribute stats based on current build
        strength_bonus = bonus_stats // 3
        agility_bonus = bonus_stats // 3
        intel_bonus = bonus_stats - strength_bonus - agility_bonus
        
        hunter['strength'] = hunter.get('strength', 10) + strength_bonus
        hunter['agility'] = hunter.get('agility', 10) + agility_bonus
        hunter['intelligence'] = hunter.get('intelligence', 10) + intel_bonus
        
        # Update base stats
        hunter['base_strength'] = hunter.get('base_strength', 10) + strength_bonus
        hunter['base_agility'] = hunter.get('base_agility', 10) + agility_bonus
        hunter['base_intelligence'] = hunter.get('base_intelligence', 10) + intel_bonus
        
        # Increase HP and MP
        hp_gain = levels_gained * 20
        mp_gain = levels_gained * 10
        
        hunter['max_hp'] = hunter.get('max_hp', 100) + hp_gain
        hunter['max_mp'] = hunter.get('max_mp', 50) + mp_gain
        hunter['hp'] = hunter['max_hp']  # Full heal on level up
        hunter['mp'] = hunter['max_mp']  # Full mana on level up
    
    try:
        print(f"[DEBUG] Attempting to save hunters_data.json after EXP award...")
        save_hunters_data(hunters_data)
        print(f"[DEBUG] Successfully saved hunters_data.json. User {user_id} now has EXP: {hunter['exp']}, Level: {hunter['level']}, Rank: {hunter['rank']}")
    except Exception as e:
        print(f"[ERROR] Failed to save hunters_data.json in award_exp: {e}")
        import traceback
        traceback.print_exc()
    
    # Handle rank role updates if level changed
    rank_changed = old_rank != new_rank
    if rank_changed and levels_gained > 0:
        try:
            user = bot.get_user(int(user_id))
            if user:
                # Find the user in all guilds to update roles
                for guild in bot.guilds:
                    member = guild.get_member(int(user_id))
                    if member:
                        await update_user_rank_role(member, new_level)
                        break
        except Exception as e:
            print(f"Error updating rank role: {e}")
    
    return {
        "old_level": old_level,
        "new_level": new_level,
        "old_rank": old_rank,
        "new_rank": new_rank,
        "exp_gained": exp_amount,
        "total_exp": new_total_exp,
        "levels_gained": levels_gained,
        "rank_changed": rank_changed
    }



async def send_level_up_notification(user, level_up_data):
    """Send a private message to user about their level up"""
    try:
        if level_up_data["levels_gained"] > 0:
            embed = discord.Embed(
                title="🎉 LEVEL UP! 🎉",
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="New Level",
                value=f"Level {level_up_data['new_level']} (+" + str(level_up_data['levels_gained']) + ")",
                inline=True
            )
            
            if level_up_data["rank_changed"]:
                embed.add_field(
                    name="Rank Promotion!",
                    value=f"{level_up_data['old_rank']} → **{level_up_data['new_rank']}**",
                    inline=True
                )
            
            embed.add_field(
                name="EXP Gained",
                value=f"+{level_up_data['exp_gained']} EXP",
                inline=True
            )
            
            embed.add_field(
                name="Total EXP",
                value=f"{level_up_data['total_exp']:,} EXP",
                inline=True
            )
            
            embed.add_field(
                name="Bonuses",
                value=f"• +{level_up_data['levels_gained'] * 3} Stat Points\n• +{level_up_data['levels_gained'] * 20} Max HP\n• +{level_up_data['levels_gained'] * 10} Max MP\n• Full HP/MP Restore",
                inline=False
            )
            
            embed.set_footer(text="Keep hunting to grow stronger!")
            
            await user.send(embed=embed)
        else:
            # Just EXP gain notification
            embed = discord.Embed(
                title="⚡ EXP Gained",
                description=f"You gained **{level_up_data['exp_gained']} EXP**!",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Total EXP",
                value=f"{level_up_data['total_exp']:,} EXP",
                inline=True
            )
            embed.add_field(
                name="Current Level",
                value=f"Level {level_up_data['new_level']}",
                inline=True
            )
            
            # Show progress to next level
            current_progress, needed_for_next = leveling_system.get_exp_progress(
                level_up_data['total_exp'], 
                level_up_data['new_level']
            )
            progress_bar = create_progress_bar(current_progress, needed_for_next)
            embed.add_field(
                name="Next Level Progress",
                value=f"{progress_bar}\n{current_progress:,}/{needed_for_next:,} EXP",
                inline=False
            )
            
            await user.send(embed=embed)
            
    except discord.Forbidden:
        # User has DMs disabled
        print(f"Cannot send DM to user {user.id} - DMs disabled")
    except Exception as e:
        print(f"Error sending level up notification: {e}")

def create_progress_bar(current: int, maximum: int, length: int = 10) -> str:
    """Create a visual progress bar"""
    if maximum == 0:
        return "█" * length
    
    filled = int((current / maximum) * length)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"

