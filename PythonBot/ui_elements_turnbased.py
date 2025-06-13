import discord
from discord.ext import commands
import json
import random
import asyncio
from datetime import datetime
from utils.boss_dialogue import dialogue_manager

class TurnBasedCombatView(discord.ui.View):
    """Turn-based combat view with authentic Solo Leveling boss conversations"""
    
    def __init__(self, bot, user_id, boss_data, combat_channel):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.boss_data = boss_data
        self.combat_channel = combat_channel
        self.boss_id = boss_data['id']
        
        # Combat state
        self.player_hp = 100
        self.player_max_hp = 100
        self.boss_hp = boss_data['hp']
        self.boss_max_hp = boss_data['hp']
        self.turn_count = 0
        self.last_action = None
        self.combat_log = []
        
        # Load player data
        self.hunter_data = self.load_hunter_data()
        if self.hunter_data:
            self.player_hp = self.hunter_data.get('hp', 100)
            self.player_max_hp = self.hunter_data.get('max_hp', 100)
        
        # Combat started flag
        self.combat_started = False
        
    def load_hunter_data(self):
        """Load hunter data"""
        try:
            with open('hunters_data.json', 'r') as f:
                data = json.load(f)
                return data.get(str(self.user_id), {})
        except FileNotFoundError:
            return {}
    
    def save_hunter_data(self):
        """Save hunter data"""
        try:
            with open('hunters_data.json', 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {}
        
        if str(self.user_id) in data:
            data[str(self.user_id)]['hp'] = self.player_hp
            
            try:
                with open('hunters_data.json', 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                print(f"Error saving hunter data: {e}")
    
    def create_combat_embed(self, dialogue_text="", action_result=""):
        """Create combat status embed with dialogue"""
        embed = discord.Embed(
            title=f"⚔️ Battle: {self.boss_data['name']}",
            color=discord.Color.red() if self.boss_hp <= self.boss_max_hp * 0.3 else discord.Color.orange()
        )
        
        # Boss health bar
        boss_hp_percent = (self.boss_hp / self.boss_max_hp) * 100
        boss_bar = self.create_health_bar(self.boss_hp, self.boss_max_hp)
        
        embed.add_field(
            name=f"🏴‍☠️ {self.boss_data['name']}",
            value=f"{boss_bar}\n**HP:** {self.boss_hp}/{self.boss_max_hp} ({boss_hp_percent:.1f}%)",
            inline=False
        )
        
        # Player health bar
        player_hp_percent = (self.player_hp / self.player_max_hp) * 100
        player_bar = self.create_health_bar(self.player_hp, self.player_max_hp)
        
        embed.add_field(
            name="🛡️ Hunter",
            value=f"{player_bar}\n**HP:** {self.player_hp}/{self.player_max_hp} ({player_hp_percent:.1f}%)",
            inline=False
        )
        
        # Dialogue section
        if dialogue_text:
            embed.add_field(
                name=f"💬 {self.boss_data['name']} speaks:",
                value=f"*\"{dialogue_text}\"*",
                inline=False
            )
        
        # Action result
        if action_result:
            embed.add_field(
                name="⚡ Combat Log",
                value=action_result,
                inline=False
            )
        
        # Turn counter
        embed.set_footer(text=f"Turn {self.turn_count} • Use buttons to take actions")
        
        return embed
    
    def create_health_bar(self, current, maximum, length=10):
        """Create visual health bar"""
        if maximum == 0:
            return "░" * length
        
        filled = int((current / maximum) * length)
        empty = length - filled
        
        bar = "█" * filled + "░" * empty
        return f"[{bar}]"
    
    async def start_combat(self):
        """Initialize combat with intro dialogue"""
        intro_dialogue = dialogue_manager.get_encounter_intro(self.boss_id)
        start_dialogue = dialogue_manager.get_combat_start(self.boss_id)
        
        # Send intro message
        intro_embed = discord.Embed(
            title=f"🌟 {self.boss_data['name']} Appears!",
            description=self.boss_data.get('description', 'A powerful enemy stands before you.'),
            color=discord.Color.dark_red()
        )
        
        intro_embed.add_field(
            name=f"💬 {self.boss_data['name']}:",
            value=f"*\"{intro_dialogue}\"*",
            inline=False
        )
        
        await self.combat_channel.send(embed=intro_embed)
        await asyncio.sleep(2)
        
        # Send combat start
        start_embed = discord.Embed(
            title="⚔️ Combat Begins!",
            description=f"*\"{start_dialogue}\"*",
            color=discord.Color.gold()
        )
        
        await self.combat_channel.send(embed=start_embed)
        await asyncio.sleep(1)
        
        # Start main combat interface
        self.combat_started = True
        self.turn_count = 1
        
        combat_embed = self.create_combat_embed("Choose your action wisely, hunter...")
        message = await self.combat_channel.send(embed=combat_embed, view=self)
        self.message = message
    
    @discord.ui.button(label="Attack", style=discord.ButtonStyle.danger, emoji="⚔️", row=0)
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle attack action"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Only the challenger can control this battle!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Calculate damage
        base_damage = random.randint(15, 25)
        if self.hunter_data:
            attack_stat = self.hunter_data.get('attack', 20)
            base_damage = random.randint(attack_stat - 5, attack_stat + 10)
        
        # Critical hit chance
        critical = random.random() < 0.15
        if critical:
            base_damage = int(base_damage * 1.5)
        
        self.boss_hp = max(0, self.boss_hp - base_damage)
        
        # Get boss response to attack
        boss_response = dialogue_manager.get_player_action_response(self.boss_id, 'attack')
        
        # Create action result
        crit_text = " **CRITICAL HIT!**" if critical else ""
        action_result = f"🗡️ You strike for **{base_damage}** damage!{crit_text}"
        
        # Check if boss is defeated
        if self.boss_hp <= 0:
            await self.handle_boss_defeat(interaction, boss_response)
            return
        
        # Boss counter-attack
        await self.process_boss_turn(interaction, boss_response, action_result)
    
    @discord.ui.button(label="Defend", style=discord.ButtonStyle.secondary, emoji="🛡️", row=0)
    async def defend_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle defend action"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Only the challenger can control this battle!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Get boss response to defense
        boss_response = dialogue_manager.get_player_action_response(self.boss_id, 'defend')
        action_result = "🛡️ You take a defensive stance, reducing incoming damage by 50%!"
        
        # Boss attack with reduced damage
        await self.process_boss_turn(interaction, boss_response, action_result, damage_reduction=0.5)
    
    @discord.ui.button(label="Special Ability", style=discord.ButtonStyle.primary, emoji="✨", row=0)
    async def special_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle special ability"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Only the challenger can control this battle!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Special ability effects
        heal_amount = random.randint(20, 35)
        self.player_hp = min(self.player_max_hp, self.player_hp + heal_amount)
        
        damage_amount = random.randint(20, 30)
        self.boss_hp = max(0, self.boss_hp - damage_amount)
        
        boss_response = "Your power... it's extraordinary!"
        action_result = f"✨ **Shadow Extraction!** You heal for **{heal_amount}** HP and deal **{damage_amount}** shadow damage!"
        
        # Check if boss is defeated
        if self.boss_hp <= 0:
            await self.handle_boss_defeat(interaction, boss_response)
            return
        
        # Boss counter-attack
        await self.process_boss_turn(interaction, boss_response, action_result)
    
    @discord.ui.button(label="Flee", style=discord.ButtonStyle.secondary, emoji="💨", row=1)
    async def flee_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle flee action"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Only the challenger can control this battle!", ephemeral=True)
            return
        
        # 30% chance to flee successfully
        if random.random() < 0.7:
            boss_response = dialogue_manager.get_player_action_response(self.boss_id, 'flee')
            
            flee_embed = discord.Embed(
                title="💨 Tactical Retreat",
                description="You attempt to flee but the boss blocks your escape!",
                color=discord.Color.orange()
            )
            
            flee_embed.add_field(
                name=f"💬 {self.boss_data['name']}:",
                value=f"*\"{boss_response}\"*",
                inline=False
            )
            
            await interaction.response.edit_message(embed=flee_embed, view=None)
            
            # Boss gets a free attack
            await asyncio.sleep(2)
            await self.process_boss_turn(interaction, "", "You failed to escape!", damage_multiplier=1.2)
        else:
            # Successful flee
            victory_dialogue = dialogue_manager.get_victory_dialogue(self.boss_id, False)
            
            flee_embed = discord.Embed(
                title="💨 Successful Retreat",
                description="You manage to escape from the battle!",
                color=discord.Color.blue()
            )
            
            flee_embed.add_field(
                name=f"💬 {self.boss_data['name']}:",
                value=f"*\"{victory_dialogue}\"*",
                inline=False
            )
            
            self.save_hunter_data()
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            await interaction.response.edit_message(embed=flee_embed, view=self)
    
    async def process_boss_turn(self, interaction, boss_response, action_result, damage_reduction=0, damage_multiplier=1.0):
        """Process boss turn with dialogue and attacks"""
        self.turn_count += 1
        
        # Update combat display with player action
        combat_embed = self.create_combat_embed(boss_response, action_result)
        await interaction.edit_original_response(embed=combat_embed, view=self)
        
        await asyncio.sleep(2)
        
        # Boss attack
        boss_attack_dialogue = dialogue_manager.get_boss_attack_dialogue(self.boss_id)
        
        # Calculate boss damage
        base_boss_damage = random.randint(self.boss_data.get('attack', 30) - 10, self.boss_data.get('attack', 30) + 5)
        base_boss_damage = int(base_boss_damage * damage_multiplier)
        
        # Apply damage reduction
        final_damage = int(base_boss_damage * (1 - damage_reduction))
        self.player_hp = max(0, self.player_hp - final_damage)
        
        boss_action_result = f"💀 {self.boss_data['name']} attacks for **{final_damage}** damage!"
        
        # Check if player is defeated
        if self.player_hp <= 0:
            await self.handle_player_defeat(interaction, boss_attack_dialogue)
            return
        
        # Check for low health dialogue
        boss_hp_percent = (self.boss_hp / self.boss_max_hp) * 100
        if boss_hp_percent <= 25 and random.random() < 0.3:
            boss_response = dialogue_manager.get_low_health_dialogue(self.boss_id)
        else:
            boss_response = boss_attack_dialogue
        
        # Update combat display
        combat_embed = self.create_combat_embed(boss_response, boss_action_result)
        await interaction.edit_original_response(embed=combat_embed, view=self)
    
    async def handle_boss_defeat(self, interaction, boss_response):
        """Handle boss defeat with victory dialogue"""
        victory_dialogue = dialogue_manager.get_victory_dialogue(self.boss_id, True)
        
        # Calculate rewards
        exp_reward = self.boss_data.get('exp_reward', 500)
        gold_reward = self.boss_data.get('gold_reward', 300)
        
        victory_embed = discord.Embed(
            title="🏆 VICTORY!",
            description=f"You have defeated {self.boss_data['name']}!",
            color=discord.Color.gold()
        )
        
        victory_embed.add_field(
            name=f"💬 {self.boss_data['name']}'s final words:",
            value=f"*\"{victory_dialogue}\"*",
            inline=False
        )
        
        victory_embed.add_field(
            name="🎁 Rewards",
            value=f"**EXP:** +{exp_reward}\n**Gold:** +{gold_reward}",
            inline=False
        )
        
        # Update hunter data with rewards
        if self.hunter_data:
            try:
                with open('hunters_data.json', 'r') as f:
                    data = json.load(f)
                
                user_data = data.get(str(self.user_id), {})
                user_data['exp'] = user_data.get('exp', 0) + exp_reward
                user_data['gold'] = user_data.get('gold', 0) + gold_reward
                data[str(self.user_id)] = user_data
                
                with open('hunters_data.json', 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                print(f"Error updating rewards: {e}")
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.edit_original_response(embed=victory_embed, view=self)
        
        # Clean up channel after delay
        await asyncio.sleep(30)
        try:
            await self.combat_channel.delete()
        except:
            pass
    
    async def handle_player_defeat(self, interaction, boss_dialogue):
        """Handle player defeat"""
        defeat_dialogue = dialogue_manager.get_victory_dialogue(self.boss_id, False)
        
        defeat_embed = discord.Embed(
            title="💀 DEFEAT",
            description=f"You have been defeated by {self.boss_data['name']}...",
            color=discord.Color.dark_red()
        )
        
        defeat_embed.add_field(
            name=f"💬 {self.boss_data['name']}:",
            value=f"*\"{defeat_dialogue}\"*",
            inline=False
        )
        
        defeat_embed.add_field(
            name="⚰️ Result",
            value="You have fallen in battle, but you can try again when you're stronger.",
            inline=False
        )
        
        # Reset player HP to 1 to prevent death loop
        self.player_hp = 1
        self.save_hunter_data()
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.edit_original_response(embed=defeat_embed, view=self)
        
        # Clean up channel after delay
        await asyncio.sleep(30)
        try:
            await self.combat_channel.delete()
        except:
            pass
    
    async def on_timeout(self):
        """Handle view timeout"""
        if hasattr(self, 'message'):
            try:
                for item in self.children:
                    item.disabled = True
                
                timeout_embed = discord.Embed(
                    title="⏰ Combat Timeout",
                    description="The battle has timed out due to inactivity.",
                    color=discord.Color.orange()
                )
                
                await self.message.edit(embed=timeout_embed, view=self)
            except:
                pass