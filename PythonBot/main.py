import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv
import asyncio
import time
from datetime import datetime, timedelta
from utils.leveling_system import award_exp, send_level_up_notification, leveling_system
from utils.theme_utils import get_user_theme_colors, get_error_embed, get_info_embed, create_progress_bar
from ui_elements import HelpView, StatusView, CombatView

# Custom JSON encoder to handle Discord objects
class CustomEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, discord.Colour):
            return o.value  # Convert discord.Colour to its integer value
        if isinstance(o, discord.Color):
            return o.value  # Convert discord.Color to its integer value
        return json.JSONEncoder.default(self, o)

# Load environment variables
load_dotenv()

# Bot configuration - Changed prefix from "!" to "."
COMMAND_PREFIX = '.'
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True  # Enable reaction intent for events

# System message configuration
# SYSTEM_CHANNEL_ID = 1381439963656355849  # announcements channel for system messages
COMBAT_CATEGORY_ID = 1382846867418775552  # Category for temporary combat channels
# PRIVATE_EVENT_CATEGORY_ID = 1382846867418775552  # New category for private event channels

# Global variables
active_battles = {}
interactive_battles = {}  # Track interactive button-based battles
rest_cooldowns = {}  # Track rest command cooldowns (1 minute 30 second cooldown)
resting_players = {}  # Track players currently resting (90 second resting period)
mini_boss_events = {}  # Track active mini boss events
mystery_gates = {}  # Track ??? gates based on daily kills
hunt_cooldowns = {}  # Track hunt command cooldowns to prevent spam
last_hunt_completion = {}  # Track last hunt completion time
player_combat_channels = {}  # Track active combat channels for each player
channel_creation_locks = {}  # Track channel creation locks to prevent race conditions
active_event_battles = {}  # Stores event boss encounters with shared combat state

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)

# Load or create hunters data
def load_hunters_data():
    try:
        with open('hunters_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_hunters_data(data):
    """Save hunter data to JSON file using CustomEncoder for Discord objects"""
    try:
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4, cls=CustomEncoder)
    except Exception as e:
        print(f"Error saving hunters_data.json: {e}")
        # Create backup if save fails
        try:
            with open('hunters_data_backup.json', 'w') as backup_f:
                json.dump(data, backup_f, indent=4, cls=CustomEncoder)
            print("Data saved to backup file instead")
        except Exception as backup_e:
            print(f"Failed to create backup: {backup_e}")

def load_monster_data():
    """Load monster data from JSON file"""
    try:
        with open('data/monsters.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("[ERROR] data/monsters.json not found")
        return {}
    except json.JSONDecodeError:
        print("[ERROR] Invalid JSON in monsters.json")
        return {}

def select_random_monster(hunter_rank):
    """Select a random monster based on hunter rank"""
    import random
    
    monster_data = load_monster_data()
    monsters = monster_data.get('monsters', {})
    
    available_monsters = monsters.get(hunter_rank, [])
    if not available_monsters:
        # Fallback to E-Rank if rank not found
        available_monsters = monsters.get('E-Rank', [])
    
    if available_monsters:
        monster = random.choice(available_monsters).copy()
        monster['max_hp'] = monster['hp']
        monster['current_hp'] = monster['hp']
        return monster
    
    # Emergency fallback
    return {
        "name": "Wild Beast",
        "level": 1,
        "hp": 50,
        "max_hp": 50,
        "current_hp": 50,
        "attack": 10,
        "defense": 5,
        "exp_reward": 30,
        "gold_reward": 20,
        "abilities": ["Bite"],
        "rarity": "common"
    }

async def process_interactive_combat(ctx, user_id, hunter, monster, combat_view):
    """Process interactive combat turn"""
    import random
    import time
    
    hunters_data = load_hunters_data()
    colors = get_user_theme_colors(user_id)
    turn_info = ""
    combat_ended = False
    
    # Process player action
    if combat_view.player_action == "attack":
        # Calculate player damage using strength as attack stat
        base_attack = hunter.get('strength', 10)
        player_damage = max(1, base_attack + random.randint(-5, 5) - monster.get('defense', 0))
        monster['current_hp'] = max(0, monster['current_hp'] - player_damage)
        turn_info += f"⚔️ You deal {player_damage} damage!\n"
        
        if monster['current_hp'] <= 0:
            # Monster defeated
            exp_gained = monster['exp_reward']
            gold_gained = monster['gold_reward']
            
            # Award experience and update hunter
            level_data = await award_exp(user_id, exp_gained, bot)
            hunters_data = load_hunters_data()
            hunter = hunters_data[user_id]
            
            # Award gold
            hunter['gold'] = hunter.get('gold', 0) + gold_gained
            save_hunters_data(hunters_data)
            
            # Update daily kills for mystery gate access
            update_daily_kills(hunter)
            
            # Update quest progress for killing monsters
            try:
                from daily_quest_system import update_quest_progress
                update_quest_progress(hunter, "kill_monsters", 1)
                save_hunters_data(hunters_data)
            except Exception as e:
                print(f"Error updating quest progress: {e}")
            
            # Create victory summary embed
            colors = get_user_theme_colors(user_id)
            victory_embed = discord.Embed(
                title=f"🎉 {hunter.get('name', 'Hunter')} Defeated the {monster['name']}!",
                description=f"**Victory!** You have successfully defeated the {monster['name']}.",
                color=discord.Color(colors.get('success', colors['primary']))
            )
            
            victory_embed.add_field(name="💰 Gold Gained", value=f"{gold_gained:,} Gold", inline=True)
            victory_embed.add_field(name="🌟 EXP Gained", value=f"{exp_gained:,} EXP", inline=True)
            
            if level_data['levels_gained'] > 0:
                level_message = f"Level: {level_data['old_level']} → {level_data['new_level']}"
                if level_data['rank_changed']:
                    level_message += f"\nRank: {level_data['old_rank']} → {level_data['new_rank']}"
                victory_embed.add_field(name="⬆️ Level Up!", value=level_message, inline=False)
            
            victory_embed.add_field(
                name="📊 Current Stats",
                value=f"Level: {hunter.get('level', 1)}\nHP: {hunter.get('hp', 0)}/{hunter.get('max_hp', 100)}\nGold: {hunter.get('gold', 0):,}",
                inline=False
            )
            victory_embed.set_footer(text="Your adventure continues!")
            
            turn_info += f"🎉 **{monster['name']} defeated!**\n"
            turn_info += f"💰 +{gold_gained} gold | ⭐ +{exp_gained} EXP"
            
            # Store victory data for detailed completion message
            combat_view.victory_data = {
                'monster_name': monster['name'],
                'gold_gained': gold_gained,
                'exp_gained': exp_gained,
                'level_up_data': level_data,
                'hunter_stats': {
                    'level': hunter.get('level', 1),
                    'hp': hunter.get('hp', 0),
                    'max_hp': hunter.get('max_hp', 100),
                    'gold': hunter.get('gold', 0)
                }
            }
            
            combat_ended = True
            
    elif combat_view.player_action == "defend":
        turn_info += f"🛡️ You raised your shield to defend!\n"
        
        # Apply defense logic with damage reduction
        base_monster_damage = monster.get('damage', 20)
        defense_multiplier = 0.5  # 50% damage reduction when defending
        final_monster_damage = int(base_monster_damage * defense_multiplier)
        
        turn_info += f"👹 The {monster['name']} attacked you for {final_monster_damage} damage (reduced by defense)!\n"
        
    elif combat_view.player_action == "flee":
        import random
        
        # 60% chance to successfully flee
        if random.random() < 0.6:
            turn_info += f"🏃 You successfully fled the battle and escaped to safety!\n"
            combat_ended = True
        else:
            turn_info += f"❌ You attempted to flee, but the {monster['name']} blocked your path!\n"
            
            # Monster gets a free attack when flee fails
            base_monster_damage = monster.get('damage', 20)
            turn_info += f"👹 The {monster['name']} attacked you for {base_monster_damage} damage!\n"
        
    elif combat_view.player_action == "use_item":
        # Process item usage
        if combat_view.item_used:
            hunters_data = load_hunters_data()
            hunter = hunters_data[user_id]
            
            # Remove item from inventory
            inventory = hunter.get('inventory', [])
            if combat_view.item_used in inventory:
                inventory.remove(combat_view.item_used)
                
                # Apply item effect (health potion example)
                if 'health' in combat_view.item_used.lower():
                    heal_amount = 50
                    old_hp = hunter['hp']
                    hunter['hp'] = min(hunter.get('max_hp', 100), hunter['hp'] + heal_amount)
                    actual_heal = hunter['hp'] - old_hp
                    turn_info += f"💊 Used {combat_view.item_used}! Restored {actual_heal} HP\n"
                
                save_hunters_data(hunters_data)
            else:
                turn_info += f"❌ {combat_view.item_used} not found in inventory!\n"
    
    # Monster's turn (if combat continues and player didn't flee)
    if not combat_ended and combat_view.player_action != "flee":
        monster_damage = max(1, monster.get('attack', 10) + random.randint(-3, 3) - hunter.get('defense', 0))
        
        # Reduce damage if player defended
        if combat_view.player_action == "defend":
            monster_damage = max(1, monster_damage // 2)
        
        hunter['hp'] = max(0, hunter['hp'] - monster_damage)
        turn_info += f"💥 {monster['name']} attacks for {monster_damage} damage!\n"
        
        # Check if player is defeated
        if hunter['hp'] <= 0:
            turn_info += f"💀 **You have been defeated by {monster['name']}!**\n"
            turn_info += f"⚰️ You will respawn in 3 minutes..."
            
            # Set respawn timer
            hunter['death_time'] = time.time()
            hunter['hp'] = 1  # Prevent negative HP
            
            save_hunters_data(hunters_data)
            combat_ended = True
    
    # Update combat embed
    embed = combat_view.create_combat_embed(hunter, monster, turn_info)
    
    if combat_ended:
        combat_view.disable_all_buttons()
        combat_view.combat_ended = True
        
        # Clean up battle tracking
        if user_id in interactive_battles:
            del interactive_battles[user_id]
            
        # Update message with final state
        try:
            await combat_view.message.edit(embed=embed, view=combat_view)
        except discord.HTTPException:
            pass
            
        # Send victory embed only to private combat channel if monster was defeated
        if monster['current_hp'] <= 0 and 'victory_embed' in locals():
            try:
                # Send victory message only to private combat channel
                user_id = str(ctx.author.id)
                if user_id in player_combat_channels:
                    channel_id = player_combat_channels[user_id]
                    if isinstance(channel_id, str):
                        channel_id = int(channel_id)
                    private_channel = bot.get_channel(channel_id)
                    if private_channel:
                        await private_channel.send(embed=victory_embed)
                # No fallback to original channel - victory only in private arena
            except Exception as e:
                print(f"[ERROR] Failed to send victory message to private channel: {e}")
            
        return True
    else:
        # Reset for next turn
        combat_view.player_action = None
        combat_view.player_turn_active = True
        
        # Update message and continue combat
        try:
            await combat_view.message.edit(embed=embed, view=combat_view)
        except discord.HTTPException:
            pass
            
        return False

# Load or create combat channels data
def load_combat_channels():
    try:
        with open('data/combat_channels.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_combat_channels():
    os.makedirs('data', exist_ok=True)
    with open('data/combat_channels.json', 'w') as f:
        json.dump(player_combat_channels, f, indent=4)

async def create_private_combat_channel(ctx):
    """Create a private temporary combat channel for a player"""
    try:
        user = ctx.author
        guild = ctx.guild
        COMBAT_CATEGORY_ID = 1382846867418775552
        
        # Try to get category with fallback
        category = discord.utils.get(guild.categories, id=COMBAT_CATEGORY_ID)
        
        if category is None:
            try:
                fetched_channel = await bot.fetch_channel(COMBAT_CATEGORY_ID)
                if isinstance(fetched_channel, discord.CategoryChannel):
                    category = fetched_channel
            except Exception as e:
                print(f"[ERROR] Failed to fetch category: {e}")
                return None
        
        if category is None:
            print(f"[ERROR] Category {COMBAT_CATEGORY_ID} not found")
            return None
        
        # Create permission overwrites
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        
        # Add moderator permissions if needed
        for role in guild.roles:
            if any(perm_name in role.name.lower() for perm_name in ['mod', 'admin', 'staff']):
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        
        # Clean username for channel name with possessive format
        username = user.display_name
        # Remove problematic characters but keep spaces for natural naming
        import re
        username = re.sub(r'[^\w\s\-]', '', username)
        if len(username) > 20:
            username = username[:20]
        channel_name = f"{username}'s Private adventure"
        
        print(f"[DEBUG] Creating channel for {user.display_name} in category: {category.name if category else 'None'}")
        
        # Create the combat channel
        combat_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Private combat arena for {user.display_name}.",
            reason=f"Created by bot for private combat session."
        )
        
        # Store channel for potential cleanup
        if not hasattr(bot, 'temp_combat_channels'):
            bot.temp_combat_channels = set()
        bot.temp_combat_channels.add(combat_channel.id)
        
        return combat_channel
        
    except discord.Forbidden:
        print(f"[ERROR] Missing permissions to create the channel.")
        try:
            await user.send("❌ I don't have permission to create your private combat channel. Please notify a server admin.")
        except:
            pass
        return None
    except Exception as e:
        print(f"[ERROR] Failed to create private combat channel: {e}")
        return None

async def send_system_message(embed, channel_override=None, user_id=None):
    """Send system messages to designated channel, or private combat channel if user_id provided"""
    # If user_id provided, try to send to their private combat channel
    if user_id:
        user_key = str(user_id)
        if user_key in player_combat_channels:
            channel_id = player_combat_channels[user_key]
            if isinstance(channel_id, str):
                channel_id = int(channel_id)
            private_channel = bot.get_channel(channel_id)
            if private_channel:
                await private_channel.send(embed=embed)
                return
    
    # Fallback to system channel or override
    target_channel = bot.get_channel(SYSTEM_CHANNEL_ID)
    if target_channel and channel_override is None:
        await target_channel.send(embed=embed)
    elif channel_override:
        await channel_override.send(embed=embed)

async def create_combat_channel(user):
    """Create a persistent private combat channel for a player"""
    guild = user.guild
    user_key = str(user.id)
    
    # Define the combat category ID
    COMBAT_CATEGORY_ID = 1382846867418775552
    
    # Prevent race conditions with async lock
    if user_key in channel_creation_locks:
        # Wait for existing channel creation to complete
        while user_key in channel_creation_locks:
            await asyncio.sleep(0.1)
        # Check again if channel was created while waiting
        if user_key in player_combat_channels:
            channel_id = player_combat_channels[user_key]
            if isinstance(channel_id, str):
                channel_id = int(channel_id)
            existing_channel = bot.get_channel(channel_id)
            if existing_channel:
                return existing_channel
    
    # Set lock to prevent duplicate creation
    channel_creation_locks[user_key] = True
    
    try:
        # Check if player already has a combat channel
        if user_key in player_combat_channels:
            channel_id = player_combat_channels[user_key]
            
            # Ensure channel_id is an integer
            if isinstance(channel_id, str):
                channel_id = int(channel_id)
                
            existing_channel = bot.get_channel(channel_id)
            
            if existing_channel:
                return existing_channel
            else:
                # Channel was deleted externally, remove from tracking and save
                del player_combat_channels[user_key]
                save_combat_channels()
        
        # Get the combat category
        category = None
        try:
            category_channel = bot.get_channel(COMBAT_CATEGORY_ID)
            if category_channel and isinstance(category_channel, discord.CategoryChannel):
                category = category_channel
            else:
                print(f"Combat category ID {COMBAT_CATEGORY_ID} not found, creating without category")
        except Exception as e:
            print(f"Error getting combat category: {e}")
        
        # Create channel with permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Add moderator permissions if they exist
        for role in guild.roles:
            if any(perm_name in role.name.lower() for perm_name in ['mod', 'admin', 'staff']):
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        # Use username for permanent adventure channel name
        username = user.display_name.lower().replace(' ', '-')
        # Remove special characters and keep alphanumeric and hyphens only
        import re
        username = re.sub(r'[^a-z0-9\-]', '', username)
        # Limit length
        if len(username) > 20:
            username = username[:20]
        channel_name = f"{username}-private-adventure"
        
        combat_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Private adventure channel for {user.display_name}. Persistent channel.",
            reason="Permanent private adventure channel"
        )
        
        # Store the channel for future use
        player_combat_channels[user_key] = combat_channel.id
        save_combat_channels()  # Persist the channel data
        
        # Send welcome message to the combat channel
        welcome_embed = discord.Embed(
            title="🌀 Private Adventure Entrance",
            description=f"Welcome {user.mention}! You have entered your personal adventure space: **{user.display_name}'s Adventure**",
            color=discord.Color.purple()
        )
        welcome_embed.add_field(
            name="Adventure Commands",
            value="Use `.attack`, `.defend`, or `.flee` to battle!\nThis adventure space remains open for future quests.",
            inline=False
        )
        await combat_channel.send("⚔️ Your private adventure has begun. This channel is permanent and tied to your ID.")
        await combat_channel.send(embed=welcome_embed)
        
        return combat_channel
        
    except discord.Forbidden:
        print(f"Failed to create combat channel - missing permissions")
        return None
    except Exception as e:
        print(f"Error creating combat channel: {e}")
        return None
    finally:
        # Always release lock
        if user_key in channel_creation_locks:
            del channel_creation_locks[user_key]

async def send_combat_completion_message(user_id, victory_data=None):
    """Send completion message to combat channel without deletion"""
    user_key = str(user_id)
    if user_key in player_combat_channels:
        channel_id = player_combat_channels[user_key]
        channel = bot.get_channel(channel_id)
        
        if channel:
            try:
                if victory_data:
                    # Create detailed victory screen with rewards
                    from utils.theme_utils import get_user_theme_colors
                    colors = get_user_theme_colors(user_id)
                    
                    final_embed = discord.Embed(
                        title="🎉 Victory Achieved!",
                        description=f"You have successfully defeated the {victory_data.get('monster_name', 'enemy')}!",
                        color=discord.Color(colors.get('success', colors['primary']))
                    )
                    
                    # Add reward information
                    reward_text = ""
                    if victory_data.get('gold_gained', 0) > 0:
                        reward_text += f"💰 **{victory_data['gold_gained']:,} Gold**\n"
                    if victory_data.get('exp_gained', 0) > 0:
                        reward_text += f"⭐ **{victory_data['exp_gained']:,} EXP**\n"
                    
                    if reward_text:
                        final_embed.add_field(
                            name="🏆 Battle Rewards",
                            value=reward_text.strip(),
                            inline=False
                        )
                    
                    # Add level up information if applicable
                    if victory_data.get('level_up_data'):
                        level_data = victory_data['level_up_data']
                        if level_data.get('levels_gained', 0) > 0:
                            level_text = f"Level: {level_data['old_level']} → **{level_data['new_level']}**"
                            if level_data.get('rank_changed'):
                                level_text += f"\nRank: {level_data['old_rank']} → **{level_data['new_rank']}**"
                            
                            final_embed.add_field(
                                name="🆙 Level Progress",
                                value=level_text,
                                inline=False
                            )
                    
                    # Add current stats
                    if victory_data.get('hunter_stats'):
                        stats = victory_data['hunter_stats']
                        stats_text = f"Level: {stats.get('level', 1)}\n"
                        stats_text += f"HP: {stats.get('hp', 0)}/{stats.get('max_hp', 100)}\n"
                        stats_text += f"Gold: {stats.get('gold', 0):,}"
                        
                        final_embed.add_field(
                            name="📊 Current Status",
                            value=stats_text,
                            inline=True
                        )
                    
                    # Add additional information if provided
                    if victory_data.get('additional_info'):
                        final_embed.add_field(
                            name="📋 Additional Details",
                            value=victory_data['additional_info'],
                            inline=False
                        )
                    
                    final_embed.set_footer(text="Your adventure continues! This channel remains open for future battles.")
                    
                else:
                    # Generic completion message for non-victory scenarios
                    final_embed = discord.Embed(
                        title="🏆 Adventure Challenge Complete",
                        description="The battle has ended. Your adventure space remains open for future quests.",
                        color=discord.Color.gold()
                    )
                
                await channel.send(embed=final_embed)
            except Exception as e:
                print(f"Error sending completion message: {e}")

async def send_combat_message(ctx, embed, redirect_message=None):
    """Send combat messages to player's private combat channel"""
    user_id = str(ctx.author.id)
    
    # Check if player already has a combat channel
    if user_id in player_combat_channels:
        channel_id = player_combat_channels[user_id]
        
        # Ensure channel_id is an integer
        if isinstance(channel_id, str):
            channel_id = int(channel_id)
        
        combat_channel = bot.get_channel(channel_id)
        
        if combat_channel:
            await combat_channel.send(embed=embed)
            return combat_channel
        else:
            # Channel was deleted, remove from tracking and save
            del player_combat_channels[user_id]
            save_combat_channels()
    
    # Create new combat channel for the player
    combat_channel = await create_combat_channel(ctx.author)
    
    if combat_channel:
        # Send redirect message in original channel
        redirect_embed = discord.Embed(
            title="🌀 Personal Adventure Opened!",
            description=f"Your private adventure has opened: {combat_channel.mention}!\nOnly you can access this dimensional space.",
            color=discord.Color.purple()
        )
        await ctx.send(embed=redirect_embed)
        
        # Send combat message in private channel
        await combat_channel.send(f"{ctx.author.mention} Welcome to your dimensional adventure!", embed=embed)
        return combat_channel
    else:
        # Fallback to current channel if creation failed
        await ctx.send(embed=embed)
        return ctx.channel

def is_combat_command(ctx, hunter):
    """Check if this is a combat-related command"""
    return any([
        hunter.get('battle'),
        hunter.get('gate_battle'), 
        hunter.get('dungeon_battle'),
        ctx.command.name in ['attack', 'defend', 'flee', 'hunt']
    ])

def get_daily_kill_requirement(hunter_level):
    """Calculate daily kill requirement for mystery gates"""
    base_requirement = 20
    level_scaling = hunter_level * 2
    return base_requirement + level_scaling

def check_mystery_gate_access(hunter):
    """Check if hunter has access to mystery gates based on daily kills"""
    today = datetime.now().strftime("%Y-%m-%d")
    daily_kills = hunter.get('daily_kills', {}).get(today, 0)
    required_kills = get_daily_kill_requirement(hunter['level'])
    return daily_kills >= required_kills

def update_daily_kills(hunter, kills=1):
    """Update daily kill count for mystery gate access"""
    today = datetime.now().strftime("%Y-%m-%d")
    if 'daily_kills' not in hunter:
        hunter['daily_kills'] = {}
    
    # Reset if new day
    if today not in hunter['daily_kills']:
        hunter['daily_kills'] = {today: 0}
    
    hunter['daily_kills'][today] += kills

def check_for_active_doorway(user_id):
    """Check if user has an active doorway exploration"""
    gates_cog = bot.get_cog('Gates')
    if gates_cog and hasattr(gates_cog, 'active_explorations'):
        if user_id in gates_cog.active_explorations:
            doorway_name = gates_cog.active_explorations[user_id].get('gate_name', 'Unknown Doorway')
            return True, doorway_name
    return False, None

async def load_cogs():
    """Load all cog files from the cogs directory"""
    try:
        # Create cogs directory if it doesn't exist
        if not os.path.exists('./cogs'):
            os.makedirs('./cogs')
            
        # List of expected cogs, replaced global_events and starting_event with event_management
        cog_files = ['gates', 'inventory', 'shop', 'pvp_system', 'dungeon_raids', 'themes', 'daily_quests', 'weekly_quests', 'special_quests', 'training', 'event_management', 'sololeveling_info', 'narrative_encounters', 'dungeon_management']
        
        for cog_name in cog_files:
            try:
                await bot.load_extension(f'cogs.{cog_name}')
                print(f'Loaded cog: {cog_name}')
            except Exception as e:
                print(f'Failed to load cog {cog_name}: {e}')
    except Exception as e:
        print(f'Error loading cogs: {e}')

def reset_stuck_players():
    """Reset all players' battle and exploration states"""
    try:
        hunters_data = load_hunters_data()
        reset_count = 0
        
        for user_id, hunter in hunters_data.items():
            # Reset all battle states
            if hunter.get('battle'):
                hunter['battle'] = None
                reset_count += 1
            
            if hunter.get('gate_battle'):
                hunter['gate_battle'] = None
                reset_count += 1
            
            if hunter.get('dungeon_battle'):
                hunter['dungeon_battle'] = None
                reset_count += 1
            
            # Ensure HP is not 0 to prevent stuck states
            if hunter.get('hp', 100) <= 0:
                hunter['hp'] = hunter.get('max_hp', 100)
                reset_count += 1
            
            # Add defense stat to existing players if missing
            if 'defense' not in hunter:
                hunter['defense'] = 5  # Base defense
                reset_count += 1
        
        if reset_count > 0:
            save_hunters_data(hunters_data)
            print(f"Reset {reset_count} stuck player states")
                
    except Exception as e:
        print(f"Error resetting stuck players: {e}")

async def cleanup_duplicate_channels():
    """Clean up any duplicate adventure channels that may exist"""
    try:
        for guild in bot.guilds:
            adventure_channels = []
            
            # Find all channels that end with "-adventure"
            for channel in guild.text_channels:
                if channel.name.endswith('-adventure'):
                    adventure_channels.append(channel)
            
            if len(adventure_channels) <= 1:
                continue
                
            # Group channels by user (based on channel name pattern)
            user_channels = {}
            for channel in adventure_channels:
                # Extract username from channel name (remove "-adventure" suffix)
                username = channel.name[:-10]  # Remove "-adventure"
                if username not in user_channels:
                    user_channels[username] = []
                user_channels[username].append(channel)
            
            # For each user with multiple channels, keep only the one in player_combat_channels
            for username, channels in user_channels.items():
                if len(channels) <= 1:
                    continue
                
                print(f"Found {len(channels)} duplicate adventure channels for {username}")
                
                # Find which channel is tracked in player_combat_channels
                tracked_channel = None
                for user_id, channel_id in player_combat_channels.items():
                    for channel in channels:
                        if channel.id == channel_id:
                            tracked_channel = channel
                            break
                    if tracked_channel:
                        break
                
                # If no tracked channel found, keep the most recent one
                if not tracked_channel:
                    tracked_channel = max(channels, key=lambda c: c.created_at)
                    print(f"No tracked channel found for {username}, keeping most recent")
                
                # Delete all other channels
                for channel in channels:
                    if channel != tracked_channel:
                        try:
                            await channel.delete(reason="Cleaning up duplicate adventure channel")
                            print(f"Deleted duplicate channel: {channel.name}")
                        except Exception as e:
                            print(f"Failed to delete duplicate channel {channel.name}: {e}")
                            
    except Exception as e:
        print(f"Error during duplicate channel cleanup: {e}")

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    
    # Set custom bot status
    await bot.change_presence(activity=discord.Game(name=".help"))
    
    # Load saved combat channels and validate they still exist
    global player_combat_channels
    player_combat_channels = load_combat_channels()
    
    # Clean up deleted channels from storage
    channels_to_remove = []
    for user_id, channel_id in player_combat_channels.items():
        channel = bot.get_channel(channel_id)
        if not channel:
            channels_to_remove.append(user_id)
    
    for user_id in channels_to_remove:
        del player_combat_channels[user_id]
    
    if channels_to_remove:
        save_combat_channels()
        print(f"Cleaned up {len(channels_to_remove)} deleted channels")
    
    print(f"Loaded {len(player_combat_channels)} saved combat channels")
    
    # Clean up any duplicate adventure channels that may exist
    await cleanup_duplicate_channels()
    
    # Reset all stuck player states on startup
    reset_stuck_players()
    
    await load_cogs()
    print('Bot is ready!')

    # Create necessary directories and files if they don't exist
    if not os.path.exists('data'):
        os.makedirs('data')
        
    if not os.path.exists('hunters_data.json'):
        save_hunters_data({})
    
    # Clear active explorations and raids from cogs after loading
    for cog_name in bot.cogs:
        cog = bot.get_cog(cog_name)
        if hasattr(cog, 'active_explorations'):
            cog.active_explorations.clear()
        if hasattr(cog, 'active_raids'):
            cog.active_raids.clear()
    
    # Start the event loop after the bot is ready and cogs are loaded
    event_cog = bot.get_cog('EventManagement')
    if event_cog:
        event_cog.event_loop.start()  # Start the automated event loop
        print("Event management loop started")

@bot.command(name='start', aliases=['awaken'])
async def start(ctx):
    """Start your journey as a hunter"""
    hunters_data = load_hunters_data()
    user_id = str(ctx.author.id)

    if user_id in hunters_data:
        await ctx.send("You are already a registered hunter!")
        return

    # Initialize new hunter data
    hunters_data[user_id] = {
        "level": 1,
        "exp": 0,
        "rank": "E",
        "hp": 100,
        "max_hp": 100,
        "mp": 50,
        "max_mp": 50,
        "mana": 100,
        "max_mana": 100,
        "strength": 10,
        "agility": 10,
        "intelligence": 10,
        "defense": 5,
        "inventory": [],
        "shadows": [],
        "equipment": {
            "weapon": None,
            "armor": None,
            "accessory": None
        },
        "abilities": ["power_strike", "heal"],
        "active_cooldowns": {},
        "temp_buffs": {},
        "gold": 100,
        "quests": {
            "daily": {},
            "last_daily_reset": ""
        },
        "battle": None,
        "last_defeated_monster": None,
        "pvp_stats": {
            "wins": 0,
            "losses": 0,
            "rank": "Unranked"
        }
    }

    save_hunters_data(hunters_data)
    
    embed = discord.Embed(
        title="🌟 Welcome, New Hunter!",
        description=f"Hunter {ctx.author.name}, your journey in the world of hunters begins now!",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="Starting Stats", 
        value="Level: 1\nRank: E\nHP: 100\nMP: 50\nGold: 100", 
        inline=True
    )
    embed.add_field(
        name="Getting Started", 
        value="Use `.status` to view your profile\nUse `.hunt` to start hunting monsters\nUse `.help` to see all commands", 
        inline=True
    )
    embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
    embed.set_footer(text="Welcome to the Solo Leveling RPG!")
    
    await ctx.send(embed=embed)

def apply_passive_regeneration(hunter):
    """Apply passive health and mana regeneration when out of combat"""
    if hunter.get('battle') is None:  # Only regen when not in battle
        max_hp = hunter.get('max_hp', 100)
        max_mp = hunter.get('max_mp', 50)
        
        # Regenerate 5% of max HP and MP per status check
        regen_hp = max(1, max_hp // 20)  # 5% HP
        regen_mp = max(1, max_mp // 20)  # 5% MP
        
        hunter['hp'] = min(max_hp, hunter.get('hp', 0) + regen_hp)
        hunter['mp'] = min(max_mp, hunter.get('mp', 0) + regen_mp)
        
        return regen_hp, regen_mp
    return 0, 0

def check_if_resting(user_id):
    """Check if a player is currently resting"""
    if user_id in resting_players:
        rest_end_time = resting_players[user_id]
        if time.time() < rest_end_time:
            remaining_time = int(rest_end_time - time.time())
            minutes = remaining_time // 60
            seconds = remaining_time % 60
            return True, f"You are currently resting. Please wait {minutes}:{seconds:02d} before using commands."
        else:
            # Rest period is over
            del resting_players[user_id]
    return False, None

def check_rest_cooldown(user_id):
    """Check if rest command is on cooldown"""
    if user_id in rest_cooldowns:
        cooldown_end = rest_cooldowns[user_id]
        if time.time() < cooldown_end:
            remaining_time = int(cooldown_end - time.time())
            minutes = remaining_time // 60
            seconds = remaining_time % 60
            return True, f"Rest command is on cooldown. Please wait {minutes}:{seconds:02d}"
        else:
            # Cooldown is over
            del rest_cooldowns[user_id]
    return False, None

def check_if_training(user_id):
    """Check if a player is currently training"""
    # Get training cog instance
    training_cog = bot.get_cog('Training')
    if not training_cog:
        return False, None
    
    if user_id not in training_cog.training_sessions:
        return False, None
    
    session = training_cog.training_sessions[user_id]
    remaining = session['end_time'] - time.time()
    
    if remaining <= 0:
        # Training completed, apply stat gains
        complete_training_session(user_id, training_cog, session)
        return False, None
    
    # Player is training
    minutes, seconds = divmod(int(remaining), 60)
    training_type = session['type'].title()
    return True, f"You're currently training **{training_type}**! Please wait {minutes}m {seconds}s before using other commands."

def complete_training_session(user_id, training_cog, session):
    """Complete a training session and apply stat gains"""
    hunters_data = load_hunters_data()
    if user_id not in hunters_data:
        del training_cog.training_sessions[user_id]
        return
    
    hunter = hunters_data[user_id]
    
    # Calculate stat gain
    stat_gain = training_cog.get_stat_gain(session['hunter_level'], session['type'])
    
    # Update base stats (which are the core stats without equipment)
    base_stat_key = f"base_{session['type']}"
    if base_stat_key not in hunter:
        hunter[base_stat_key] = hunter.get(session['type'], 10)
    
    hunter[base_stat_key] += stat_gain
    
    # Update current stat (this will be recalculated with equipment bonuses)
    hunter[session['type']] = hunter.get(session['type'], 10) + stat_gain
    
    # Update total stats for power calculation
    if 'total_stats_gained' not in hunter:
        hunter['total_stats_gained'] = 0
    hunter['total_stats_gained'] += stat_gain
    
    # Recalculate stats with equipment bonuses
    update_hunter_equipment_stats(hunter)
    
    save_hunters_data(hunters_data)
    del training_cog.training_sessions[user_id]

def update_hunter_equipment_stats(hunter):
    """Update hunter stats with equipment bonuses"""
    # Initialize base stats if they don't exist
    if 'base_strength' not in hunter:
        hunter['base_strength'] = hunter.get('strength', 10)
    if 'base_agility' not in hunter:
        hunter['base_agility'] = hunter.get('agility', 10)
    if 'base_intelligence' not in hunter:
        hunter['base_intelligence'] = hunter.get('intelligence', 10)
    if 'base_defense' not in hunter:
        hunter['base_defense'] = hunter.get('defense', 5)
    
    # Reset to base stats
    hunter['strength'] = hunter['base_strength']
    hunter['agility'] = hunter['base_agility']
    hunter['intelligence'] = hunter['base_intelligence']
    hunter['defense'] = hunter['base_defense']  # Start with base defense
    
    # Load item data to get equipment bonuses
    try:
        import json
        with open('data/items.json', 'r') as f:
            items_data = json.load(f)
    except FileNotFoundError:
        return
    
    # Add equipment bonuses
    equipment = hunter.get('equipment', {})
    for item_name in equipment.values():
        if item_name:
            # Find item in all categories
            item_info = None
            for category in items_data.values():
                if item_name in category:
                    item_info = category[item_name]
                    break
            
            if item_info:
                hunter['strength'] += item_info.get('strength', 0)
                hunter['agility'] += item_info.get('agility', 0)
                hunter['intelligence'] += item_info.get('intelligence', 0)
                hunter['defense'] += item_info.get('defense', 0)

@bot.command(name='status')
async def status(ctx):
    """Check your hunter status"""
    user_id = str(ctx.author.id)
    
    # Check for active doorway
    has_doorway, doorway_name = check_for_active_doorway(user_id)
    if has_doorway:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, f"You already have an open doorway ({doorway_name}) where you can continue your adventure! Complete your current exploration first.")
        await ctx.send(embed=embed)
        return
    
    # Check if player is resting
    is_resting, rest_message = check_if_resting(user_id)
    if is_resting:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, rest_message)
        await ctx.send(embed=embed)
        return
    
    # Check if training completed (this will auto-apply stat gains)
    check_if_training(user_id)
    
    hunters_data = load_hunters_data()

    if user_id not in hunters_data:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, "You haven't started your journey yet! Use `.start` to begin.")
        await ctx.send(embed=embed)
        return

    hunter = hunters_data[user_id]
    print(f"[DEBUG] Status - Loaded data for {user_id}: EXP: {hunter.get('exp', 0)}, Level: {hunter.get('level', 1)}, Rank: {hunter.get('rank', 'E')}")
    
    # Ensure equipment stats are current before calculating status
    update_hunter_equipment_stats(hunter)
    
    # Apply passive regeneration when checking status
    regen_hp, regen_mp = apply_passive_regeneration(hunter)

    # Calculate progress bars
    def create_progress_bar(current, maximum, length=10):
        if maximum == 0:
            return "░" * length
        filled = int((current / maximum) * length)
        return "█" * filled + "░" * (length - filled)

    # Calculate exp progress using new leveling system
    total_exp = hunter.get('exp', 0)
    
    # Calculate correct level from EXP (don't use stored level)
    current_level = leveling_system.get_level_from_exp(total_exp)
    print(f"[DEBUG] Status - Calculated level from EXP: Current Level: {current_level}, Stored Level: {hunter.get('level', 1)}")
    
    # Update stored level if it's different
    old_level = hunter.get('level', 1)
    old_rank = hunter.get('rank', 'E')
    
    # Always update level and rank to match current EXP
    hunter['level'] = current_level
    new_rank = leveling_system.get_rank_for_level(current_level)
    hunter['rank'] = new_rank
    print(f"[DEBUG] Status - After level/rank update: Level: {hunter['level']}, Rank: {hunter['rank']}")
    save_hunters_data(hunters_data)
    
    # Handle rank promotion only if rank actually changed
    if old_rank != new_rank:
        print(f"[DEBUG] Rank change detected for {ctx.author}: {old_rank} -> {new_rank}")
        print(f"[DEBUG] Available guild roles: {[role.name for role in ctx.guild.roles]}")
        
        # Enhanced rank promotion with iterative role removal
        try:
            from utils.leveling_system import get_rank_role_name, RANK_ROLES
            
            guild = ctx.guild
            new_rank_name = get_rank_role_name(current_level)
            
            # Find or create new rank role
            new_rank_role = discord.utils.get(guild.roles, name=new_rank_name)
            if new_rank_role is None:
                try:
                    new_rank_role = await guild.create_role(
                        name=new_rank_name,
                        reason="Auto-created rank role for leveling system"
                    )
                    print(f"[DEBUG] Created new rank role: {new_rank_name}")
                except discord.Forbidden:
                    print(f"[DEBUG] Insufficient permissions to create role: {new_rank_name}")
                    pass
                except Exception as e:
                    print(f"[DEBUG] Error creating role {new_rank_name}: {e}")
                    pass
            
            # Remove ALL existing rank roles from user iteratively
            rank_names = list(RANK_ROLES.values())
            roles_to_remove = [r for r in ctx.author.roles if r.name in rank_names]
            
            # Remove roles one by one to prevent bulk removal issues
            for role in roles_to_remove:
                try:
                    await ctx.author.remove_roles(role, reason="Rank update - removing old rank")
                    print(f"[DEBUG] Removed role: {role.name}")
                except discord.Forbidden:
                    print(f"[DEBUG] No permission to remove role: {role.name}")
                    pass
                except Exception as e:
                    print(f"[DEBUG] Error removing role {role.name}: {e}")
                    pass
            
            # Assign new role if it exists
            if new_rank_role:
                try:
                    await ctx.author.add_roles(new_rank_role, reason="Rank promotion")
                    print(f"[DEBUG] Added new role: {new_rank_role.name}")
                except discord.Forbidden:
                    print(f"[DEBUG] No permission to add role: {new_rank_role.name}")
                    pass
                except Exception as e:
                    print(f"[DEBUG] Error adding role {new_rank_role.name}: {e}")
                    pass
            
            # Send DM notification
            try:
                await ctx.author.send(f"🎉 Congratulations! You've been promoted to **{new_rank_name}** (Level {current_level})!")
            except discord.Forbidden:
                pass
            
            # Send rank promotion announcement
            if str(ctx.author.id) == "562670505782542366":
                rank_embed = discord.Embed(
                    title="🎖️ Special Rank Promotion!",
                    description=f"Congratulations {ctx.author.mention}! You have been promoted to **{new_rank}**!",
                    color=discord.Color.gold()
                )
            else:
                rank_embed = discord.Embed(
                    title="🎖️ Rank Promotion!",
                    description=f"{ctx.author.mention} has been promoted to **{new_rank}**!",
                    color=discord.Color.gold()
                )
            
            rank_embed.add_field(
                name="New Level",
                value=f"Level {current_level}",
                inline=True
            )
            rank_embed.add_field(
                name="New Rank",
                value=f"**{new_rank}**",
                inline=True
            )
            await send_system_message(rank_embed)
            
        except Exception as e:
            print(f"[ERROR] Error updating rank role for {ctx.author}: {e}")
            import traceback
            traceback.print_exc()
    
    # Get current level's EXP progress
    current_progress, needed_for_next = leveling_system.get_exp_progress(total_exp, current_level)
    exp_percentage = (current_progress / needed_for_next) * 100 if needed_for_next > 0 else 0

    from utils.theme_utils import get_user_theme_colors
    colors = get_user_theme_colors(ctx.author.id)
    
    # Check for custom title
    custom_title = hunter.get('custom_title', '')
    if custom_title:
        title_text = f"**{custom_title}**\n{hunter['rank']}-Rank Hunter"
    else:
        title_text = f"**{hunter['rank']}-Rank Hunter**"
    
    status_embed = discord.Embed(
        title="📊 Hunter Profile",
        description=title_text,
        color=discord.Color(colors['accent'])
    )

    # Health and Mana bars
    hp_bar = create_progress_bar(hunter['hp'], hunter.get('max_hp', 100))
    mp_bar = create_progress_bar(hunter['mp'], hunter.get('max_mp', 50))
    status_embed.add_field(
        name="Health & Mana",
        value=f"❤️ HP: {hp_bar} {hunter['hp']}/{hunter.get('max_hp', 100)}\n💠 MP: {mp_bar} {hunter['mp']}/{hunter.get('max_mp', 50)}",
        inline=False
    )

    # Level and Experience
    exp_bar = create_progress_bar(current_progress, needed_for_next)
    status_embed.add_field(
        name="Level & Experience",
        value=f"📊 Level: {current_level}\n⭐ EXP: {exp_bar} {current_progress:,}/{needed_for_next:,} ({exp_percentage:.1f}%)\n💫 Total EXP: {total_exp:,}",
        inline=False
    )

    # Combat Stats
    status_embed.add_field(
        name="Combat Stats",
        value=f"⚔️ Strength: {hunter['strength']}\n🏃 Agility: {hunter['agility']}\n🧠 Intelligence: {hunter['intelligence']}\n🛡️ Defense: {hunter.get('defense', 5)}",
        inline=True
    )

    # Equipment
    equipment = hunter['equipment']
    equip_status = (
        f"🗡️ Weapon: {equipment['weapon'] or 'None'}\n"
        f"🛡️ Armor: {equipment['armor'] or 'None'}\n"
        f"💍 Accessory: {equipment['accessory'] or 'None'}"
    )
    status_embed.add_field(name="Equipment", value=equip_status, inline=True)

    # Additional Info
    status_embed.add_field(
        name="Resources",
        value=f"🪙 Gold: {hunter.get('gold', 0)}\n📦 Items: {len(hunter.get('inventory', []))}\n🎨 Theme: {hunter.get('theme', 'dark').title()}",
        inline=True
    )

    # PvP Stats
    pvp_stats = hunter.get('pvp_stats', {'wins': 0, 'losses': 0, 'rank': 'Unranked'})
    status_embed.add_field(
        name="PvP Record",
        value=f"🏆 Wins: {pvp_stats['wins']}\n💀 Losses: {pvp_stats['losses']}\n🎖️ Rank: {pvp_stats['rank']}",
        inline=True
    )

    # Add regeneration message if applicable
    regen_message = ""
    if regen_hp > 0 or regen_mp > 0:
        regen_message = f"\n🔄 Regenerated: +{regen_hp} HP, +{regen_mp} MP"
    
    status_embed.set_footer(text=f"Use .help to see available commands{regen_message}")
    
    # Save data after regeneration
    save_hunters_data(hunters_data)
    
    # Create and send interactive status view
    status_view = StatusView(bot, ctx.author.id, initial_page="main")
    embed = await status_view.get_main_profile_embed(ctx.author.id)
    message = await ctx.send(embed=embed, view=status_view)
    status_view.message = message

@bot.command(name='rest')
async def rest(ctx):
    """Rest to fully restore health and mana (5 minute cooldown, 90 second rest period)"""
    user_id = str(ctx.author.id)

    # Check for active doorway
    has_doorway, doorway_name = check_for_active_doorway(user_id)
    if has_doorway:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, f"You already have an open doorway ({doorway_name}) where you can continue your adventure! Complete your current exploration first.")
        await ctx.send(embed=embed)
        return

    # Check if player is already resting
    is_resting, rest_message = check_if_resting(user_id)
    if is_resting:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, rest_message)
        await ctx.send(embed=embed)
        return

    # Check if rest command is on cooldown
    on_cooldown, cooldown_message = check_rest_cooldown(user_id)
    if on_cooldown:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, cooldown_message)
        await ctx.send(embed=embed)
        return

    hunters_data = load_hunters_data()

    if user_id not in hunters_data:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, "You need to start your journey first! Use `.start`")
        await ctx.send(embed=embed)
        return

    hunter = hunters_data[user_id]
    
    # Check if in battle
    if hunter.get('battle'):
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, "You can't rest while in battle! Finish the fight first.")
        await ctx.send(embed=embed)
        return

    # Check if already at full health and mana
    max_hp = hunter.get('max_hp', 100)
    max_mp = hunter.get('max_mp', 50)
    current_hp = hunter.get('hp', 0)
    current_mp = hunter.get('mp', 0)
    
    if current_hp >= max_hp and current_mp >= max_mp:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, "You're already at full health and mana!")
        await ctx.send(embed=embed)
        return

    # Calculate restoration amounts
    hp_restored = max_hp - current_hp
    mp_restored = max_mp - current_mp
    
    # Restore to full
    hunter['hp'] = max_hp
    hunter['mp'] = max_mp
    
    # Set rest cooldown (5 minutes = 300 seconds)
    rest_cooldowns[user_id] = time.time() + 300
    
    # Set resting period (90 seconds)
    resting_players[user_id] = time.time() + 90
    
    from utils.theme_utils import get_user_theme_colors
    colors = get_user_theme_colors(ctx.author.id)
    
    embed = discord.Embed(
        title="😴 Resting...",
        description="You find a safe place to rest and recover your strength.\n⏰ **You will be unable to use commands for 90 seconds.**",
        color=discord.Color(colors['info'])
    )
    
    embed.add_field(
        name="Recovery",
        value=f"❤️ Health: +{hp_restored} HP (Full)\n💙 Mana: +{mp_restored} MP (Full)",
        inline=False
    )
    
    embed.add_field(
        name="Cooldowns",
        value="🛌 Rest again in: **5 minutes**\n⚔️ Commands available in: **90 seconds**",
        inline=False
    )
    
    embed.set_footer(text="You are now resting peacefully...")
    
    save_hunters_data(hunters_data)
    await ctx.send(embed=embed)

@bot.command(name='hunt')
async def hunt(ctx):
    """Start interactive hunting with button-based combat in a private channel"""
    user_id = str(ctx.author.id)
    
    # Check for active doorway
    has_doorway, doorway_name = check_for_active_doorway(user_id)
    if has_doorway:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, f"You already have an open doorway ({doorway_name}) where you can continue your adventure! Complete your current exploration first.")
        await ctx.send(embed=embed)
        return
    
    # Check if player is resting
    is_resting, rest_message = check_if_resting(user_id)
    if is_resting:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, rest_message)
        await ctx.send(embed=embed)
        return
    
    # Check if player is training
    is_training, training_message = check_if_training(user_id)
    if is_training:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, training_message)
        await ctx.send(embed=embed)
        return
    
    hunters_data = load_hunters_data()

    if user_id not in hunters_data:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, "You need to start your journey first! Use `.start`")
        await ctx.send(embed=embed)
        return

    hunter = hunters_data[user_id]
    
    # Check if already in interactive battle
    if user_id in interactive_battles:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, "You are already in an interactive battle! Use the buttons to continue fighting.")
        await ctx.send(embed=embed)
        return
    
    # Enhanced channel management - check for existing valid channel
    adventure_channel = None
    stored_channel_id = hunter.get('private_adventure_channel_id')
    
    print(f"[DEBUG] Stored channel ID for user {user_id}: {stored_channel_id}")
    
    if stored_channel_id:
        # Try to fetch the channel from Discord's cache/API
        adventure_channel = bot.get_channel(stored_channel_id)
        print(f"[DEBUG] Found existing channel: {adventure_channel}")
        
        if adventure_channel:
            print(f"[DEBUG] Channel category ID: {adventure_channel.category_id}, Expected: {COMBAT_CATEGORY_ID}")
            # Channel exists, check if it's in the correct category
            if adventure_channel.category_id != COMBAT_CATEGORY_ID:
                print(f"[DEBUG] Channel in wrong category, clearing and creating new one")
                await ctx.send("Your previous private adventure channel was moved. Creating a new one.", delete_after=10)
                adventure_channel = None
                hunter['private_adventure_channel_id'] = None
                if user_id in player_combat_channels:
                    del player_combat_channels[user_id]
                    save_combat_channels()
                hunters_data[user_id] = hunter
                save_hunters_data(hunters_data)
            else:
                print(f"[DEBUG] Reusing existing valid channel: {adventure_channel.name}")
                # Channel is valid, ensure permissions and use it
                try:
                    await adventure_channel.set_permissions(ctx.author, read_messages=True, send_messages=True)
                    await adventure_channel.set_permissions(ctx.guild.me, read_messages=True, send_messages=True)
                except discord.Forbidden:
                    pass  # Continue anyway if permissions fail
                
                # Update combat channels tracking
                player_combat_channels[user_id] = adventure_channel.id
                save_combat_channels()
                
                # Send reuse notification
                await ctx.send(f"Continuing your adventure in {adventure_channel.mention}!", delete_after=5)
                # Skip channel creation since we're reusing existing one
                print(f"[DEBUG] Successfully reusing channel, skipping creation")
        else:
            print(f"[DEBUG] Stored channel ID {stored_channel_id} not found, clearing data")
            # Channel no longer exists
            hunter['private_adventure_channel_id'] = None
            if user_id in player_combat_channels:
                del player_combat_channels[user_id]
                save_combat_channels()
            hunters_data[user_id] = hunter
            save_hunters_data(hunters_data)
    
    # Check legacy player_combat_channels for existing channel
    elif user_id in player_combat_channels:
        channel_id = player_combat_channels[user_id]
        if isinstance(channel_id, str):
            channel_id = int(channel_id)
        existing_channel = bot.get_channel(channel_id)
        
        if existing_channel and existing_channel.category_id == COMBAT_CATEGORY_ID:
            adventure_channel = existing_channel
            # Update hunter data with the channel ID
            hunter['private_adventure_channel_id'] = adventure_channel.id
            save_hunters_data(hunters_data)
        else:
            # Channel no longer exists or wrong category
            del player_combat_channels[user_id]
            save_combat_channels()
    
    # Check if already in legacy battles
    if hunter.get('battle') or hunter.get('gate_battle') or hunter.get('dungeon_battle'):
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, "You are already in battle! Complete your current fight first.")
        await ctx.send(embed=embed)
        return
    
    # Check hunt cooldown to prevent spam
    current_time = time.time()
    if user_id in hunt_cooldowns:
        time_since_last = current_time - hunt_cooldowns[user_id]
        if time_since_last < 3:  # 3 second cooldown between hunts
            remaining = 3 - time_since_last
            await ctx.send(f"You need to wait {remaining:.1f} seconds before hunting again!")
            return
    
    # Set hunt cooldown
    hunt_cooldowns[user_id] = current_time

    # Select a random monster based on hunter rank
    monster = select_random_monster(hunter.get('rank', 'E-Rank'))
    
    if not monster:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, "No suitable monsters found for your rank!")
        await ctx.send(embed=embed)
        return
    
    # Create or reuse adventure channel
    if not adventure_channel:
        print(f"[DEBUG] No existing channel found, creating new one")
        # Create new private combat channel
        try:
            adventure_channel = await create_private_combat_channel(ctx)
            if not adventure_channel:
                from utils.theme_utils import get_error_embed
                embed = get_error_embed(ctx.author.id, "Failed to create private combat channel. Please try again.")
                await ctx.send(embed=embed)
                return
            
            # Update hunter data with new channel ID
            hunter['private_adventure_channel_id'] = adventure_channel.id
            hunters_data[user_id] = hunter
            save_hunters_data(hunters_data)
            print(f"[DEBUG] Created new channel {adventure_channel.id} and stored in hunter data")
            
            # Send redirect message in original channel
            from utils.theme_utils import get_user_theme_colors
            colors = get_user_theme_colors(ctx.author.id)
            redirect_embed = discord.Embed(
                title="⚔️ Private Combat Arena Created!",
                description=f"Your personal combat has started in {adventure_channel.mention}",
                color=discord.Color(colors['success'])
            )
            await ctx.send(embed=redirect_embed)
            
            # Send welcome message in combat channel
            from utils.theme_utils import get_info_embed
            welcome_embed = get_info_embed(
                "🏟️ Welcome to Your Private Combat Arena!",
                f"{ctx.author.mention} You venture into the dangerous territories in search of monsters to hunt..."
            )
            await adventure_channel.send(embed=welcome_embed)
        except Exception as e:
            from utils.theme_utils import get_error_embed
            embed = get_error_embed(ctx.author.id, f"Failed to create combat channel: {str(e)}")
            await ctx.send(embed=embed)
            return
    else:
        print(f"[DEBUG] Reusing existing channel {adventure_channel.id}")
        # Using existing channel - send hunt start message
        from utils.theme_utils import get_info_embed
        hunt_embed = get_info_embed(
            "🎯 New Hunt Started!",
            f"{ctx.author.mention} You venture deeper into the dangerous territories in search of new monsters to hunt..."
        )
        await adventure_channel.send(embed=hunt_embed)
        
    # Brief delay for immersion
    await asyncio.sleep(2)
    
    # Create interactive combat view
    combat_view = CombatView(bot, ctx, user_id, monster, combat_type="hunt")
    combat_view.combat_channel = adventure_channel  # Store reference to combat channel
    
    # Create initial combat embed
    embed = combat_view.create_combat_embed(hunter, monster, f"A wild **{monster['name']}** (Level {monster['level']}) appeared!")
    
    # Send combat message with interactive buttons in the combat channel
    combat_message = await adventure_channel.send(embed=embed, view=combat_view)
    combat_view.message = combat_message
    
    # Store battle state
    interactive_battles[user_id] = {
        'hunter': hunter,
        'monster': monster,
        'combat_view': combat_view,
        'combat_message': combat_message,
        'combat_channel': adventure_channel
    }
    
    # Start interactive combat loop
    while not combat_view.combat_ended:
        try:
            # Wait for player action
            await combat_view.wait()
            
            if combat_view.player_action:
                # Process the combat turn
                battle_ended = await process_interactive_combat(ctx, user_id, hunter, monster, combat_view)
                
                if battle_ended:
                    break
                    
                # Create new view for next turn
                new_combat_view = CombatView(bot, ctx, user_id, monster, combat_type="hunt")
                new_combat_view.message = combat_message
                new_combat_view.combat_channel = adventure_channel  # Preserve combat channel reference
                
                # Update embed with current battle state
                embed = new_combat_view.create_combat_embed(hunter, monster, "Choose your next action:")
                
                try:
                    await combat_message.edit(embed=embed, view=new_combat_view)
                    combat_view = new_combat_view
                    interactive_battles[user_id]['combat_view'] = combat_view
                except discord.HTTPException:
                    break
            else:
                # View timed out or was stopped
                break
                
        except asyncio.TimeoutError:
            # Combat timed out
            break
        except Exception as e:
            print(f"[ERROR] Interactive combat error: {e}")
            break
    
    # Clean up battle tracking but keep channel permanent
    if user_id in interactive_battles:
        del interactive_battles[user_id]
    
    # Send completion message to permanent channel
    try:
        completion_embed = discord.Embed(
            title="🏆 Combat Complete",
            description="Your adventure continues! This channel remains open for future battles.",
            color=discord.Color.gold()
        )
        await adventure_channel.send(embed=completion_embed)
    except Exception as e:
        print(f"[ERROR] Failed to send completion message: {e}")

@bot.command(name='attack')
async def attack(ctx):
    """Attack the current monster"""
    user_id = str(ctx.author.id)
    
    # Check if player is resting
    is_resting, rest_message = check_if_resting(user_id)
    if is_resting:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, rest_message)
        await ctx.send(embed=embed)
        return
    
    # Check if player is training
    is_training, training_message = check_if_training(user_id)
    if is_training:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, training_message)
        await ctx.send(embed=embed)
        return
    
    hunters_data = load_hunters_data()

    if user_id not in hunters_data:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, "You need to start your journey first! Use `.start`")
        await ctx.send(embed=embed)
        return

    hunter = hunters_data[user_id]
    
    # Check for event battle first
    if hunter.get('event_battle'):
        await handle_event_battle_attack(ctx, user_id, hunter, hunters_data)
        return
    
    # Check for gate battle
    if hunter.get('gate_battle'):
        await handle_gate_battle_attack(ctx, user_id, hunter, hunters_data)
        return
    
    # Check for dungeon battle
    dungeon_cog = bot.get_cog('DungeonRaids')
    if dungeon_cog and hasattr(dungeon_cog, 'active_raids') and user_id in dungeon_cog.active_raids:
        if hunter.get('dungeon_battle'):
            await handle_dungeon_battle_attack(ctx, user_id, hunter, hunters_data, dungeon_cog)
            return
    
    # Regular hunt battle
    battle = hunter.get('battle')
    
    if not battle:
        await ctx.send("You're not in battle! Use `.hunt` to find monsters.")
        return

    if battle['turn'] != 'hunter':
        await ctx.send("It's not your turn!")
        return

    # Calculate damage
    import random
    base_damage = hunter['strength'] + random.randint(1, 10)
    monster_defense = battle['monster']['defense']
    damage = max(1, base_damage - monster_defense)
    
    # Apply damage to monster
    battle['monster_hp'] = max(0, battle['monster_hp'] - damage)
    
    from utils.theme_utils import get_user_theme_colors, create_progress_bar
    colors = get_user_theme_colors(ctx.author.id)
    
    embed = discord.Embed(
        title="⚔️ Attack!",
        description=f"You attack the {battle['monster']['name']} for {damage} damage!",
        color=discord.Color(colors['warning'])
    )
    
    # Check if monster is defeated
    if battle['monster_hp'] <= 0:
        # Monster defeated - Calculate EXP using Solo Leveling lore-accurate system
        from utils.leveling_system import leveling_system
        monster_rank = battle['monster'].get('rank', 'E')
        exp_gained = leveling_system.calculate_exp_gain('hunt', monster_rank, 'normal')
        gold_gained = battle['monster']['gold_reward']
        
        # Award EXP using new leveling system
        print(f"[DEBUG] Hunt - Before award_exp: User {user_id} has EXP: {hunter.get('exp', 0)}, Level: {hunter.get('level', 1)}")
        level_up_data = await award_exp(user_id, exp_gained, bot, "hunt")
        print(f"[DEBUG] Level up data: {level_up_data}")
        
        # CRITICAL: Reload hunters_data after award_exp to get fresh data
        print(f"[DEBUG] Hunt - Reloading hunters_data after award_exp...")
        hunters_data = load_hunters_data()
        hunter = hunters_data[user_id]
        print(f"[DEBUG] Hunt - After reload: User {user_id} has EXP: {hunter.get('exp', 0)}, Level: {hunter.get('level', 1)}")
        
        hunter['gold'] = hunter.get('gold', 0) + gold_gained
        hunter['last_defeated_monster'] = battle['monster'].copy()
        
        # Update quest progress and daily kills
        try:
            from daily_quest_system import update_quest_progress
            update_quest_progress(hunter, "kill_monsters", 1)
            update_quest_progress(hunter, "earn_gold", gold_gained)
            
            # Update daily kills for mystery gate access
            update_daily_kills(hunter, 1)
        except:
            pass
        
        # Handle level up notifications
        level_up_msg = ""
        if level_up_data.get("levels_gained", 0) > 0:
            level_up_msg = f"\n🎉 **LEVEL UP!** You are now level {level_up_data['new_level']}!"
            
            # Send level up notification to user
            await send_level_up_notification(ctx.author, level_up_data)
            
            # Send level up announcement to system channel
            level_embed = discord.Embed(
                title="🌟 Level Up!",
                description=f"{ctx.author.mention} reached **Level {level_up_data['new_level']}**!",
                color=discord.Color.gold()
            )
            level_embed.add_field(
                name="New Rank",
                value=f"**{level_up_data['new_rank']}**",
                inline=True
            )
            level_embed.add_field(
                name="EXP Gained",
                value=f"+{level_up_data['exp_gained']} EXP",
                inline=True
            )
            await send_system_message(level_embed, user_id=user_id)
            
            # Add rank announcement to global events if rank changed
            if level_up_data.get("rank_changed", False):
                global_events_cog = bot.get_cog('GlobalEvents')
                if global_events_cog and hasattr(global_events_cog, 'add_rank_announcement'):
                    # Reload hunter data to get updated stats
                    updated_hunters_data = load_hunters_data()
                    updated_hunter = updated_hunters_data[user_id]
                    progress_info = f"Level {updated_hunter['level']} • {updated_hunter['strength']} STR • {updated_hunter['agility']} AGI • {updated_hunter['intelligence']} INT"
                    global_events_cog.add_rank_announcement(ctx.author.display_name, level_up_data['new_rank'], updated_hunter['level'], progress_info)
        
        embed.title = "🏆 Victory!"
        embed.description = f"You defeated the {battle['monster']['name']}!"
        embed.color = discord.Color(colors['success'])
        embed.add_field(
            name="Rewards",
            value=f"💰 {gold_gained} Gold\n⭐ {exp_gained} EXP{level_up_msg}",
            inline=False
        )
        
        # Clear battle and set completion time to prevent exploit
        hunter['battle'] = None
        last_hunt_completion[user_id] = time.time()
        
        # Prepare victory data for completion message
        victory_data = {
            'monster_name': battle['monster']['name'],
            'gold_gained': gold_gained,
            'exp_gained': exp_gained,
            'level_up_data': level_up_data if level_up_data.get("levels_gained", 0) > 0 else None,
            'hunter_stats': {
                'level': hunter['level'],
                'hp': hunter['hp'],
                'max_hp': hunter['max_hp'],
                'gold': hunter['gold']
            }
        }
        
        # Send completion message to combat channel
        await send_combat_completion_message(user_id, victory_data)
    else:
        # Monster's turn to attack
        monster_damage = battle['monster']['attack'] + random.randint(1, 5)
        hunter_defense = hunter.get('defense', 5) + (hunter['agility'] // 3)  # Defense stat + agility bonus
        final_damage = max(1, monster_damage - hunter_defense)
        
        hunter['hp'] = max(0, hunter['hp'] - final_damage)
        
        monster_bar = create_progress_bar(battle['monster_hp'], battle['monster']['hp'])
        embed.add_field(
            name="Monster Status",
            value=f"👹 **{battle['monster']['name']}**\n❤️ HP: {battle['monster_hp']}/{battle['monster']['hp']}\n{monster_bar}",
            inline=False
        )
        
        embed.add_field(
            name="Monster Counter-Attack!",
            value=f"The {battle['monster']['name']} attacks you for {final_damage} damage!\n❤️ Your HP: {hunter['hp']}/{hunter.get('max_hp', 100)}",
            inline=False
        )
        
        # Check if hunter is defeated
        if hunter['hp'] <= 0:
            embed.title = "💀 Defeated!"
            embed.description = f"You were defeated by the {battle['monster']['name']}! You respawn with full health."
            embed.color = discord.Color.dark_red()
            embed.add_field(name="Result", value="Battle lost - no rewards gained", inline=False)
            embed.add_field(name="Respawn", value="Your health has been fully restored!", inline=False)
            
            # No penalties, just no rewards - respawn with full health
            hunter['hp'] = hunter.get('max_hp', 100)  # Full health restoration
            hunter['battle'] = None
            
            # Send completion message to combat channel
            await send_combat_completion_message(user_id)
    
    save_hunters_data(hunters_data)
    
    # Send to combat channel for all battle-related responses
    await send_combat_message(ctx, embed)

@bot.command(name='defend')
async def defend(ctx):
    """Defend against monster attack"""
    user_id = str(ctx.author.id)
    
    # Check if player is resting
    is_resting, rest_message = check_if_resting(user_id)
    if is_resting:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, rest_message)
        await ctx.send(embed=embed)
        return
    
    # Check if player is training
    is_training, training_message = check_if_training(user_id)
    if is_training:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, training_message)
        await ctx.send(embed=embed)
        return
    
    hunters_data = load_hunters_data()

    if user_id not in hunters_data:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, "You need to start your journey first! Use `.start`")
        await ctx.send(embed=embed)
        return

    hunter = hunters_data[user_id]
    
    # Check for gate battle first
    if hunter.get('gate_battle'):
        await handle_gate_battle_defend(ctx, user_id, hunter, hunters_data)
        return
    
    # Check for dungeon battle
    dungeon_cog = bot.get_cog('DungeonRaids')
    if dungeon_cog and hasattr(dungeon_cog, 'active_raids') and user_id in dungeon_cog.active_raids:
        if hunter.get('dungeon_battle'):
            await handle_dungeon_battle_defend(ctx, user_id, hunter, hunters_data, dungeon_cog)
            return
    
    # Regular hunt battle
    battle = hunter.get('battle')
    
    if not battle:
        await ctx.send("You're not in battle! Use `.hunt` to find monsters.")
        return

    if battle['turn'] != 'hunter':
        await ctx.send("It's not your turn!")
        return

    import random
    
    # Defending reduces incoming damage and may restore some HP/MP
    monster_damage = battle['monster']['attack']
    defense_reduction = hunter['agility'] + hunter['intelligence'] // 2
    reduced_damage = max(1, monster_damage - defense_reduction)
    
    hunter['hp'] = max(0, hunter['hp'] - reduced_damage)
    
    # Small chance to restore HP/MP when defending
    if random.random() < 0.3:  # 30% chance
        heal_amount = random.randint(5, 15)
        hunter['hp'] = min(hunter.get('max_hp', 100), hunter['hp'] + heal_amount)
        heal_msg = f"\nYou recovered {heal_amount} HP while defending!"
    else:
        heal_msg = ""

    embed = discord.Embed(
        title="🛡️ Defend!",
        description=f"You brace for the {battle['monster']['name']}'s attack!",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="Defense Result",
        value=f"Reduced damage to {reduced_damage} (from {monster_damage})!\n❤️ Your HP: {hunter['hp']}/{hunter.get('max_hp', 100)}{heal_msg}",
        inline=False
    )
    
    embed.add_field(
        name="Monster Status",
        value=f"❤️ HP: {battle['monster_hp']}/{battle['monster']['hp']}",
        inline=True
    )
    
    # Check if hunter is defeated
    if hunter['hp'] <= 0:
        embed.title = "💀 Defeated!"
        embed.description = f"Even while defending, the {battle['monster']['name']} was too strong! You respawn with full health."
        embed.color = discord.Color.dark_red()
        embed.add_field(name="Result", value="Battle lost - no rewards gained", inline=False)
        embed.add_field(name="Respawn", value="Your health has been fully restored!", inline=False)
        
        # No penalties, just no rewards - respawn with full health
        hunter['hp'] = hunter.get('max_hp', 100)  # Full health restoration
        hunter['battle'] = None
        
        # Send completion message to combat channel
        await send_combat_completion_message(user_id)
    
    save_hunters_data(hunters_data)
    
    # Send to combat channel for all defend-related responses
    await send_combat_message(ctx, embed)

@bot.command(name='flee')
async def flee(ctx):
    """Flee from battle"""
    user_id = str(ctx.author.id)
    
    # Check if player is resting
    is_resting, rest_message = check_if_resting(user_id)
    if is_resting:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, rest_message)
        await ctx.send(embed=embed)
        return
    
    # Check if player is training
    is_training, training_message = check_if_training(user_id)
    if is_training:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, training_message)
        await ctx.send(embed=embed)
        return
    
    hunters_data = load_hunters_data()

    if user_id not in hunters_data:
        await ctx.send("You need to start your journey first! Use `.start`")
        return

    hunter = hunters_data[user_id]
    
    # Check for gate battle first
    if hunter.get('gate_battle'):
        await handle_gate_battle_flee(ctx, user_id, hunter, hunters_data)
        return
    
    # Check for dungeon battle
    dungeon_cog = bot.get_cog('DungeonRaids')
    if dungeon_cog and hasattr(dungeon_cog, 'active_raids') and user_id in dungeon_cog.active_raids:
        if hunter.get('dungeon_battle'):
            await handle_dungeon_battle_flee(ctx, user_id, hunter, hunters_data, dungeon_cog)
            return
    
    # Regular hunt battle
    battle = hunter.get('battle')
    
    if not battle:
        await ctx.send("You're not in battle!")
        return

    import random
    
    # Flee success chance based on agility
    flee_chance = 0.5 + (hunter['agility'] * 0.02)  # Base 50% + agility bonus
    flee_chance = min(0.9, flee_chance)  # Cap at 90%
    
    if random.random() < flee_chance:
        # Successful flee
        hunter['battle'] = None
        
        embed = discord.Embed(
            title="🏃 Escaped!",
            description=f"You successfully fled from the {battle['monster']['name']}!",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Result", value="You escaped without rewards, but you're safe!", inline=False)
    else:
        # Failed flee - monster gets free attack
        monster_damage = battle['monster']['attack'] + random.randint(1, 10)
        hunter['hp'] = max(0, hunter['hp'] - monster_damage)
        
        embed = discord.Embed(
            title="🏃 Flee Failed!",
            description=f"You couldn't escape! The {battle['monster']['name']} attacks as you try to flee!",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Attack of Opportunity",
            value=f"You took {monster_damage} damage!\n❤️ HP: {hunter['hp']}/{hunter.get('max_hp', 100)}",
            inline=False
        )
        
        if hunter['hp'] <= 0:
            embed.add_field(name="Defeated", value="You were caught and defeated while fleeing!", inline=False)
            hunter['exp'] = max(0, hunter['exp'] - 75)  # Higher penalty for failed flee
            hunter['gold'] = max(0, hunter.get('gold', 0) - 50)
            hunter['hp'] = 1
            hunter['battle'] = None
            
            # Send completion message to combat channel
            await send_combat_completion_message(user_id)
    
    save_hunters_data(hunters_data)
    
    # Send to combat channel for all flee-related responses
    await send_combat_message(ctx, embed)





@bot.command(name='claim')
async def claim_quest_rewards(ctx):
    """Claim rewards for completed quests"""
    user_id = str(ctx.author.id)
    
    # Check if player is resting
    is_resting, rest_message = check_if_resting(user_id)
    if is_resting:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, rest_message)
        await ctx.send(embed=embed)
        return
    
    hunters_data = load_hunters_data()

    if user_id not in hunters_data:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, "You need to start your journey first! Use `.start`")
        await ctx.send(embed=embed)
        return

    hunter = hunters_data[user_id]
    quests = hunter.get('quests', {})
    daily_quests = quests.get('daily', {})
    weekly_quests = quests.get('weekly', {})
    special_quests = quests.get('special', {})
    
    claimed_rewards = {'gold': 0, 'exp': 0}
    claimed_quests = []
    special_items = []
    
    # Check daily quests
    for quest_id, quest in daily_quests.items():
        if quest.get('completed', False) and not quest.get('claimed', False):
            claimed_rewards['gold'] += quest.get('reward_gold', 0)
            claimed_rewards['exp'] += quest.get('reward_exp', 0)
            quest['claimed'] = True
            claimed_quests.append(f"Daily: {quest['name']}")
    
    # Check weekly quests
    for quest_id, quest in weekly_quests.items():
        if quest.get('completed', False) and not quest.get('claimed', False):
            claimed_rewards['gold'] += quest.get('reward_gold', 0)
            claimed_rewards['exp'] += quest.get('reward_exp', 0)
            quest['claimed'] = True
            claimed_quests.append(f"Weekly: {quest['name']}")
            
            # Add special reward to inventory if present
            if quest.get('special_reward'):
                special_items.append(quest['special_reward'])
    
    # Check special quests
    for quest_id, quest in special_quests.items():
        if quest.get('completed', False) and not quest.get('claimed', False):
            claimed_rewards['gold'] += quest.get('reward_gold', 0)
            claimed_rewards['exp'] += quest.get('reward_exp', 0)
            quest['claimed'] = True
            claimed_quests.append(f"Special: {quest['name']}")
            
            # Add special reward to inventory if present
            if quest.get('special_reward'):
                special_items.append(quest['special_reward'])
    
    # Add special items to inventory
    if special_items:
        if 'inventory' not in hunter:
            hunter['inventory'] = {}
        for item in special_items:
            hunter['inventory'][item] = hunter['inventory'].get(item, 0) + 1
    
    if not claimed_quests:
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(ctx.author.id, "No completed quests to claim!")
        await ctx.send(embed=embed)
        return
    
    # Award rewards using new leveling system
    hunter['gold'] = hunter.get('gold', 0) + claimed_rewards['gold']
    
    level_up_msg = ""
    if claimed_rewards['exp'] > 0:
        level_up_data = await award_exp(user_id, claimed_rewards['exp'], bot, "quest_complete")
        
        # Handle level up notifications
        if level_up_data.get("levels_gained", 0) > 0:
            await send_level_up_notification(ctx.author, level_up_data)
            level_up_msg = f"\n🎉 **LEVEL UP!** You are now level {level_up_data['new_level']}!"
    
    save_hunters_data(hunters_data)
    
    from utils.theme_utils import get_user_theme_colors
    colors = get_user_theme_colors(ctx.author.id)
    
    embed = discord.Embed(
        title="🎁 Quest Rewards Claimed!",
        description="You have successfully claimed your quest rewards",
        color=discord.Color(colors['accent'])
    )
    
    embed.add_field(
        name="Completed Quests",
        value="\n".join(f"✅ {quest}" for quest in claimed_quests),
        inline=False
    )
    
    reward_text = f"💰 {claimed_rewards['gold']} Gold\n⭐ {claimed_rewards['exp']} EXP"
    if special_items:
        reward_text += f"\n🎁 {', '.join(special_items)}"
    reward_text += level_up_msg
    
    embed.add_field(
        name="Rewards Received",
        value=reward_text,
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='reset_stuck')
async def reset_stuck_command(ctx):
    """Admin command to reset all stuck player states"""
    # Only allow specific admin users
    admin_ids = ["299559754756521985"]  # Add admin user IDs here
    if str(ctx.author.id) not in admin_ids:
        await ctx.send("You don't have permission to use this command.")
        return
    
    reset_stuck_players()
    
    # Clear active explorations and raids from cogs
    for cog_name in bot.cogs:
        cog = bot.get_cog(cog_name)
        if hasattr(cog, 'active_explorations'):
            cleared_explorations = len(cog.active_explorations)
            cog.active_explorations.clear()
        if hasattr(cog, 'active_raids'):
            cleared_raids = len(cog.active_raids)
            cog.active_raids.clear()
    
    await ctx.send("✅ All stuck player states have been reset! Players can now use commands normally.")

@bot.command(name='my_adventure')
async def my_adventure(ctx):
    """Show your personal adventure channel"""
    user_id = str(ctx.author.id)
    
    # Check if player has an adventure channel
    if user_id in player_combat_channels:
        channel_id = player_combat_channels[user_id]
        adventure_channel = bot.get_channel(channel_id)
        
        if adventure_channel:
            from utils.theme_utils import get_info_embed
            embed = get_info_embed(
                "🌀 Your Personal Adventure",
                f"Your adventure space: {adventure_channel.mention}\n\n"
                f"All your battles and adventures take place in this private channel. "
                f"Only you can access this dimensional space where you can:\n\n"
                f"⚔️ Fight monsters with `.hunt`\n"
                f"🚪 Explore gates with `.gates`\n"
                f"🏰 Raid dungeons with `.dungeons`\n"
                f"🛡️ Use combat commands: `.attack`, `.defend`, `.flee`\n\n"
                f"Visit your adventure channel to continue any active battles!"
            )
            await ctx.send(embed=embed)
            return
        else:
            # Channel was deleted, remove from tracking
            del player_combat_channels[user_id]
            save_combat_channels()
    
    # Create a new adventure channel for the player
    try:
        adventure_channel = await create_combat_channel(ctx.author)
        if adventure_channel:
            from utils.theme_utils import get_info_embed
            embed = get_info_embed(
                "🌀 Personal Adventure Created!",
                f"Your adventure space: {adventure_channel.mention}\n\n"
                f"This private channel is your dimensional space where you can:\n\n"
                f"⚔️ Fight monsters with `.hunt`\n"
                f"🚪 Explore gates with `.gates`\n"
                f"🏰 Raid dungeons with `.dungeons`\n"
                f"🛡️ Use combat commands: `.attack`, `.defend`, `.flee`\n\n"
                f"Your adventure awaits!"
            )
            await ctx.send(embed=embed)
        else:
            from utils.theme_utils import get_error_embed
            embed = get_error_embed(
                ctx.author.id,
                "❌ Channel Creation Failed",
                "Unable to create your adventure channel. Please try again or contact an administrator."
            )
            await ctx.send(embed=embed)
    except Exception as e:
        print(f"Error creating adventure channel: {e}")
        from utils.theme_utils import get_error_embed
        embed = get_error_embed(
            ctx.author.id,
            "❌ Error",
            "An error occurred while creating your adventure channel. Please try again later."
        )
        await ctx.send(embed=embed)

@bot.command(name='set_jinwoo')
async def set_jinwoo(ctx, target: discord.Member = None):
    """Admin command to set someone as Sung Jinwoo"""
    if ctx.author.id != 299559754756521985:  # Only allow specific user
        await ctx.send("This command is restricted to administrators.")
        return
    
    if target is None:
        target = ctx.author
    
    user_id = str(target.id)
    hunters_data = load_hunters_data()
    
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
            'theme': 'shadow'
        }
    
    hunter = hunters_data[user_id]
    
    # Set Sung Jinwoo stats - Shadow Monarch level
    hunter['level'] = 100
    hunter['exp'] = leveling_system._exp_table.get(100, 1000000)  # Max EXP for level 100
    hunter['rank'] = 'Monarch'
    hunter['custom_title'] = 'Shadow Monarch'
    
    # Shadow Monarch stats
    hunter['base_strength'] = 200
    hunter['base_agility'] = 180
    hunter['base_intelligence'] = 150
    hunter['base_defense'] = 120
    
    hunter['strength'] = 200
    hunter['agility'] = 180
    hunter['intelligence'] = 150
    hunter['defense'] = 120
    
    # Monarch-level HP/MP
    hunter['max_hp'] = 2500
    hunter['max_mp'] = 1500
    hunter['hp'] = 2500
    hunter['mp'] = 1500
    
    # Shadow Monarch wealth
    hunter['gold'] = 1000000
    
    # Shadow theme
    hunter['theme'] = 'shadow'
    
    # Clear any active states
    hunter['battle'] = None
    if 'gate_battle' in hunter:
        del hunter['gate_battle']
    if 'dungeon_battle' in hunter:
        del hunter['dungeon_battle']
    
    save_hunters_data(hunters_data)
    
    await ctx.send(f"✅ {target.mention} has been set as **Sung Jinwoo, the Shadow Monarch**!\n"
                   f"Level 100 • Monarch Rank • 2500 HP • 1500 MP\n"
                   f"Stats: 200 STR • 180 AGI • 150 INT • 120 DEF")

@bot.command(name='set_level')
async def set_level(ctx, user_id: str, level: int):
    """Admin command to set a specific user's level"""
    if ctx.author.id != 299559754756521985:  # Only allow specific user
        await ctx.send("This command is restricted to administrators.")
        return
    
    if level < 1 or level > 100:
        await ctx.send("Level must be between 1 and 100.")
        return
    
    hunters_data = load_hunters_data()
    
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
    
    save_hunters_data(hunters_data)
    
    try:
        user = bot.get_user(int(user_id))
        username = user.display_name if user else f"User {user_id}"
    except:
        username = f"User {user_id}"
    
    await ctx.send(f"✅ Set {username} to Level {level} ({hunter['rank']})\n"
                   f"HP: {hunter['max_hp']} • MP: {hunter['max_mp']}\n"
                   f"Stats: {hunter['strength']} STR • {hunter['agility']} AGI • {hunter['intelligence']} INT • {hunter['defense']} DEF")

@bot.command(name='reset_levels')
async def reset_levels(ctx):
    """Admin command to reset all players to level 1"""
    if ctx.author.id != 299559754756521985:  # Only allow specific user
        await ctx.send("This command is restricted to administrators.")
        return
    
    hunters_data = load_hunters_data()
    reset_count = 0
    
    for user_id, hunter in hunters_data.items():
        # Reset to level 1 with starting stats
        hunter['level'] = 1
        hunter['exp'] = 0
        hunter['rank'] = 'E Rank'
        
        # Reset base stats to starting values
        hunter['base_strength'] = 10
        hunter['base_agility'] = 10
        hunter['base_intelligence'] = 10
        hunter['base_defense'] = 5
        
        # Reset current stats (will be recalculated with equipment)
        hunter['strength'] = 10
        hunter['agility'] = 10
        hunter['intelligence'] = 10
        hunter['defense'] = 5
        
        # Reset HP/MP to starting values
        hunter['max_hp'] = 100
        hunter['max_mp'] = 50
        hunter['hp'] = 100
        hunter['mp'] = 50
        
        # Clear any active battles or explorations
        hunter['battle'] = None
        if 'gate_battle' in hunter:
            del hunter['gate_battle']
        if 'dungeon_battle' in hunter:
            del hunter['dungeon_battle']
        
        reset_count += 1
    
    save_hunters_data(hunters_data)
    
    await ctx.send(f"✅ Reset {reset_count} players to level 1 with starting stats.")

@bot.command(name='migrate_exp')
async def migrate_exp_system(ctx):
    """Admin command to migrate player data to new EXP system"""
    if ctx.author.id != 299559754756521985:  # Only allow specific user
        await ctx.send("This command is restricted to administrators.")
        return
    
    hunters_data = load_hunters_data()
    migrated_count = 0
    
    for user_id, hunter in hunters_data.items():
        # Convert old EXP system to new system
        old_level = hunter.get('level', 1)
        old_exp = hunter.get('exp', 0)
        
        # Calculate appropriate total EXP for their current level
        if old_level <= 1:
            new_total_exp = 0
        else:
            # Give them EXP equivalent to their level achievement
            new_total_exp = leveling_system._exp_table.get(old_level, 0)
        
        # Update their data
        hunter['exp'] = new_total_exp
        hunter['level'] = leveling_system.get_level_from_exp(new_total_exp)
        hunter['rank'] = leveling_system.get_rank_for_level(hunter['level'])
        
        migrated_count += 1
    
    save_hunters_data(hunters_data)
    await ctx.send(f"✅ Migrated {migrated_count} players to the new EXP system!")

@bot.command(name='exp_info', aliases=['leveling'])
async def exp_info(ctx):
    """Display detailed leveling system information"""
    from utils.theme_utils import get_user_theme_colors
    colors = get_user_theme_colors(ctx.author.id)
    
    embed = discord.Embed(
        title="📊 EXP & Leveling System",
        description="Comprehensive leveling system with realistic progression",
        color=discord.Color(colors['accent'])
    )
    
    # Level ranges and EXP requirements
    embed.add_field(
        name="🎯 EXP Requirements by Level Range",
        value=(
            "**Levels 1-10:** 100-300 EXP per level\n"
            "**Levels 11-20:** 500-1,000 EXP per level\n"
            "**Levels 21-30:** 1,500-2,500 EXP per level\n"
            "**Levels 31-40:** 3,000-4,500 EXP per level\n"
            "**Levels 41-50:** 5,000-7,000 EXP per level\n"
            "**Levels 51-60:** 8,000-10,000 EXP per level\n"
            "**Levels 61-70:** 12,000-15,000 EXP per level\n"
            "**Levels 71-80:** 18,000-25,000 EXP per level\n"
            "**Levels 81-90:** 30,000-40,000 EXP per level\n"
            "**Levels 91-100:** 50,000-100,000 EXP per level"
        ),
        inline=False
    )
    
    # Rank progression - Solo Leveling Lore Accurate
    embed.add_field(
        name="🏆 Rank Progression",
        value=(
            "**E Rank:** Levels 1-10 (Beginner hunters)\n"
            "**D Rank:** Levels 11-20 (Low-level hunters)\n"
            "**C Rank:** Levels 21-30 (Mid-tier hunters)\n"
            "**B Rank:** Levels 31-40 (Skilled hunters)\n"
            "**A Rank:** Levels 41-50 (High-level hunters)\n"
            "**S Rank:** Levels 51-60 (Top-tier hunters)\n"
            "**National Level Hunter:** Levels 61-100 (Elite hunters)\n"
            "**Monarch:** Level 100+ (Legendary hunters like Sung Jin-Woo)"
        ),
        inline=True
    )
    
    # EXP sources
    embed.add_field(
        name="⭐ EXP Sources",
        value=(
            "**Hunting:** 25 base EXP per monster\n"
            "**Gate Clear:** 100 base EXP\n"
            "**Dungeon Clear:** 150 base EXP\n"
            "**Boss Kill:** 200 base EXP\n"
            "**Quest Complete:** 50 base EXP\n"
            "**Daily Quest:** 30 base EXP\n"
            "**Weekly Quest:** 100 base EXP\n"
            "**Special Quest:** 300 base EXP"
        ),
        inline=True
    )
    
    # Level up bonuses
    embed.add_field(
        name="💪 Level Up Bonuses",
        value=(
            "**Per Level Gained:**\n"
            "• +3 Stat Points (distributed among STR/AGI/INT)\n"
            "• +20 Max HP\n"
            "• +10 Max MP\n"
            "• Full HP/MP restoration\n"
            "• Automatic rank promotion when reaching thresholds\n"
            "• Private level-up notification with details"
        ),
        inline=False
    )
    
    embed.set_footer(text="EXP scales with enemy rank and quest difficulty • Use .status to see your progress")
    await ctx.send(embed=embed)

@bot.command(name='help')
async def help_command(ctx):
    """Shows all available commands with an interactive menu"""
    user_id = str(ctx.author.id)
    colors = get_user_theme_colors(user_id)
    
    # Load hunter data to determine available commands
    hunters_data = load_hunters_data()
    hunter_exists = user_id in hunters_data

    # Create and send the interactive HelpView
    help_view = HelpView(bot, colors, hunter_exists) 
    
    # Get the initial embed for the "Main" category
    initial_embed = help_view.get_page_embed("Main") 
    
    message = await ctx.send(embed=initial_embed, view=help_view)
    help_view.message = message

@bot.command(name='commands', aliases=['cmd_list'])
async def commands_help(ctx):
    """Display all available commands"""
    from utils.theme_utils import get_user_theme_colors
    colors = get_user_theme_colors(ctx.author.id)
    
    # Main header embed
    embed = discord.Embed(
        title="⚔️ Solo Leveling RPG Command Center",
        description="*Rise from E-Rank to be the best hunter there is*\n\n🌟 **Welcome, Hunter!** Choose your path to greatness:",
        color=discord.Color(colors['accent'])
    )
    
    # Core Commands - Essential for new players
    embed.add_field(
        name="🏁 **ESSENTIAL COMMANDS**",
        value="```\n.start     → Awaken as a hunter\n.status    → View your profile\n.hunt      → Battle monsters\n.rest      → Recover HP/MP\n.my_adventure → Find your private channel```",
        inline=False
    )
    
    # Combat & Battle System
    embed.add_field(
        name="⚔️ **COMBAT SYSTEM**",
        value="```\n.attack    → Strike your enemy\n.defend    → Defensive stance\n.flee      → Escape battle```",
        inline=True
    )
    
    # Quest & Progression
    embed.add_field(
        name="📋 **QUEST SYSTEM**",
        value="```\n.daily     → Daily objectives\n.weekly    → Weekly challenges\n.special   → Legendary quests\n.claim     → Collect rewards```",
        inline=True
    )
    
    # Exploration & Adventure
    embed.add_field(
        name="🌍 **EXPLORATION**",
        value="```\n.gates     → Dimensional gates\n.dungeons  → Raid dungeons\n.enter_gate <name>\n.raid <name>```",
        inline=False
    )
    
    # Economy & Inventory
    embed.add_field(
        name="💰 **ECONOMY & GEAR**",
        value="```\n.shop      → Browse items\n.buy <item> → Purchase gear\n.sell <item> → Sell for 50% price\n.inventory → View items\n.equip <item> → Gear up```",
        inline=True
    )
    
    # Training & Stats
    embed.add_field(
        name="🏋️ **TRAINING SYSTEM**",
        value="```\n.train     → View training options\n.train <stat> → Boost stats\n.training  → Check progress\n.tstats    → Training details```",
        inline=True
    )
    
    # Leveling & Progression System
    embed.add_field(
        name="📊 **LEVELING SYSTEM**",
        value="```\n.exp_info  → View leveling guide\n.leveling  → EXP requirements\n.rank      → Check rank progress\n.migrate_exp → Convert data (admin)```",
        inline=True
    )
    
    # PvP & Social Features
    embed.add_field(
        name="🥊 **PVP & SOCIAL**",
        value="```\n.pvp @user → Challenge hunter\n.rankings  → Leaderboards\n.themes    → Customize UI\n.set_theme <name>```",
        inline=True
    )
    
    # Solo Leveling Information
    embed.add_field(
        name="📖 **SOLO LEVELING INFO**",
        value="```\n.weaponsinfo → All weapons & artifacts\n.bossinfo    → Shadow army details\n.gatesinfo   → Dimensional gates guide\n.dungeonsinfo → Instance dungeons\n.slquickref  → Quick reference```",
        inline=True
    )
    
    # Event System - Global Boss Events
    embed.add_field(
        name="🔥 **EVENT SYSTEM**",
        value="```\n.weekend_exp → Check weekend 2x EXP status\n.event_boss <id> → Spawn event boss (admin)\n.random_boss [tier] → Random boss (admin)\n.list_bosses → View all event bosses```\n\n**How Event Bosses Work:**\n🎯 Watch for event announcements in system channels\n✅ Click \"Join Event\" button to get private chamber access\n⚔️ Battle in turn-based combat with authentic boss dialogue\n🏆 Earn exclusive equipment from weekend special bosses",
        inline=False
    )
    
    # Power User Section
    embed.add_field(
        name="⭐ **QUICK ACCESS & PROGRESSION**",
        value="**Shortcuts:** `.daily` `.weekly` `.special` `.inv` `.exp_info`\n**Leveling:** View `.exp_info` for detailed progression guide\n**Pro Tip:** All activities award EXP - hunt, complete gates/dungeons, and finish quests for optimal growth",
        inline=False
    )
    
    # Footer with styling
    embed.set_footer(
        text="🎮 All commands use '.' prefix | 💡 Type any command to see detailed help",
        icon_url="https://cdn.discordapp.com/emojis/123456789.png"
    )
    
    # Add thumbnail for visual appeal
    embed.set_thumbnail(url="https://i.imgur.com/placeholder.png")
    
    await ctx.send(embed=embed)

def get_rank_requirements():
    """Get rank progression requirements"""
    return {
        'E': {'level': 1, 'next_rank': 'D'},
        'D': {'level': 15, 'next_rank': 'C', 'gates_cleared': 5},
        'C': {'level': 30, 'next_rank': 'B', 'gates_cleared': 15, 'dungeons_cleared': 3},
        'B': {'level': 50, 'next_rank': 'A', 'gates_cleared': 30, 'dungeons_cleared': 10},
        'A': {'level': 70, 'next_rank': 'S', 'gates_cleared': 50, 'dungeons_cleared': 25, 'pvp_wins': 10},
        'S': {'level': 90, 'next_rank': 'National Level', 'gates_cleared': 100, 'dungeons_cleared': 50, 'pvp_wins': 25},
        'National Level': {'level': 100, 'next_rank': None}
    }

def check_rank_up(hunter):
    """Check if hunter qualifies for rank up"""
    current_rank = hunter.get('rank', 'E')
    requirements = get_rank_requirements()
    
    if current_rank not in requirements:
        return False
    
    rank_req = requirements[current_rank]
    next_rank = rank_req.get('next_rank')
    
    if not next_rank:
        return False  # Already at max rank
    
    # Check level requirement
    if hunter['level'] < rank_req.get('level', 1):
        return False
    
    # Check additional requirements
    gates_cleared = hunter.get('gates_cleared', 0)
    dungeons_cleared = hunter.get('dungeons_cleared', 0)
    pvp_wins = hunter.get('pvp_wins', 0)
    
    if gates_cleared < rank_req.get('gates_cleared', 0):
        return False
    if dungeons_cleared < rank_req.get('dungeons_cleared', 0):
        return False
    if pvp_wins < rank_req.get('pvp_wins', 0):
        return False
    
    # All requirements met - promote!
    hunter['rank'] = next_rank
    return True

@bot.command(name='rank')
async def check_rank(ctx):
    """Check your hunter rank and progression"""
    hunters_data = load_hunters_data()
    user_id = str(ctx.author.id)
    
    if user_id not in hunters_data:
        await ctx.send("You need to start your journey first! Use `.start`")
        return
    
    hunter = hunters_data[user_id]
    current_rank = hunter.get('rank', 'E')
    requirements = get_rank_requirements()
    
    from utils.theme_utils import get_user_theme_colors
    colors = get_user_theme_colors(ctx.author.id)
    
    embed = discord.Embed(
        title=f"🏆 Hunter Rank Status",
        description=f"**Current Rank:** {current_rank}-Rank\n**Level:** {hunter['level']}",
        color=discord.Color(colors['accent'])
    )
    
    # Current rank info
    gates_cleared = hunter.get('gates_cleared', 0)
    dungeons_cleared = hunter.get('dungeons_cleared', 0)
    pvp_wins = hunter.get('pvp_wins', 0)
    
    current_progress = f"🚪 Gates Cleared: {gates_cleared}\n🏰 Dungeons Cleared: {dungeons_cleared}\n⚔️ PvP Wins: {pvp_wins}"
    embed.add_field(name="Current Progress", value=current_progress, inline=True)
    
    # Next rank requirements
    if current_rank in requirements:
        rank_req = requirements[current_rank]
        next_rank = rank_req.get('next_rank')
        
        if next_rank:
            next_requirements = []
            
            # Level requirement
            level_req = rank_req.get('level', 1)
            if hunter['level'] >= level_req:
                next_requirements.append(f"✅ Level {level_req}")
            else:
                next_requirements.append(f"❌ Level {level_req} (Current: {hunter['level']})")
            
            # Gates requirement
            gates_req = rank_req.get('gates_cleared', 0)
            if gates_req > 0:
                if gates_cleared >= gates_req:
                    next_requirements.append(f"✅ {gates_req} Gates Cleared")
                else:
                    next_requirements.append(f"❌ {gates_req} Gates Cleared (Current: {gates_cleared})")
            
            # Dungeons requirement
            dungeons_req = rank_req.get('dungeons_cleared', 0)
            if dungeons_req > 0:
                if dungeons_cleared >= dungeons_req:
                    next_requirements.append(f"✅ {dungeons_req} Dungeons Cleared")
                else:
                    next_requirements.append(f"❌ {dungeons_req} Dungeons Cleared (Current: {dungeons_cleared})")
            
            # PvP requirement
            pvp_req = rank_req.get('pvp_wins', 0)
            if pvp_req > 0:
                if pvp_wins >= pvp_req:
                    next_requirements.append(f"✅ {pvp_req} PvP Wins")
                else:
                    next_requirements.append(f"❌ {pvp_req} PvP Wins (Current: {pvp_wins})")
            
            embed.add_field(
                name=f"Requirements for {next_rank}-Rank",
                value="\n".join(next_requirements),
                inline=True
            )
            
            # Check if ready for rank up
            old_rank = hunter.get('rank', 'E')
            if check_rank_up(hunter):
                save_hunters_data(hunters_data)
                
                # Add global rank announcement
                events_cog = bot.get_cog('GlobalEvents')
                if events_cog:
                    progress_info = f"Gates: {hunter.get('gates_cleared', 0)} | Dungeons: {hunter.get('dungeons_cleared', 0)} | PvP: {hunter.get('pvp_wins', 0)}"
                    events_cog.add_rank_announcement(
                        ctx.author.display_name,
                        hunter['rank'],
                        hunter['level'],
                        progress_info
                    )
                
                embed.add_field(
                    name="🎊 RANK UP!",
                    value=f"Congratulations! You have been promoted to **{hunter['rank']}-Rank**!\n*This achievement will be announced globally!*",
                    inline=False
                )
        else:
            embed.add_field(
                name="Maximum Rank",
                value="You have reached the highest rank: National Level!",
                inline=False
            )
    
    embed.set_footer(text="Complete gates, dungeons, and PvP battles to advance your rank!")
    await ctx.send(embed=embed)

async def handle_gate_battle_attack(ctx, user_id, hunter, hunters_data):
    """Handle attack command for gate battles"""
    battle = hunter['gate_battle']
    
    # Ensure active exploration exists for gate battles
    gates_cog = bot.get_cog('Gates')
    if gates_cog and not hasattr(gates_cog, 'active_explorations'):
        gates_cog.active_explorations = {}
    if gates_cog and user_id not in gates_cog.active_explorations:
        # Create minimal exploration data for ongoing battle
        gates_cog.active_explorations[user_id] = {
            'gate_name': 'Current Gate',
            'current_floor': battle.get('floor', 1),
            'total_exp': 0,
            'total_gold': 0
        }
    
    # Calculate damage
    import random
    base_damage = hunter['strength'] + random.randint(1, 10)
    damage = max(1, base_damage)
    
    # Apply damage to monster
    battle['monster_hp'] = max(0, battle['monster_hp'] - damage)
    
    from utils.theme_utils import get_user_theme_colors
    colors = get_user_theme_colors(ctx.author.id)
    
    embed = discord.Embed(
        title="⚔️ Attack!",
        description=f"You attack the {battle['monster']['name']} for {damage} damage!",
        color=discord.Color(colors['warning'])
    )
    
    def create_progress_bar(current, maximum, length=10):
        filled = int((current / maximum) * length)
        bar = "█" * filled + "░" * (length - filled)
        return f"{bar} {current}/{maximum}"
    
    # Check if monster is defeated
    if battle['monster_hp'] <= 0:
        # Monster defeated - advance to next floor or complete
        gates_cog = bot.get_cog('Gates')
        if gates_cog and hasattr(gates_cog, 'active_explorations') and user_id in gates_cog.active_explorations:
            exploration = gates_cog.active_explorations[user_id]
            
            # Award floor rewards
            exp_gained = battle['monster']['exp_reward']
            gold_gained = battle['monster']['gold_reward']
            exploration['total_exp'] += exp_gained
            exploration['total_gold'] += gold_gained
            
            embed.title = "🏆 Floor Cleared!"
            embed.description = f"You defeated the {battle['monster']['name']}!"
            embed.color = discord.Color(colors['success'])
            embed.add_field(
                name="Floor Rewards",
                value=f"💰 {gold_gained} Gold\n⭐ {exp_gained} EXP",
                inline=False
            )
            
            # Update quest progress for killing monsters in gates
            try:
                from daily_quest_system import update_quest_progress
                update_quest_progress(hunter, "kill_monsters", 1)
            except Exception as e:
                print(f"Error updating quest progress in gate: {e}")
            
            # Clear gate battle
            del hunter['gate_battle']
            
            # Check if this was the boss floor
            if battle['is_boss']:
                save_hunters_data(hunters_data)
                await ctx.send(embed=embed)
                await gates_cog.complete_gate_exploration(ctx, user_id, True)
            else:
                # Advance to next floor
                exploration['current_floor'] += 1
                save_hunters_data(hunters_data)
                await ctx.send(embed=embed)
                await asyncio.sleep(2)
                # Validate exploration still exists before proceeding
                if user_id in gates_cog.active_explorations:
                    await gates_cog.process_gate_floor(ctx, user_id)
        return
    
    # Monster still alive - monster counter-attacks
    monster_damage = battle['monster']['attack'] + random.randint(1, 5)
    hunter_defense = hunter['agility'] // 2
    final_damage = max(1, monster_damage - hunter_defense)
    
    hunter['hp'] = max(0, hunter['hp'] - final_damage)
    
    monster_bar = create_progress_bar(battle['monster_hp'], battle['monster']['hp'])
    hunter_bar = create_progress_bar(hunter['hp'], hunter.get('max_hp', 100))
    
    embed.add_field(
        name="Monster Status",
        value=f"👹 **{battle['monster']['name']}**\n❤️ HP: {battle['monster_hp']}/{battle['monster']['hp']}\n{monster_bar}",
        inline=False
    )
    
    embed.add_field(
        name="Monster Counter-Attack!",
        value=f"The {battle['monster']['name']} attacks you for {final_damage} damage!\n❤️ Your HP: {hunter['hp']}/{hunter.get('max_hp', 100)}\n{hunter_bar}",
        inline=False
    )
    
    # Check if hunter is defeated
    if hunter['hp'] <= 0:
        embed.title = "💀 Defeated!"
        embed.description = f"You were defeated by the {battle['monster']['name']}!"
        embed.color = discord.Color.dark_red()
        
        # Complete gate exploration as failure
        gates_cog = bot.get_cog('Gates')
        if gates_cog and hasattr(gates_cog, 'active_explorations') and user_id in gates_cog.active_explorations:
            del hunter['gate_battle']
            hunter['hp'] = hunter.get('max_hp', 100)  # Respawn with full health
            save_hunters_data(hunters_data)
            await ctx.send(embed=embed)
            await gates_cog.complete_gate_exploration(ctx, user_id, False)
            return
    else:
        # Battle continues - show combat commands
        embed.add_field(
            name="Combat Commands",
            value="`.attack` - Attack the enemy\n`.defend` - Reduce incoming damage\n`.flee` - Escape from battle",
            inline=False
        )
    
    save_hunters_data(hunters_data)
    await ctx.send(embed=embed)

async def handle_dungeon_battle_attack(ctx, user_id, hunter, hunters_data, dungeon_cog):
    """Handle attack command for dungeon battles"""
    if not hasattr(dungeon_cog, 'active_raids') or user_id not in dungeon_cog.active_raids:
        return
    
    raid = dungeon_cog.active_raids[user_id]
    battle = hunter.get('dungeon_battle')
    
    if not battle:
        return
    
    # Calculate damage
    import random
    base_damage = hunter['strength'] + random.randint(1, 10)
    damage = max(1, base_damage)
    
    # Apply damage to monster
    battle['monster_hp'] = max(0, battle['monster_hp'] - damage)
    
    from utils.theme_utils import get_user_theme_colors
    colors = get_user_theme_colors(ctx.author.id)
    
    embed = discord.Embed(
        title="⚔️ Attack!",
        description=f"You attack the {battle['monster']['name']} for {damage} damage!",
        color=discord.Color(colors['warning'])
    )
    
    def create_progress_bar(current, maximum, length=10):
        filled = int((current / maximum) * length)
        bar = "█" * filled + "░" * (length - filled)
        return f"{bar} {current}/{maximum}"
    
    # Check if monster is defeated
    if battle['monster_hp'] <= 0:
        # Monster defeated - advance to next floor or complete
        exp_gained = battle['monster']['exp_reward']
        gold_gained = battle['monster']['gold_reward']
        raid['total_exp'] += exp_gained
        raid['total_gold'] += gold_gained
        
        embed.title = "🏆 Floor Cleared!"
        embed.description = f"You defeated the {battle['monster']['name']}!"
        embed.color = discord.Color(colors['success'])
        embed.add_field(
            name="Floor Rewards",
            value=f"💰 {gold_gained} Gold\n⭐ {exp_gained} EXP",
            inline=False
        )
        
        # Update quest progress for killing monsters in dungeons
        try:
            from daily_quest_system import update_quest_progress
            update_quest_progress(hunter, "kill_monsters", 1)
        except Exception as e:
            print(f"Error updating quest progress in dungeon: {e}")
        
        # Clear dungeon battle
        del hunter['dungeon_battle']
        
        # Check if this was the boss floor
        if battle['is_boss']:
            save_hunters_data(hunters_data)
            await ctx.send(embed=embed)
            await dungeon_cog.complete_raid(ctx, user_id, True)
        else:
            # Advance to next floor
            raid['current_floor'] += 1
            save_hunters_data(hunters_data)
            await ctx.send(embed=embed)
            await asyncio.sleep(2)
            await dungeon_cog.process_floor(ctx, user_id)
        return
    
    # Monster still alive - monster counter-attacks
    monster_damage = battle['monster']['attack'] + random.randint(1, 5)
    hunter_defense = hunter['agility'] // 2
    final_damage = max(1, monster_damage - hunter_defense)
    
    hunter['hp'] = max(0, hunter['hp'] - final_damage)
    
    monster_bar = create_progress_bar(battle['monster_hp'], battle['monster']['hp'])
    hunter_bar = create_progress_bar(hunter['hp'], hunter.get('max_hp', 100))
    
    embed.add_field(
        name="Monster Status",
        value=f"👹 **{battle['monster']['name']}**\n❤️ HP: {battle['monster_hp']}/{battle['monster']['hp']}\n{monster_bar}",
        inline=False
    )
    
    embed.add_field(
        name="Monster Counter-Attack!",
        value=f"The {battle['monster']['name']} attacks you for {final_damage} damage!\n❤️ Your HP: {hunter['hp']}/{hunter.get('max_hp', 100)}\n{hunter_bar}",
        inline=False
    )
    
    # Check if hunter is defeated
    if hunter['hp'] <= 0:
        embed.title = "💀 Defeated!"
        embed.description = f"You were defeated by the {battle['monster']['name']}!"
        embed.color = discord.Color.dark_red()
        
        # Complete dungeon raid as failure
        del hunter['dungeon_battle']
        hunter['hp'] = hunter.get('max_hp', 100)  # Respawn with full health
        save_hunters_data(hunters_data)
        await ctx.send(embed=embed)
        await dungeon_cog.complete_raid(ctx, user_id, False)
        return
    else:
        # Battle continues - show combat commands
        embed.add_field(
            name="Combat Commands",
            value="`.attack` - Attack the enemy\n`.defend` - Reduce incoming damage\n`.flee` - Escape from battle",
            inline=False
        )
    
    save_hunters_data(hunters_data)
    await ctx.send(embed=embed)

async def handle_gate_battle_defend(ctx, user_id, hunter, hunters_data):
    """Handle defend command for gate battles"""
    battle = hunter['gate_battle']
    
    import random
    
    # Defending reduces incoming damage and may restore some HP/MP
    monster_damage = battle['monster']['attack'] + random.randint(1, 5)
    defense_reduction = hunter['agility'] + hunter['intelligence'] // 2
    reduced_damage = max(1, monster_damage - defense_reduction)
    
    hunter['hp'] = max(0, hunter['hp'] - reduced_damage)
    
    # Small chance to restore HP/MP when defending
    heal_msg = ""
    if random.random() < 0.3:  # 30% chance
        heal_amount = random.randint(5, 15)
        hunter['hp'] = min(hunter.get('max_hp', 100), hunter['hp'] + heal_amount)
        heal_msg = f"\nYou recovered {heal_amount} HP while defending!"
    
    from utils.theme_utils import get_user_theme_colors
    colors = get_user_theme_colors(ctx.author.id)
    
    embed = discord.Embed(
        title="🛡️ Defend!",
        description=f"You defended against the {battle['monster']['name']}'s attack!",
        color=discord.Color(colors['info'])
    )
    
    def create_progress_bar(current, maximum, length=10):
        filled = int((current / maximum) * length)
        bar = "█" * filled + "░" * (length - filled)
        return f"{bar} {current}/{maximum}"
    
    hunter_bar = create_progress_bar(hunter['hp'], hunter.get('max_hp', 100))
    monster_bar = create_progress_bar(battle['monster_hp'], battle['monster']['hp'])
    
    embed.add_field(
        name="Combat Result",
        value=f"You took {reduced_damage} damage (reduced by defense)!{heal_msg}\n❤️ Your HP: {hunter['hp']}/{hunter.get('max_hp', 100)}\n{hunter_bar}",
        inline=False
    )
    
    embed.add_field(
        name="Enemy Status",
        value=f"👹 **{battle['monster']['name']}**\n❤️ HP: {battle['monster_hp']}/{battle['monster']['hp']}\n{monster_bar}",
        inline=False
    )
    
    # Check if hunter is defeated
    if hunter['hp'] <= 0:
        embed.title = "💀 Defeated!"
        embed.description = f"You were defeated by the {battle['monster']['name']}!"
        embed.color = discord.Color.dark_red()
        
        # Complete gate exploration as failure
        gates_cog = bot.get_cog('Gates')
        if gates_cog and hasattr(gates_cog, 'active_explorations') and user_id in gates_cog.active_explorations:
            del hunter['gate_battle']
            hunter['hp'] = hunter.get('max_hp', 100)  # Respawn with full health
            save_hunters_data(hunters_data)
            await ctx.send(embed=embed)
            await gates_cog.complete_gate_exploration(ctx, user_id, False)
            return
    
    save_hunters_data(hunters_data)
    await ctx.send(embed=embed)

async def handle_dungeon_battle_defend(ctx, user_id, hunter, hunters_data, dungeon_cog):
    """Handle defend command for dungeon battles"""
    battle = hunter['dungeon_battle']
    
    import random
    
    # Defending reduces incoming damage and may restore some HP/MP
    monster_damage = battle['monster']['attack'] + random.randint(1, 5)
    defense_reduction = hunter['agility'] + hunter['intelligence'] // 2
    reduced_damage = max(1, monster_damage - defense_reduction)
    
    hunter['hp'] = max(0, hunter['hp'] - reduced_damage)
    
    # Small chance to restore HP/MP when defending
    heal_msg = ""
    if random.random() < 0.3:  # 30% chance
        heal_amount = random.randint(5, 15)
        hunter['hp'] = min(hunter.get('max_hp', 100), hunter['hp'] + heal_amount)
        heal_msg = f"\nYou recovered {heal_amount} HP while defending!"
    
    from utils.theme_utils import get_user_theme_colors
    colors = get_user_theme_colors(ctx.author.id)
    
    embed = discord.Embed(
        title="🛡️ Defend!",
        description=f"You defended against the {battle['monster']['name']}'s attack!",
        color=discord.Color(colors['info'])
    )
    
    def create_progress_bar(current, maximum, length=10):
        filled = int((current / maximum) * length)
        bar = "█" * filled + "░" * (length - filled)
        return f"{bar} {current}/{maximum}"
    
    hunter_bar = create_progress_bar(hunter['hp'], hunter.get('max_hp', 100))
    monster_bar = create_progress_bar(battle['monster_hp'], battle['monster']['hp'])
    
    embed.add_field(
        name="Combat Result",
        value=f"You took {reduced_damage} damage (reduced by defense)!{heal_msg}\n❤️ Your HP: {hunter['hp']}/{hunter.get('max_hp', 100)}\n{hunter_bar}",
        inline=False
    )
    
    embed.add_field(
        name="Enemy Status",
        value=f"👹 **{battle['monster']['name']}**\n❤️ HP: {battle['monster_hp']}/{battle['monster']['hp']}\n{monster_bar}",
        inline=False
    )
    
    # Check if hunter is defeated
    if hunter['hp'] <= 0:
        embed.title = "💀 Defeated!"
        embed.description = f"You were defeated by the {battle['monster']['name']}!"
        embed.color = discord.Color.dark_red()
        
        # Complete dungeon raid as failure
        del hunter['dungeon_battle']
        hunter['hp'] = hunter.get('max_hp', 100)  # Respawn with full health
        save_hunters_data(hunters_data)
        await ctx.send(embed=embed)
        await dungeon_cog.complete_raid(ctx, user_id, False)
        return
    
    save_hunters_data(hunters_data)
    await ctx.send(embed=embed)

async def handle_gate_battle_flee(ctx, user_id, hunter, hunters_data):
    """Handle flee command for gate battles"""
    battle = hunter['gate_battle']
    
    import random
    
    # Flee success chance based on agility
    flee_chance = 0.5 + (hunter['agility'] * 0.02)  # Base 50% + agility bonus
    flee_chance = min(0.9, flee_chance)  # Cap at 90%
    
    from utils.theme_utils import get_user_theme_colors
    colors = get_user_theme_colors(ctx.author.id)
    
    if random.random() < flee_chance:
        # Successful flee - complete gate exploration as failure
        gates_cog = bot.get_cog('Gates')
        if gates_cog and hasattr(gates_cog, 'active_explorations') and user_id in gates_cog.active_explorations:
            del hunter['gate_battle']
            save_hunters_data(hunters_data)
            
            embed = discord.Embed(
                title="🏃 Escaped!",
                description=f"You successfully fled from the {battle['monster']['name']}!",
                color=discord.Color.yellow()
            )
            embed.add_field(name="Result", value="You escaped but failed to complete the gate exploration.", inline=False)
            await ctx.send(embed=embed)
            await gates_cog.complete_gate_exploration(ctx, user_id, False)
    else:
        # Failed flee - monster gets free attack
        monster_damage = battle['monster']['attack'] + random.randint(1, 5)
        hunter['hp'] = max(0, hunter['hp'] - monster_damage)
        
        embed = discord.Embed(
            title="❌ Flee Failed!",
            description=f"You failed to escape from the {battle['monster']['name']}!",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Consequence",
            value=f"The {battle['monster']['name']} attacks you for {monster_damage} damage!\n❤️ Your HP: {hunter['hp']}/{hunter.get('max_hp', 100)}",
            inline=False
        )
        
        # Check if hunter is defeated
        if hunter['hp'] <= 0:
            embed.add_field(name="💀 Defeated!", value="You were defeated while trying to flee!", inline=False)
            gates_cog = bot.get_cog('Gates')
            if gates_cog and hasattr(gates_cog, 'active_explorations') and user_id in gates_cog.active_explorations:
                del hunter['gate_battle']
                hunter['hp'] = hunter.get('max_hp', 100)  # Respawn with full health
                save_hunters_data(hunters_data)
                await ctx.send(embed=embed)
                await gates_cog.complete_gate_exploration(ctx, user_id, False)
                return
        
        save_hunters_data(hunters_data)
        await ctx.send(embed=embed)

async def handle_dungeon_battle_flee(ctx, user_id, hunter, hunters_data, dungeon_cog):
    """Handle flee command for dungeon battles"""
    battle = hunter['dungeon_battle']
    
    import random
    
    # Flee success chance based on agility
    flee_chance = 0.5 + (hunter['agility'] * 0.02)  # Base 50% + agility bonus
    flee_chance = min(0.9, flee_chance)  # Cap at 90%
    
    from utils.theme_utils import get_user_theme_colors
    colors = get_user_theme_colors(ctx.author.id)
    
    if random.random() < flee_chance:
        # Successful flee - complete dungeon raid as failure
        del hunter['dungeon_battle']
        save_hunters_data(hunters_data)
        
        embed = discord.Embed(
            title="🏃 Escaped!",
            description=f"You successfully fled from the {battle['monster']['name']}!",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Result", value="You escaped but failed to complete the dungeon raid.", inline=False)
        await ctx.send(embed=embed)
        await dungeon_cog.complete_raid(ctx, user_id, False)
    else:
        # Failed flee - monster gets free attack
        monster_damage = battle['monster']['attack'] + random.randint(1, 5)
        hunter['hp'] = max(0, hunter['hp'] - monster_damage)
        
        embed = discord.Embed(
            title="❌ Flee Failed!",
            description=f"You failed to escape from the {battle['monster']['name']}!",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Consequence",
            value=f"The {battle['monster']['name']} attacks you for {monster_damage} damage!\n❤️ Your HP: {hunter['hp']}/{hunter.get('max_hp', 100)}",
            inline=False
        )
        
        # Check if hunter is defeated
        if hunter['hp'] <= 0:
            embed.add_field(name="💀 Defeated!", value="You were defeated while trying to flee!", inline=False)
            del hunter['dungeon_battle']
            hunter['hp'] = hunter.get('max_hp', 100)  # Respawn with full health
            save_hunters_data(hunters_data)
            await ctx.send(embed=embed)
            await dungeon_cog.complete_raid(ctx, user_id, False)
            return
        
        save_hunters_data(hunters_data)
        await ctx.send(embed=embed)

async def handle_event_battle_attack(ctx, user_id, hunter, hunters_data):
    """Handle attack command for event battles"""
    event_battle = hunter.get('event_battle')
    if not event_battle:
        await ctx.send("You're not in an event battle!")
        return
    
    boss = event_battle['boss']
    
    if boss['current_hp'] <= 0:
        await ctx.send("The boss is already defeated!")
        return
    
    from utils.theme_utils import get_user_theme_colors, create_progress_bar
    colors = get_user_theme_colors(ctx.author.id)
    
    # Calculate damage
    import random
    base_damage = hunter['strength'] + random.randint(10, 30)
    boss_defense = boss['defense']
    damage = max(1, base_damage - boss_defense)
    
    # Apply damage to boss
    boss['current_hp'] = max(0, boss['current_hp'] - damage)
    
    embed = discord.Embed(
        title="⚔️ Attack!",
        description=f"You attack the {boss['name']} for {damage} damage!",
        color=discord.Color(colors['warning'])
    )
    
    # Add boss HP bar
    hp_bar = create_progress_bar(boss['current_hp'], boss['max_hp'])
    embed.add_field(
        name=f"{boss['name']} HP",
        value=f"{hp_bar} {boss['current_hp']:,}/{boss['max_hp']:,}",
        inline=False
    )
    
    # Check if boss is defeated
    if boss['current_hp'] <= 0:
        # Boss defeated
        exp_gained = boss['exp_reward']
        gold_gained = boss['gold_reward']
        
        # Award EXP using new leveling system
        from utils.leveling_system import award_exp
        level_up_data = await award_exp(user_id, exp_gained, bot, "event_battle")
        
        # CRITICAL: Reload hunters_data after award_exp
        hunters_data = load_hunters_data()
        hunter = hunters_data[user_id]
        
        # Award gold
        hunter['gold'] = hunter.get('gold', 0) + gold_gained
        
        # Build level up message
        level_up_msg = ""
        if level_up_data.get('levels_gained', 0) > 0:
            level_up_msg = f"\n🆙 **Level Up!** {level_up_data['old_level']} → {level_up_data['new_level']}"
            if level_up_data.get("rank_changed", False):
                level_up_msg += f"\n🏆 **Rank Up!** {level_up_data['old_rank']} → {level_up_data['new_rank']}"
        
        embed.title = "🏆 Victory!"
        embed.description = f"You defeated the {boss['name']}!"
        embed.color = discord.Color(colors['success'])
        embed.add_field(
            name="Rewards",
            value=f"💰 {gold_gained:,} Gold\n⭐ {exp_gained:,} EXP{level_up_msg}",
            inline=False
        )
        
        if boss.get('drops'):
            embed.add_field(
                name="🎁 Loot Drops",
                value=", ".join(boss['drops']),
                inline=False
            )
        
        # Clear event battle
        hunter['event_battle'] = None
        hunters_data[user_id] = hunter
        save_hunters_data(hunters_data)
        
        # Clear from GlobalEvents cog
        global_events_cog = bot.get_cog('GlobalEvents')
        if global_events_cog and hasattr(global_events_cog, 'event_battles'):
            if user_id in global_events_cog.event_battles:
                del global_events_cog.event_battles[user_id]
        
        await ctx.send(embed=embed)
        return
    
    else:
        # Boss counter-attacks
        boss_damage = boss['attack'] - hunter.get('defense', 0)
        boss_damage = max(boss_damage // 3, 10)  # Reduce boss damage for balance
        
        hunter['hp'] = max(1, hunter['hp'] - boss_damage)
        
        embed.add_field(
            name="💥 Boss Counter-Attack",
            value=f"The {boss['name']} strikes back for {boss_damage} damage!",
            inline=False
        )
        
        # Update hunter HP bar
        hunter_hp_bar = create_progress_bar(hunter['hp'], hunter.get('max_hp', 100))
        embed.add_field(
            name="Your HP",
            value=f"{hunter_hp_bar} {hunter['hp']}/{hunter.get('max_hp', 100)}",
            inline=False
        )
        
        # Check if hunter died
        if hunter['hp'] <= 1:
            embed.add_field(
                name="💀 Defeated",
                value="You have been defeated! The boss battle ends.",
                inline=False
            )
            
            # Clear event battle
            hunter['event_battle'] = None
        
        # Update hunter data
        hunters_data[user_id] = hunter
        save_hunters_data(hunters_data)
        
        await ctx.send(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found! Use `.commands` to see available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument! Use `.commands` for command usage.")
    else:
        print(f"An error occurred: {error}")
        await ctx.send("An error occurred while processing your command.")

# Run the bot
async def main():
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("Error: DISCORD_TOKEN not found in environment variables!")
        return
    
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
