import discord
from discord.ext import commands
import json
import random
import asyncio
import time
from datetime import datetime, timedelta

def load_hunters_data():
    """Loads hunter data from a JSON file."""
    try:
        with open('hunters_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print("Error: hunters_data.json is empty or malformed. Returning empty dict.")
        return {}

def save_hunters_data(data):
    """Saves hunter data to a JSON file."""
    with open('hunters_data.json', 'w') as f:
        json.dump(data, f, indent=4)

def get_user_theme_colors(user_id):
    """Get user-specific theme colors."""
    return discord.Color.blue()

def get_info_embed(title, description, color):
    """Generates a standard info embed."""
    embed = discord.Embed(title=title, description=description, color=color)
    return embed

def get_error_embed(title, description):
    """Generates a standard error embed."""
    return discord.Embed(title=title, description=description, color=discord.Color.red())

def award_exp(hunter, exp_gained):
    """Awards experience to a hunter."""
    hunter['exp'] = hunter.get('exp', 0) + exp_gained

def load_monster_data():
    """Load monster data from JSON file"""
    try:
        with open('data/monsters.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback monsters if file doesn't exist
        return {
            "goblins": [
                {
                    "name": "Goblin Scout",
                    "hp": 50, "attack": 15, "defense": 5,
                    "exp_reward": 25, "gold_reward": 10,
                    "image_url": "https://static.wikia.nocookie.net/solo-leveling/images/3/3e/Goblin_Scout.png"
                }
            ],
            "orcs": [
                {
                    "name": "Orc Warrior", 
                    "hp": 120, "attack": 25, "defense": 10,
                    "exp_reward": 60, "gold_reward": 25,
                    "image_url": "https://static.wikia.nocookie.net/solo-leveling/images/5/5a/Orc_Warrior.png"
                }
            ],
            "wolves": [
                {
                    "name": "Shadow Wolf",
                    "hp": 80, "attack": 20, "defense": 8,
                    "exp_reward": 40, "gold_reward": 15,
                    "image_url": "https://static.wikia.nocookie.net/solo-leveling/images/7/7b/Shadow_Wolf.png"
                }
            ]
        }

def select_random_monster(hunter_rank):
    """Select a random monster based on hunter rank"""
    monsters_data = load_monster_data()
    
    # Rank-based monster selection with progressive access
    if hunter_rank in ["E Rank", "F Rank"]:
        available_monsters = monsters_data.get("goblins", [])
    elif hunter_rank == "D Rank":
        available_monsters = monsters_data.get("goblins", []) + monsters_data.get("wolves", [])
    elif hunter_rank == "C Rank":
        available_monsters = (monsters_data.get("goblins", []) + 
                            monsters_data.get("wolves", []) + 
                            monsters_data.get("orcs", []))
    elif hunter_rank == "B Rank":
        available_monsters = (monsters_data.get("wolves", []) + 
                            monsters_data.get("orcs", []) + 
                            monsters_data.get("spiders", []) + 
                            monsters_data.get("undead", []))
    elif hunter_rank == "A Rank":
        available_monsters = (monsters_data.get("orcs", []) + 
                            monsters_data.get("spiders", []) + 
                            monsters_data.get("undead", []) + 
                            monsters_data.get("elementals", []))
    else:  # S Rank and National Level
        # Access to all monster types including demons
        all_monsters = []
        for monster_type in monsters_data.values():
            all_monsters.extend(monster_type)
        available_monsters = all_monsters
    
    if not available_monsters:
        # Fallback monster
        return {
            "name": "Wild Slime",
            "hp": 30, "attack": 8, "defense": 2,
            "exp_reward": 20, "gold_reward": 5,
            "image_url": "https://static.wikia.nocookie.net/solo-leveling/images/2/2a/Slime.png"
        }
    
    return random.choice(available_monsters)

class DungeonCombatView(discord.ui.View):
    def __init__(self, bot_ref, hunter_id, monster_data, initial_combat_log):
        super().__init__(timeout=180)
        self.bot = bot_ref
        self.hunter_id = hunter_id
        self.monster_data = monster_data
        self.combat_log = [initial_combat_log]
        self.message = None

    async def on_timeout(self):
        hunters_data = load_hunters_data()
        hunter = hunters_data.get(self.hunter_id)
        if hunter and hunter.get('dungeon_battle'):
            del hunter['dungeon_battle']
            save_hunters_data(hunters_data)
        
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(content="Combat timed out due to inactivity.", view=self)
            except (discord.NotFound, discord.Forbidden):
                pass
        self.stop()

    def get_combat_embed(self):
        hunters_data = load_hunters_data()
        hunter = hunters_data.get(self.hunter_id)
        if not hunter or not hunter.get('dungeon_battle'):
            return get_error_embed("Combat Ended", "This combat session is no longer active.")

        dungeon_battle = hunter['dungeon_battle']

        # HP Bar for Monster
        monster_hp_percentage = (dungeon_battle['current_monster_hp'] / self.monster_data['hp']) * 100
        monster_hp_bar = "█" * int(monster_hp_percentage / 10) + "░" * (10 - int(monster_hp_percentage / 10))
        
        # HP Bar for Hunter
        hunter_hp_percentage = (hunter['hp'] / hunter.get('max_hp', 100)) * 100
        hunter_hp_bar = "█" * int(hunter_hp_percentage / 10) + "░" * (10 - int(hunter_hp_percentage / 10))

        embed = get_info_embed(
            f"⚔️ Hunt: {self.monster_data['name']} ⚔️",
            f"**{self.monster_data['name']} HP:** {monster_hp_bar} {dungeon_battle['current_monster_hp']}/{self.monster_data['hp']}\n"
            f"**Your HP:** {hunter_hp_bar} {hunter['hp']}/{hunter.get('max_hp', 100)}",
            get_user_theme_colors(self.hunter_id)
        )
        
        if self.monster_data.get('image_url'):
            embed.set_thumbnail(url=self.monster_data['image_url'])

        if self.combat_log:
            embed.add_field(name="Combat Log", value="\n".join(self.combat_log[-3:]), inline=False)

        return embed

    async def update_message(self):
        if self.message:
            try:
                await self.message.edit(embed=self.get_combat_embed(), view=self)
            except (discord.NotFound, discord.Forbidden):
                self.stop()
            except Exception as e:
                print(f"ERROR: Failed to update combat message for {self.hunter_id}: {e}")
                self.stop()

    @discord.ui.button(label="⚔️ Attack", style=discord.ButtonStyle.primary, custom_id="dungeon_attack")
    async def attack_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.hunter_id:
            await interaction.response.send_message("This battle is not yours to control!", ephemeral=True)
            return

        hunters_data = load_hunters_data()
        hunter = hunters_data.get(self.hunter_id)

        if not hunter or not hunter.get('dungeon_battle'):
            await interaction.response.edit_message(embed=get_error_embed("Combat Ended", "This combat session is no longer active."), view=None)
            self.stop()
            return

        if hunter['hp'] <= 0:
            await interaction.response.send_message("You are defeated and cannot attack!", ephemeral=True)
            hunter['hp'] = hunter.get('max_hp', 100)
            del hunter['dungeon_battle']
            save_hunters_data(hunters_data)
            for item in self.children: 
                item.disabled = True
            await self.message.edit(view=self)
            self.stop()
            return
            
        dungeon_battle = hunter['dungeon_battle']

        # Hunter attacks monster
        hunter_damage_dealt = max(1, hunter['attack'] - self.monster_data['defense'])
        dungeon_battle['current_monster_hp'] -= hunter_damage_dealt
        dungeon_battle['current_monster_hp'] = max(0, dungeon_battle['current_monster_hp'])
        self.combat_log.append(f"You attacked the {self.monster_data['name']} for {hunter_damage_dealt} damage!")

        if dungeon_battle['current_monster_hp'] <= 0:
            # Monster defeated
            exp_gained = self.monster_data['exp_reward']
            gold_gained = self.monster_data['gold_reward']
            
            # Check for weekend double EXP
            event_cog = self.bot.get_cog("EventManagement")
            if event_cog and hasattr(event_cog, 'is_weekend') and event_cog.is_weekend():
                exp_gained = int(exp_gained * event_cog.get_exp_multiplier())

            award_exp(hunter, exp_gained)
            hunter['gold'] = hunter.get('gold', 0) + gold_gained
            hunter['hp'] = hunter.get('max_hp', 100)
            
            self.combat_log.append(f"🎉 You defeated the {self.monster_data['name']}!")
            self.combat_log.append(f"You gained {exp_gained} EXP and {gold_gained} gold!")
            
            del hunter['dungeon_battle']
            save_hunters_data(hunters_data)

            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(embed=self.get_combat_embed(), view=self)
            self.stop()
            return
        
        # Monster retaliates
        monster_damage_dealt = max(1, self.monster_data['attack'] - hunter['defense'])
        hunter['hp'] -= monster_damage_dealt
        hunter['hp'] = max(0, hunter['hp'])
        self.combat_log.append(f"The {self.monster_data['name']} retaliated, dealing {monster_damage_dealt} damage!")

        if hunter['hp'] <= 0:
            self.combat_log.append("💀 You were defeated by the monster!")
            del hunter['dungeon_battle']
            hunter['hp'] = hunter.get('max_hp', 100)
            save_hunters_data(hunters_data)

            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(embed=self.get_combat_embed(), view=self)
            await interaction.followup.send(f"{interaction.user.mention}, you have been defeated! You automatically recovered and can start a new hunt.")
            self.stop()
            return

        hunter['dungeon_battle'] = dungeon_battle
        save_hunters_data(hunters_data)
        
        await interaction.response.edit_message(embed=self.get_combat_embed(), view=self)

    @discord.ui.button(label="🏃 Flee", style=discord.ButtonStyle.danger, custom_id="dungeon_flee")
    async def flee_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.hunter_id:
            await interaction.response.send_message("This battle is not yours to control!", ephemeral=True)
            return

        hunters_data = load_hunters_data()
        hunter = hunters_data.get(self.hunter_id)

        if not hunter or not hunter.get('dungeon_battle'):
            await interaction.response.edit_message(embed=get_error_embed("Combat Ended", "This combat session is no longer active."), view=None)
            self.stop()
            return
        
        # Fleeing penalty
        flee_damage = random.randint(5, 20)
        hunter['hp'] -= flee_damage
        hunter['hp'] = max(0, hunter['hp'])

        self.combat_log.append(f"You attempted to flee from the {self.monster_data['name']}!")
        self.combat_log.append(f"You successfully escaped but took {flee_damage} damage.")

        if hunter['hp'] <= 0:
            self.combat_log.append("💀 You were defeated while trying to flee! You automatically recovered.")
            hunter['hp'] = hunter.get('max_hp', 100)
            del hunter['dungeon_battle']
            save_hunters_data(hunters_data)
            
            for item in self.children: 
                item.disabled = True
            await interaction.response.edit_message(embed=self.get_combat_embed(), view=self)
            await interaction.followup.send(f"{interaction.user.mention}, you have been defeated while fleeing! You can start a new hunt.")
            self.stop()
            return
        
        del hunter['dungeon_battle']
        save_hunters_data(hunters_data)

        self.combat_log.append("You successfully fled the battle.")
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(embed=self.get_combat_embed(), view=self)
        self.stop()

class DungeonManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.COOLDOWN_SECONDS = 30
        self.HUNT_COOLDOWNS = {}

    @commands.command(name="quick_hunt")
    async def quick_hunt_command(self, ctx):
        user_id = str(ctx.author.id)
        hunters_data = load_hunters_data()
        hunter = hunters_data.get(user_id)

        if not hunter:
            await ctx.send("You are not registered as a hunter! Use `.start` to begin your journey.")
            return

        # Cooldown check
        if user_id in self.HUNT_COOLDOWNS:
            remaining_time = self.HUNT_COOLDOWNS[user_id] - time.time()
            if remaining_time > 0:
                await ctx.send(f"You are on cooldown! Please wait {remaining_time:.1f} seconds before hunting again.")
                return

        # Check if already in a dungeon battle
        if hunter.get('dungeon_battle'):
            if hunter['dungeon_battle'].get('message_id') and hunter['dungeon_battle'].get('channel_id'):
                try:
                    channel = self.bot.get_channel(hunter['dungeon_battle']['channel_id'])
                    if channel:
                        message = await channel.fetch_message(hunter['dungeon_battle']['message_id'])
                        await ctx.send(f"You are already engaged in a hunt! Continue your fight here: {message.jump_url}")
                        return
                except (discord.NotFound, discord.Forbidden):
                    pass
            
            del hunter['dungeon_battle']
            save_hunters_data(hunters_data)
            await ctx.send("Your previous hunt state was invalid and has been cleared. Please try `.hunt` again.")
            return
        
        # Auto-heal if defeated
        if hunter['hp'] <= 0:
            hunter['hp'] = hunter.get('max_hp', 100)
            save_hunters_data(hunters_data)

        # Select a random monster for the hunt
        monster_data = select_random_monster(hunter.get('rank', 'E Rank'))
        
        # Set cooldown
        self.HUNT_COOLDOWNS[user_id] = time.time() + self.COOLDOWN_SECONDS

        initial_log = f"A wild {monster_data['name']} appeared!"
        combat_view = DungeonCombatView(self.bot, user_id, monster_data, initial_log)

        try:
            message = await ctx.send(embed=combat_view.get_combat_embed(), view=combat_view)
            combat_view.message = message
            
            hunter['dungeon_battle'] = {
                "current_monster_hp": monster_data['hp'],
                "last_attack_time": time.time(),
                "message_id": message.id,
                "channel_id": ctx.channel.id
            }
            hunters_data[user_id] = hunter
            save_hunters_data(hunters_data)

        except discord.Forbidden:
            await ctx.send("I don't have permissions to send messages with buttons in this channel. Please check my permissions.")
            return
        except Exception as e:
            await ctx.send(f"An error occurred while starting the hunt: {e}")
            print(f"Error starting hunt for {user_id}: {e}")
            return

    @commands.command(name="button_hunt_info")
    async def button_hunt_info(self, ctx):
        """Information about the new button-based hunting system"""
        embed = discord.Embed(
            title="🎮 Enhanced Combat System",
            description="Experience interactive button-based combat with the new `.quick_hunt` command!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="New Features",
            value="• Interactive Attack & Flee buttons\n• Real-time HP tracking\n• Progressive monster encounters\n• Enhanced visual combat log",
            inline=False
        )
        embed.add_field(
            name="Commands",
            value="• `.quick_hunt` - Start button-based combat\n• Use the `.hunt` command for the traditional system",
            inline=False
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(DungeonManagement(bot))