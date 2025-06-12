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
SYSTEM_CHANNEL_ID = 1381439963656355849  # announcements channel for system messages
COMBAT_CATEGORY_ID = 1382589016393650248  # Category for temporary combat channels
PRIVATE_EVENT_CATEGORY_ID = 1382529024022155274  # New category for private event channels

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
        # Ensure monster has required fields
        monster.setdefault('name', 'Unknown Monster')
        monster.setdefault('hp', 100)
        monster.setdefault('max_hp', monster['hp'])
        monster.setdefault('attack', 20)
        monster.setdefault('defense', 5)
        monster.setdefault('exp_reward', 25)
        monster.setdefault('gold_reward', 15)
        return monster
    else:
        # Return a default monster if no monsters found
        return {
            'name': 'Shadow Wolf',
            'hp': 80,
            'max_hp': 80,
            'attack': 25,
            'defense': 8,
            'exp_reward': 25,
            'gold_reward': 15
        }

async def process_interactive_combat(ctx, user_id, hunter, monster, combat_view):
    """Process interactive combat turn"""
    try:
        # This function is called by the combat view buttons
        # The actual combat logic is handled in the CombatView class
        pass
    except Exception as e:
        print(f"Error in interactive combat: {e}")

def load_combat_channels():
    """Load combat channel data from file"""
    try:
        with open('combat_channels.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_combat_channels():
    """Save combat channel data to file"""
    try:
        with open('combat_channels.json', 'w') as f:
            json.dump(player_combat_channels, f, indent=4)
    except Exception as e:
        print(f"Error saving combat channels: {e}")

async def create_private_combat_channel(ctx):
    """Create a private temporary combat channel for a player"""
    try:
        user_id = str(ctx.author.id)
        
        # Check if user already has a combat channel
        if user_id in player_combat_channels:
            channel_id = player_combat_channels[user_id]
            channel = bot.get_channel(channel_id)
            if channel:
                # Channel still exists, redirect user
                redirect_embed = discord.Embed(
                    title="🏟️ Combat Channel Active",
                    description=f"You already have an active combat channel: {channel.mention}",
                    color=discord.Color.blue()
                )
                await ctx.send(embed=redirect_embed, delete_after=5)
                return channel
            else:
                # Channel no longer exists, remove from tracking
                del player_combat_channels[user_id]
        
        # Prevent race conditions during channel creation
        if user_id in channel_creation_locks:
            await ctx.send("⏳ Combat channel is being created, please wait...", delete_after=3)
            return None
        
        channel_creation_locks[user_id] = True
        
        try:
            guild = ctx.guild
            category = bot.get_channel(COMBAT_CATEGORY_ID)
            
            # Create channel permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
            
            # Create temporary combat channel
            channel_name = f"hunt-{ctx.author.display_name.lower().replace(' ', '-')}-{int(time.time())}"
            combat_channel = await guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Private combat channel for {ctx.author.display_name}"
            )
            
            # Track the channel
            player_combat_channels[user_id] = combat_channel.id
            save_combat_channels()
            
            # Store in bot's temporary tracking
            if not hasattr(bot, 'temp_combat_channels'):
                bot.temp_combat_channels = {}
            bot.temp_combat_channels[user_id] = combat_channel.id
            
            # Send welcome message
            welcome_embed = discord.Embed(
                title="🏟️ Private Combat Arena",
                description=f"Welcome to your private hunting ground, {ctx.author.mention}!",
                color=discord.Color.green()
            )
            
            welcome_embed.add_field(
                name="🎯 Combat Features",
                value="• Private channel for focused combat\n• Interactive button-based fighting\n• Real-time damage and status updates\n• Automatic cleanup when done",
                inline=False
            )
            
            await combat_channel.send(embed=welcome_embed)
            
            return combat_channel
            
        finally:
            # Remove the lock when done
            channel_creation_locks.pop(user_id, None)
        
    except Exception as e:
        print(f"Error creating private combat channel: {e}")
        # Remove the lock on error
        channel_creation_locks.pop(user_id, None)
        return None

async def send_system_message(embed, channel_override=None, user_id=None):
    """Send system messages to designated channel, or private combat channel if user_id provided"""
    try:
        target_channel = None
        
        # Priority 1: Check for user's private combat channel
        if user_id and str(user_id) in player_combat_channels:
            channel_id = player_combat_channels[str(user_id)]
            target_channel = bot.get_channel(channel_id)
        
        # Priority 2: Use channel override
        if not target_channel and channel_override:
            target_channel = channel_override
        
        # Priority 3: Use system channel
        if not target_channel:
            target_channel = bot.get_channel(SYSTEM_CHANNEL_ID)
        
        if target_channel:
            await target_channel.send(embed=embed)
        else:
            print("No valid channel found for system message")
            
    except Exception as e:
        print(f"Error sending system message: {e}")

async def create_combat_channel(user):
    """Create a persistent private combat channel for a player"""
    try:
        guild = user.guild
        category = bot.get_channel(COMBAT_CATEGORY_ID)
        
        # Create channel permissions - private to user only
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        
        # Create the channel
        channel_name = f"adventure-{user.display_name.lower().replace(' ', '-')}"
        channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Private adventure channel for {user.display_name}"
        )
        
        return channel
        
    except Exception as e:
        print(f"Error creating combat channel: {e}")
        return None

async def send_combat_completion_message(user_id, victory_data=None):
    """Send completion message to combat channel without deletion"""
    try:
        # Check if user has a private combat channel
        if str(user_id) in player_combat_channels:
            channel_id = player_combat_channels[str(user_id)]
            channel = bot.get_channel(channel_id)
            
            if channel:
                if victory_data:
                    victory_embed = discord.Embed(
                        title="🎉 Combat Complete!",
                        description=f"Congratulations! You have defeated the {victory_data.get('monster_name', 'monster')}!",
                        color=discord.Color.gold()
                    )
                    
                    victory_embed.add_field(
                        name="🏆 Rewards",
                        value=f"**EXP:** +{victory_data.get('exp', 0)}\n**Gold:** +{victory_data.get('gold', 0)}",
                        inline=True
                    )
                    
                    if victory_data.get('level_up'):
                        victory_embed.add_field(
                            name="📈 Level Up!",
                            value=f"You reached level {victory_data.get('new_level', '?')}!",
                            inline=True
                        )
                        victory_embed.color = discord.Color.purple()
                
                await channel.send(embed=victory_embed)
    except Exception as e:
        print(f"Error sending combat completion message: {e}")

async def send_combat_message(ctx, embed, redirect_message=None):
    """Send combat messages to player's private combat channel"""
    try:
        user_id = str(ctx.author.id)
        
        # Check if user has a private combat channel
        if user_id in player_combat_channels:
            channel_id = player_combat_channels[user_id]
            channel = bot.get_channel(channel_id)
            
            if channel:
                # Send to private channel
                await channel.send(embed=embed)
                
                # Send redirect message if requested
                if redirect_message:
                    redirect_embed = discord.Embed(
                        description=f"Combat in progress! Check {channel.mention}",
                        color=discord.Color.blue()
                    )
                    await ctx.send(embed=redirect_embed, delete_after=5)
                return True
        
        # Fallback to current channel if no private channel
        await ctx.send(embed=embed)
        return False
        
    except Exception as e:
        print(f"Error sending combat message: {e}")
        await ctx.send(embed=embed)  # Fallback
        return False

def is_combat_command(ctx, hunter):
    """Check if this is a combat-related command"""
    combat_commands = ['hunt', 'attack', 'defend', 'flee']
    return ctx.command.name in combat_commands and hunter.get('in_battle', False)

def get_daily_kill_requirement(hunter_level):
    """Calculate daily kill requirement for mystery gates"""
    if hunter_level < 10:
        return 3
    elif hunter_level < 20:
        return 5
    elif hunter_level < 30:
        return 8
    else:
        return 10

def check_mystery_gate_access(hunter):
    """Check if hunter has access to mystery gates based on daily kills"""
    daily_kills = hunter.get('daily_kills', 0)
    required_kills = get_daily_kill_requirement(hunter.get('level', 1))
    return daily_kills >= required_kills

def update_daily_kills(hunter, kills=1):
    """Update daily kill count for mystery gate access"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Reset daily kills if it's a new day
    if hunter.get('last_kill_date') != today:
        hunter['daily_kills'] = 0
        hunter['last_kill_date'] = today
    
    hunter['daily_kills'] = hunter.get('daily_kills', 0) + kills

def check_for_active_doorway(user_id):
    """Check if user has an active doorway exploration"""
    doorway_cog = bot.get_cog('DimensionalDoorways')
    if doorway_cog and hasattr(doorway_cog, 'active_explorations'):
        return user_id in doorway_cog.active_explorations
    return False

# Load cogs function
async def load_cogs():
    """Load all cog files from the cogs directory"""
    cog_files = [
        'gates', 'inventory', 'shop', 'pvp_system', 'dungeon_raids', 
        'themes', 'daily_quests', 'weekly_quests', 'special_quests',
        'training', 'event_management', 'sololeveling_info', 'narrative_encounters'
    ]
    
    for cog_file in cog_files:
        try:
            await bot.load_extension(f'cogs.{cog_file}')
            print(f"Loaded cog: {cog_file}")
        except Exception as e:
            print(f"Failed to load cog {cog_file}: {e}")

def reset_stuck_players():
    """Reset all players' battle and exploration states"""
    hunters_data = load_hunters_data()
    
    for user_id, hunter in hunters_data.items():
        # Reset battle states
        hunter['in_battle'] = False
        hunter.pop('current_monster', None)
        hunter.pop('battle_start_time', None)
        
        # Reset exploration states
        hunter.pop('in_gate', None)
        hunter.pop('current_gate', None)
        hunter.pop('gate_progress', None)
        hunter.pop('in_dungeon', None)
        hunter.pop('current_dungeon', None)
    
    save_hunters_data(hunters_data)
    print("Reset all stuck player states")

# Cleanup duplicate channels function
async def cleanup_duplicate_channels():
    """Clean up any duplicate adventure channels that may exist"""
    try:
        for guild in bot.guilds:
            combat_category = bot.get_channel(COMBAT_CATEGORY_ID)
            if combat_category:
                # Get all channels in combat category
                channels = combat_category.channels
                user_channels = {}
                
                for channel in channels:
                    if channel.name.startswith('adventure-'):
                        # Extract username from channel name
                        username = channel.name.replace('adventure-', '').replace('-', ' ')
                        
                        if username in user_channels:
                            # Duplicate found, delete the older one
                            older_channel = user_channels[username]
                            try:
                                await older_channel.delete(reason="Cleaning up duplicate channel")
                                print(f"Deleted duplicate channel: {older_channel.name}")
                            except:
                                pass
                        
                        user_channels[username] = channel
                        
        print("Completed duplicate channel cleanup")
    except Exception as e:
        print(f"Error during channel cleanup: {e}")

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    
    # Load combat channels data
    global player_combat_channels
    player_combat_channels = load_combat_channels()
    print(f"Loaded {len(player_combat_channels)} saved combat channels")
    
    # Load all cogs
    await load_cogs()
    
    # Reset stuck players on startup
    reset_stuck_players()
    
    # Clean up any duplicate channels
    await cleanup_duplicate_channels()
    
    print("Bot is ready!")

@bot.command(name='start')
async def start(ctx):
    """Start your journey as a hunter"""
    user_id = str(ctx.author.id)
    hunters_data = load_hunters_data()
    
    if user_id in hunters_data:
        # User already exists, show their current status instead
        hunter = hunters_data[user_id]
        
        embed = discord.Embed(
            title="⚔️ Welcome Back, Hunter!",
            description=f"You are already registered in the Hunter System.\nUse `.status` to check your progress or `.hunt` to start battling!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🏷️ Current Status",
            value=f"**Level:** {hunter.get('level', 1)}\n**Rank:** {hunter.get('rank', 'E')}\n**EXP:** {hunter.get('exp', 0)}\n**Gold:** {hunter.get('gold', 0)}",
            inline=True
        )
        
        embed.add_field(
            name="📚 Quick Commands",
            value="`.status` - View detailed stats\n`.hunt` - Start hunting monsters\n`.inventory` - Check your items\n`.help` - View all commands",
            inline=True
        )
        
        await ctx.send(embed=embed)
        return
    
    # Create new hunter
    new_hunter = {
        'name': ctx.author.display_name,
        'level': 1,
        'exp': 0,
        'rank': 'E',
        'hp': 100,
        'max_hp': 100,
        'mp': 50,
        'max_mp': 50,
        'attack': 25,
        'defense': 15,
        'agility': 10,
        'intelligence': 10,
        'gold': 100,
        'inventory': [],
        'equipped': {
            'weapon': None,
            'armor': None,
            'accessory': None
        },
        'in_battle': False,
        'gates_cleared': 0,
        'dungeons_cleared': 0,
        'pvp_wins': 0,
        'pvp_losses': 0,
        'daily_kills': 0,
        'last_kill_date': datetime.now().strftime('%Y-%m-%d'),
        'creation_date': datetime.now().isoformat(),
        'last_active': datetime.now().isoformat()
    }
    
    hunters_data[user_id] = new_hunter
    save_hunters_data(hunters_data)
    
    # Send welcome message with embed
    embed = discord.Embed(
        title="🌟 Welcome to the Hunter System!",
        description=f"**{ctx.author.display_name}** has awakened as an E-Rank Hunter!\n\n*The System has detected your potential. Your journey to become the strongest hunter begins now.*",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="📊 Starting Stats",
        value=f"**Level:** 1\n**Rank:** E\n**HP:** 100/100\n**MP:** 50/50\n**Gold:** 100",
        inline=True
    )
    
    embed.add_field(
        name="⚔️ Combat Stats",
        value=f"**Attack:** 25\n**Defense:** 15\n**Agility:** 10\n**Intelligence:** 10",
        inline=True
    )
    
    embed.add_field(
        name="🎯 Next Steps",
        value="• Use `.hunt` to battle monsters\n• Use `.status` to check your progress\n• Use `.shop` to buy equipment\n• Use `.help` for all commands",
        inline=False
    )
    
    embed.set_footer(text="Tip: All activities award EXP! Complete quests, explore gates, and train to level up faster.")
    
    await ctx.send(embed=embed)

def apply_passive_regeneration(hunter):
    """Apply passive health and mana regeneration when out of combat"""
    if not hunter.get('in_battle', False):
        # Regenerate 2% HP and MP every time this is called (when checking status)
        max_hp = hunter.get('max_hp', 100)
        max_mp = hunter.get('max_mp', 50)
        
        hp_regen = max(1, int(max_hp * 0.02))
        mp_regen = max(1, int(max_mp * 0.02))
        
        hunter['hp'] = min(max_hp, hunter.get('hp', max_hp) + hp_regen)
        hunter['mp'] = min(max_mp, hunter.get('mp', max_mp) + mp_regen)

def check_if_resting(user_id):
    """Check if a player is currently resting"""
    return user_id in resting_players

def check_rest_cooldown(user_id):
    """Check if rest command is on cooldown"""
    if user_id in rest_cooldowns:
        time_passed = time.time() - rest_cooldowns[user_id]
        cooldown_time = 300  # 5 minutes in seconds
        return time_passed < cooldown_time, cooldown_time - time_passed
    return False, 0

def check_if_training(user_id):
    """Check if a player is currently training"""
    training_cog = bot.get_cog('Training')
    if training_cog and hasattr(training_cog, 'training_sessions'):
        return user_id in training_cog.training_sessions
    return False

def complete_training_session(user_id, training_cog, session):
    """Complete a training session and apply stat gains"""
    if training_cog and hasattr(training_cog, 'training_sessions'):
        del training_cog.training_sessions[user_id]

def update_hunter_equipment_stats(hunter):
    """Update hunter stats with equipment bonuses"""
    base_attack = 25 + (hunter.get('level', 1) - 1) * 3
    base_defense = 15 + (hunter.get('level', 1) - 1) * 2
    
    # Reset to base stats
    hunter['attack'] = base_attack
    hunter['defense'] = base_defense
    
    # Apply equipment bonuses
    equipped = hunter.get('equipped', {})
    
    # Weapon bonus
    weapon = equipped.get('weapon')
    if weapon and isinstance(weapon, dict):
        hunter['attack'] += weapon.get('attack_bonus', 0)
    
    # Armor bonus
    armor = equipped.get('armor')
    if armor and isinstance(armor, dict):
        hunter['defense'] += armor.get('defense_bonus', 0)
    
    # Accessory bonuses
    accessory = equipped.get('accessory')
    if accessory and isinstance(accessory, dict):
        hunter['attack'] += accessory.get('attack_bonus', 0)
        hunter['defense'] += accessory.get('defense_bonus', 0)

@bot.command(name='status')
async def status(ctx):
    """Check your hunter status"""
    user_id = str(ctx.author.id)
    hunters_data = load_hunters_data()
    
    if user_id not in hunters_data:
        embed = discord.Embed(
            title="❌ Not Registered",
            description="You need to start your journey first! Use `.start` to begin.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    hunter = hunters_data[user_id]
    
    # Apply passive regeneration
    apply_passive_regeneration(hunter)
    
    # Update equipment stats
    update_hunter_equipment_stats(hunter)
    
    # Save the updated data
    hunters_data[user_id] = hunter
    save_hunters_data(hunters_data)
    
    # Get user theme colors
    colors = get_user_theme_colors(user_id)
    
    # Create progress bar function for HP/MP/EXP
    def create_progress_bar(current, maximum, length=10):
        if maximum == 0:
            return "░" * length
        filled = int((current / maximum) * length)
        return "█" * filled + "░" * (length - filled)
    
    # Calculate next level EXP requirement
    next_level_exp = leveling_system.get_exp_requirement(hunter.get('level', 1) + 1)
    current_exp = hunter.get('exp', 0)
    exp_for_next = next_level_exp - current_exp
    
    # Create main status embed
    embed = discord.Embed(
        title=f"⚔️ Hunter Profile: {hunter['name']}",
        color=discord.Color(colors['primary'])
    )
    
    # Basic Info
    embed.add_field(
        name="📊 Basic Information",
        value=f"**Level:** {hunter.get('level', 1)}\n**Rank:** {hunter.get('rank', 'E')}\n**EXP:** {current_exp:,}\n**Gold:** {hunter.get('gold', 0):,}",
        inline=True
    )
    
    # Health and Mana with progress bars
    hp_bar = create_progress_bar(hunter.get('hp', 100), hunter.get('max_hp', 100))
    mp_bar = create_progress_bar(hunter.get('mp', 50), hunter.get('max_mp', 50))
    exp_bar = create_progress_bar(current_exp - leveling_system.get_exp_requirement(hunter.get('level', 1)), 
                                 next_level_exp - leveling_system.get_exp_requirement(hunter.get('level', 1)))
    
    embed.add_field(
        name="💚 Health & Mana",
        value=f"**HP:** {hunter.get('hp', 100)}/{hunter.get('max_hp', 100)}\n{hp_bar}\n**MP:** {hunter.get('mp', 50)}/{hunter.get('max_mp', 50)}\n{mp_bar}",
        inline=True
    )
    
    # Combat Stats
    embed.add_field(
        name="⚔️ Combat Stats",
        value=f"**Attack:** {hunter.get('attack', 25)}\n**Defense:** {hunter.get('defense', 15)}\n**Agility:** {hunter.get('agility', 10)}\n**Intelligence:** {hunter.get('intelligence', 10)}",
        inline=True
    )
    
    # Progress Info
    embed.add_field(
        name="📈 Progress",
        value=f"**EXP to Next Level:** {exp_for_next:,}\n{exp_bar}\n**Gates Cleared:** {hunter.get('gates_cleared', 0)}\n**Dungeons Cleared:** {hunter.get('dungeons_cleared', 0)}",
        inline=True
    )
    
    # Activity Status
    status_info = []
    if hunter.get('in_battle', False):
        status_info.append("⚔️ In Combat")
    if check_if_resting(user_id):
        status_info.append("😴 Resting")
    if check_if_training(user_id):
        status_info.append("🏋️ Training")
    if check_for_active_doorway(user_id):
        status_info.append("🌀 Exploring Doorway")
    
    if not status_info:
        status_info.append("🆓 Available")
    
    embed.add_field(
        name="🎯 Current Status",
        value="\n".join(status_info),
        inline=True
    )
    
    # Equipment Info
    equipped = hunter.get('equipped', {})
    equipment_info = []
    
    weapon = equipped.get('weapon')
    if weapon:
        if isinstance(weapon, dict):
            equipment_info.append(f"🗡️ **Weapon:** {weapon.get('name', 'Unknown')} (+{weapon.get('attack_bonus', 0)} ATK)")
        else:
            equipment_info.append(f"🗡️ **Weapon:** {weapon}")
    else:
        equipment_info.append("🗡️ **Weapon:** None")
    
    armor = equipped.get('armor')
    if armor:
        if isinstance(armor, dict):
            equipment_info.append(f"🛡️ **Armor:** {armor.get('name', 'Unknown')} (+{armor.get('defense_bonus', 0)} DEF)")
        else:
            equipment_info.append(f"🛡️ **Armor:** {armor}")
    else:
        equipment_info.append("🛡️ **Armor:** None")
    
    accessory = equipped.get('accessory')
    if accessory:
        if isinstance(accessory, dict):
            equipment_info.append(f"💍 **Accessory:** {accessory.get('name', 'Unknown')}")
        else:
            equipment_info.append(f"💍 **Accessory:** {accessory}")
    else:
        equipment_info.append("💍 **Accessory:** None")
    
    embed.add_field(
        name="🎒 Equipment",
        value="\n".join(equipment_info),
        inline=True
    )
    
    # Add footer with helpful tips
    embed.set_footer(text="💡 Use .rest to recover HP/MP • Use .hunt to battle monsters • Use .shop to buy equipment")
    
    # Create interactive status view
    view = StatusView(bot, user_id, colors)
    
    try:
        message = await ctx.send(embed=embed, view=view)
        view.message = message
    except Exception as e:
        # Fallback without view if there's an error
        await ctx.send(embed=embed)

@bot.command(name='rest')
async def rest(ctx):
    """Rest to fully restore health and mana (5 minute cooldown, 90 second rest period)"""
    user_id = str(ctx.author.id)
    hunters_data = load_hunters_data()
    
    if user_id not in hunters_data:
        await ctx.send("❌ You need to start your journey first! Use `.start` to begin.")
        return
    
    hunter = hunters_data[user_id]
    
    # Check if user is in battle
    if hunter.get('in_battle', False):
        await ctx.send("❌ You cannot rest while in battle!")
        return
    
    # Check if user is already resting
    if check_if_resting(user_id):
        await ctx.send("😴 You are already resting! Please wait...")
        return
    
    # Check cooldown
    on_cooldown, time_left = check_rest_cooldown(user_id)
    if on_cooldown:
        minutes = int(time_left // 60)
        seconds = int(time_left % 60)
        await ctx.send(f"⏰ Rest is on cooldown! Time remaining: {minutes}m {seconds}s")
        return
    
    # Check if already at full HP and MP
    if hunter.get('hp', 100) >= hunter.get('max_hp', 100) and hunter.get('mp', 50) >= hunter.get('max_mp', 50):
        await ctx.send("💚 You are already at full health and mana!")
        return
    
    # Start resting
    resting_players[user_id] = time.time()
    
    embed = discord.Embed(
        title="😴 Resting...",
        description=f"{ctx.author.mention} is taking a rest to recover HP and MP.",
        color=discord.Color.blue()
    )
    embed.add_field(name="⏰ Duration", value="90 seconds", inline=True)
    embed.add_field(name="🔄 Recovery", value="Full HP and MP restoration", inline=True)
    
    await ctx.send(embed=embed)
    
    # Wait for rest period
    await asyncio.sleep(90)  # 90 seconds
    
    # Remove from resting players
    resting_players.pop(user_id, None)
    
    # Restore HP and MP
    hunter['hp'] = hunter.get('max_hp', 100)
    hunter['mp'] = hunter.get('max_mp', 50)
    
    # Set cooldown
    rest_cooldowns[user_id] = time.time()
    
    # Save data
    save_hunters_data(hunters_data)
    
    # Send completion message
    complete_embed = discord.Embed(
        title="✨ Rest Complete!",
        description=f"{ctx.author.mention} has fully recovered!",
        color=discord.Color.green()
    )
    complete_embed.add_field(
        name="💚 Recovery",
        value=f"**HP:** {hunter['hp']}/{hunter['max_hp']}\n**MP:** {hunter['mp']}/{hunter['max_mp']}",
        inline=True
    )
    complete_embed.add_field(
        name="⏰ Next Rest",
        value="Available in 5 minutes",
        inline=True
    )
    
    await ctx.send(embed=complete_embed)

@bot.command(name='hunt')
async def hunt(ctx):
    """Start interactive hunting with button-based combat in a private channel"""
    user_id = str(ctx.author.id)
    hunters_data = load_hunters_data()
    
    if user_id not in hunters_data:
        await ctx.send("❌ You need to start your journey first! Use `.start` to begin.")
        return
    
    hunter = hunters_data[user_id]
    
    # Check if hunter is already in battle
    if hunter.get('in_battle', False):
        await ctx.send("⚔️ You are already in battle! Use `.attack`, `.defend`, or `.flee` to continue fighting.")
        return
    
    # Check if user is resting
    if check_if_resting(user_id):
        await ctx.send("😴 You cannot hunt while resting! Please wait for your rest to complete.")
        return
    
    # Check if user is training
    if check_if_training(user_id):
        await ctx.send("🏋️ You cannot hunt while training! Please wait for your training to complete.")
        return
    
    # Create or get private combat channel
    combat_channel = await create_private_combat_channel(ctx)
    if not combat_channel:
        await ctx.send("❌ Failed to create combat channel. Please try again.")
        return
    
    # Select monster based on hunter rank
    monster = select_random_monster(hunter.get('rank', 'E'))
    
    # Start battle
    hunter['in_battle'] = True
    hunter['current_monster'] = monster
    hunter['battle_start_time'] = time.time()
    
    # Create combat embed
    embed = discord.Embed(
        title="⚔️ Monster Encounter!",
        description=f"A wild **{monster['name']}** appears!\nPrepare for battle!",
        color=discord.Color.red()
    )
    
    embed.add_field(
        name="👹 Monster Stats",
        value=f"**HP:** {monster['hp']}/{monster['max_hp']}\n**Attack:** {monster.get('attack', 20)}\n**Defense:** {monster.get('defense', 5)}",
        inline=True
    )
    
    embed.add_field(
        name="⚔️ Your Stats", 
        value=f"**HP:** {hunter['hp']}/{hunter['max_hp']}\n**Attack:** {hunter.get('attack', 25)}\n**Defense:** {hunter.get('defense', 15)}",
        inline=True
    )
    
    embed.add_field(
        name="🎯 Choose Your Action",
        value="Use the buttons below to fight!",
        inline=False
    )
    
    # Save data
    save_hunters_data(hunters_data)
    
    # Create combat view with buttons
    view = CombatView(bot, user_id, monster)
    view.combat_channel = combat_channel
    
    # Send combat message to private channel
    message = await combat_channel.send(embed=embed, view=view)
    view.message = message
    
    # Send confirmation to original channel
    confirmation_embed = discord.Embed(
        title="🏟️ Hunt Started!",
        description=f"Battle initiated in your private combat channel: {combat_channel.mention}",
        color=discord.Color.green()
    )
    await ctx.send(embed=confirmation_embed, delete_after=10)

@bot.command(name='attack')
async def attack(ctx):
    """Attack the current monster"""
    user_id = str(ctx.author.id)
    hunters_data = load_hunters_data()
    
    if user_id not in hunters_data:
        await ctx.send("❌ You need to start your journey first! Use `.start` to begin.")
        return
    
    hunter = hunters_data[user_id]
    
    if not hunter.get('in_battle', False):
        await ctx.send("❌ You are not in battle! Use `.hunt` to start fighting monsters.")
        return
    
    # Check if this is a gate battle
    gates_cog = bot.get_cog('Gates')
    if gates_cog and hunter.get('in_gate'):
        await handle_gate_battle_attack(ctx, user_id, hunter, hunters_data)
        return
    
    # Check if this is a dungeon battle
    dungeon_cog = bot.get_cog('DungeonRaids')
    if dungeon_cog and hunter.get('in_dungeon'):
        await handle_dungeon_battle_attack(ctx, user_id, hunter, hunters_data, dungeon_cog)
        return
    
    # Check if this is an event battle
    if hunter.get('battle_type') == 'event_boss':
        await handle_event_battle_attack(ctx, user_id, hunter, hunters_data)
        return
    
    # Regular monster battle
    monster = hunter.get('current_monster')
    if not monster:
        await ctx.send("❌ No monster to fight! Use `.hunt` to start a new battle.")
        return
    
    import random
    
    # Calculate damage
    base_damage = hunter.get('attack', 25)
    damage = random.randint(int(base_damage * 0.8), int(base_damage * 1.2))
    damage = max(1, damage - monster.get('defense', 5))
    
    # Apply damage
    monster['hp'] = max(0, monster['hp'] - damage)
    
    embed = discord.Embed(title="⚔️ Attack!", color=discord.Color.red())
    embed.add_field(name="💥 Damage Dealt", value=f"{damage}", inline=True)
    embed.add_field(name="👹 Monster HP", value=f"{monster['hp']}/{monster['max_hp']}", inline=True)
    
    # Check if monster is defeated
    if monster['hp'] <= 0:
        # Monster defeated
        exp_gained = monster.get('exp_reward', 25)
        gold_gained = monster.get('gold_reward', 15)
        
        # Apply weekend EXP multiplier if active
        event_management = bot.get_cog('EventManagement')
        if event_management and event_management.is_weekend():
            exp_multiplier = event_management.get_exp_multiplier()
            exp_gained = int(exp_gained * exp_multiplier)
        
        hunter['exp'] += exp_gained
        hunter['gold'] += gold_gained
        hunter['in_battle'] = False
        hunter.pop('current_monster', None)
        
        # Update daily kills for mystery gate access
        update_daily_kills(hunter)
        
        embed.add_field(name="🎉 Victory!", value=f"You defeated the {monster['name']}!", inline=False)
        embed.add_field(name="🏆 Rewards", value=f"**EXP:** +{exp_gained}\n**Gold:** +{gold_gained}", inline=True)
        embed.color = discord.Color.green()
        
        # Check for level up
        old_level = hunter.get('level', 1)
        hunter = await award_exp(user_id, 0, hunter)  # Level up check without additional EXP
        
        if hunter.get('level', 1) > old_level:
            embed.add_field(name="📈 Level Up!", value=f"You reached level {hunter['level']}!", inline=True)
            embed.color = discord.Color.purple()
            
            # Send level up notification
            await send_level_up_notification(ctx, user_id, hunter['level'], old_level)
        
        # Update quest progress
        from daily_quest_system import update_quest_progress
        update_quest_progress(hunter, 'monsters_defeated')
        
    else:
        # Monster attacks back
        monster_damage = random.randint(int(monster.get('attack', 20) * 0.8), int(monster.get('attack', 20) * 1.2))
        monster_damage = max(1, monster_damage - hunter.get('defense', 15))
        hunter['hp'] = max(0, hunter['hp'] - monster_damage)
        
        embed.add_field(name="💥 Monster Attacks Back!", value=f"The {monster['name']} deals {monster_damage} damage!", inline=False)
        embed.add_field(name="💚 Your HP", value=f"{hunter['hp']}/{hunter['max_hp']}", inline=True)
        
        # Check if hunter is defeated
        if hunter['hp'] <= 0:
            hunter['in_battle'] = False
            hunter.pop('current_monster', None)
            hunter['hp'] = 1  # Prevent complete death
            
            embed.add_field(name="💀 Defeat!", value="You have been defeated! You barely escape with your life.", inline=False)
            embed.color = discord.Color.dark_red()
    
    # Create progress bar function
    def create_progress_bar(current, maximum, length=10):
        if maximum == 0:
            return "░" * length
        filled = int((current / maximum) * length)
        return "█" * filled + "░" * (length - filled)
    
    # Add health bars
    monster_bar = create_progress_bar(monster['hp'], monster['max_hp'])
    hunter_bar = create_progress_bar(hunter['hp'], hunter['max_hp'])
    
    embed.add_field(
        name="📊 Battle Status",
        value=f"**Monster:** {monster_bar} {monster['hp']}/{monster['max_hp']}\n**You:** {hunter_bar} {hunter['hp']}/{hunter['max_hp']}",
        inline=False
    )
    
    # Save data
    save_hunters_data(hunters_data)
    
    await send_combat_message(ctx, embed, "⚔️ Combat in progress!")

@bot.command(name='defend')
async def defend(ctx):
    """Defend against monster attack"""
    user_id = str(ctx.author.id)
    hunters_data = load_hunters_data()
    
    if user_id not in hunters_data:
        await ctx.send("❌ You need to start your journey first! Use `.start` to begin.")
        return
    
    hunter = hunters_data[user_id]
    
    if not hunter.get('in_battle', False):
        await ctx.send("❌ You are not in battle! Use `.hunt` to start fighting monsters.")
        return
    
    # Check if this is a gate battle
    gates_cog = bot.get_cog('Gates')
    if gates_cog and hunter.get('in_gate'):
        await handle_gate_battle_defend(ctx, user_id, hunter, hunters_data)
        return
    
    # Check if this is a dungeon battle
    dungeon_cog = bot.get_cog('DungeonRaids')
    if dungeon_cog and hunter.get('in_dungeon'):
        await handle_dungeon_battle_defend(ctx, user_id, hunter, hunters_data, dungeon_cog)
        return
    
    # Regular monster battle
    monster = hunter.get('current_monster')
    if not monster:
        await ctx.send("❌ No monster to fight! Use `.hunt` to start a new battle.")
        return
    
    import random
    
    # Monster attacks but damage is reduced
    monster_damage = random.randint(int(monster.get('attack', 20) * 0.5), int(monster.get('attack', 20) * 0.8))
    monster_damage = max(1, monster_damage - hunter.get('defense', 15))
    hunter['hp'] = max(0, hunter['hp'] - monster_damage)
    
    embed = discord.Embed(title="🛡️ Defend!", color=discord.Color.blue())
    embed.add_field(name="🛡️ Defense Successful!", value=f"You block most of the attack!", inline=False)
    embed.add_field(name="💥 Reduced Damage", value=f"The {monster['name']} deals only {monster_damage} damage!", inline=True)
    embed.add_field(name="💚 Your HP", value=f"{hunter['hp']}/{hunter['max_hp']}", inline=True)
    
    # Check if hunter is defeated
    if hunter['hp'] <= 0:
        hunter['in_battle'] = False
        hunter.pop('current_monster', None)
        hunter['hp'] = 1  # Prevent complete death
        
        embed.add_field(name="💀 Defeat!", value="Despite your defense, you have been defeated! You barely escape with your life.", inline=False)
        embed.color = discord.Color.dark_red()
    
    # Create progress bar function
    def create_progress_bar(current, maximum, length=10):
        if maximum == 0:
            return "░" * length
        filled = int((current / maximum) * length)
        return "█" * filled + "░" * (length - filled)
    
    # Add health bars
    monster_bar = create_progress_bar(monster['hp'], monster['max_hp'])
    hunter_bar = create_progress_bar(hunter['hp'], hunter['max_hp'])
    
    embed.add_field(
        name="📊 Battle Status",
        value=f"**Monster:** {monster_bar} {monster['hp']}/{monster['max_hp']}\n**You:** {hunter_bar} {hunter['hp']}/{hunter['max_hp']}",
        inline=False
    )
    
    # Save data
    save_hunters_data(hunters_data)
    
    await send_combat_message(ctx, embed, "🛡️ Defending in combat!")

@bot.command(name='flee')
async def flee(ctx):
    """Flee from battle"""
    user_id = str(ctx.author.id)
    hunters_data = load_hunters_data()
    
    if user_id not in hunters_data:
        await ctx.send("❌ You need to start your journey first! Use `.start` to begin.")
        return
    
    hunter = hunters_data[user_id]
    
    if not hunter.get('in_battle', False):
        await ctx.send("❌ You are not in battle!")
        return
    
    # Check if this is a gate battle
    gates_cog = bot.get_cog('Gates')
    if gates_cog and hunter.get('in_gate'):
        await handle_gate_battle_flee(ctx, user_id, hunter, hunters_data)
        return
    
    # Check if this is a dungeon battle
    dungeon_cog = bot.get_cog('DungeonRaids')
    if dungeon_cog and hunter.get('in_dungeon'):
        await handle_dungeon_battle_flee(ctx, user_id, hunter, hunters_data, dungeon_cog)
        return
    
    # Regular monster battle
    import random
    
    # 70% chance to successfully flee
    if random.random() < 0.7:
        hunter['in_battle'] = False
        hunter.pop('current_monster', None)
        
        embed = discord.Embed(
            title="🏃 Fled Successfully!",
            description="You managed to escape from the battle!",
            color=discord.Color.yellow()
        )
    else:
        # Failed to flee, monster gets a free attack
        monster = hunter.get('current_monster', {})
        monster_damage = random.randint(int(monster.get('attack', 20) * 0.8), int(monster.get('attack', 20) * 1.2))
        monster_damage = max(1, monster_damage - hunter.get('defense', 15))
        hunter['hp'] = max(0, hunter['hp'] - monster_damage)
        
        embed = discord.Embed(
            title="🏃 Failed to Flee!",
            description=f"You couldn't escape! The {monster.get('name', 'monster')} attacks you as you try to run!",
            color=discord.Color.orange()
        )
        embed.add_field(name="💥 Damage Taken", value=f"{monster_damage}", inline=True)
        embed.add_field(name="💚 Your HP", value=f"{hunter['hp']}/{hunter['max_hp']}", inline=True)
        
        # Check if hunter is defeated
        if hunter['hp'] <= 0:
            hunter['in_battle'] = False
            hunter.pop('current_monster', None)
            hunter['hp'] = 1  # Prevent complete death
            
            embed.add_field(name="💀 Defeat!", value="The attack knocks you unconscious! You barely escape with your life.", inline=False)
            embed.color = discord.Color.dark_red()
    
    # Save data
    save_hunters_data(hunters_data)
    
    await send_combat_message(ctx, embed, "🏃 Fleeing from combat!")

@bot.command(name='claim', aliases=['claim_rewards'])
async def claim_quest_rewards(ctx):
    """Claim rewards for completed quests"""
    user_id = str(ctx.author.id)
    hunters_data = load_hunters_data()
    
    if user_id not in hunters_data:
        await ctx.send("❌ You need to start your journey first! Use `.start` to begin.")
        return
    
    hunter = hunters_data[user_id]
    
    # Get quest cogs
    daily_cog = bot.get_cog('DailyQuests')
    weekly_cog = bot.get_cog('WeeklyQuests')
    special_cog = bot.get_cog('SpecialQuests')
    
    claimed_anything = False
    total_exp = 0
    total_gold = 0
    rewards_summary = []
    
    # Check daily quests
    if daily_cog:
        claimed_daily = await daily_cog.claim_daily_rewards(ctx, user_id)
        if claimed_daily:
            claimed_anything = True
            if 'exp' in claimed_daily:
                total_exp += claimed_daily['exp']
            if 'gold' in claimed_daily:
                total_gold += claimed_daily['gold']
            rewards_summary.append("Daily Quest rewards")
    
    # Check weekly quests
    if weekly_cog:
        claimed_weekly = await weekly_cog.claim_weekly_rewards(ctx, user_id)
        if claimed_weekly:
            claimed_anything = True
            if 'exp' in claimed_weekly:
                total_exp += claimed_weekly['exp']
            if 'gold' in claimed_weekly:
                total_gold += claimed_weekly['gold']
            rewards_summary.append("Weekly Quest rewards")
    
    # Check special quests
    if special_cog:
        claimed_special = await special_cog.claim_special_rewards(ctx, user_id)
        if claimed_special:
            claimed_anything = True
            if 'exp' in claimed_special:
                total_exp += claimed_special['exp']
            if 'gold' in claimed_special:
                total_gold += claimed_special['gold']
            rewards_summary.append("Special Quest rewards")
    
    if not claimed_anything:
        embed = discord.Embed(
            title="📋 No Rewards Available",
            description="You don't have any completed quests to claim rewards from.",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="💡 Tip",
            value="Complete daily, weekly, or special quests to earn rewards!",
            inline=False
        )
        await ctx.send(embed=embed)
        return
    
    # Create summary embed
    embed = discord.Embed(
        title="🎉 Rewards Claimed!",
        description="You have successfully claimed your quest rewards!",
        color=discord.Color.green()
    )
    
    if total_exp > 0 or total_gold > 0:
        embed.add_field(
            name="🏆 Total Rewards",
            value=f"**EXP:** +{total_exp}\n**Gold:** +{total_gold}",
            inline=True
        )
    
    embed.add_field(
        name="📋 Sources",
        value="\n".join(rewards_summary),
        inline=True
    )
    
    await ctx.send(embed=embed)

@bot.command(name='reset_stuck')
@commands.has_permissions(administrator=True)
async def reset_stuck_command(ctx):
    """Admin command to reset all stuck player states"""
    reset_stuck_players()
    await ctx.send("✅ Reset all stuck player states successfully!")

@bot.command(name='my_adventure', aliases=['my_channel', 'combat_channel'])
async def my_adventure(ctx):
    """Show your personal adventure channel"""
    user_id = str(ctx.author.id)
    
    # Check if user has a combat channel
    if user_id in player_combat_channels:
        channel_id = player_combat_channels[user_id]
        channel = bot.get_channel(channel_id)
        
        if channel:
            embed = discord.Embed(
                title="🏟️ Your Adventure Channel",
                description=f"Your private combat channel: {channel.mention}",
                color=discord.Color.green()
            )
            embed.add_field(
                name="🎯 Purpose",
                value="This is your private channel for hunting and combat activities.",
                inline=False
            )
            await ctx.send(embed=embed)
        else:
            # Channel no longer exists, remove from tracking
            del player_combat_channels[user_id]
            save_combat_channels()
            await ctx.send("❌ Your adventure channel no longer exists. Use `.hunt` to create a new one!")
    else:
        await ctx.send("❌ You don't have an adventure channel yet. Use `.hunt` to create one!")

# Admin commands
@bot.command(name='set_jinwoo')
@commands.has_permissions(administrator=True)
async def set_jinwoo(ctx, target: discord.Member = None):
    """Admin command to set someone as Sung Jinwoo"""
    if not target:
        target = ctx.author
    
    user_id = str(target.id)
    hunters_data = load_hunters_data()
    
    # Create Sung Jinwoo stats
    jinwoo_stats = {
        'name': 'Sung Jin-Woo',
        'level': 100,
        'exp': 999999999,
        'rank': 'Monarch',
        'hp': 10000,
        'max_hp': 10000,
        'mp': 5000,
        'max_mp': 5000,
        'attack': 1000,
        'defense': 800,
        'agility': 900,
        'intelligence': 750,
        'gold': 1000000,
        'inventory': [],
        'equipped': {
            'weapon': {
                'name': 'Demon King\'s Longsword',
                'type': 'weapon',
                'attack_bonus': 500,
                'rarity': 'legendary'
            },
            'armor': {
                'name': 'Shadow Monarch\'s Armor',
                'type': 'armor',
                'defense_bonus': 400,
                'rarity': 'legendary'
            },
            'accessory': {
                'name': 'System\'s Ring',
                'type': 'accessory',
                'special_effects': ['Double EXP', 'Unlimited MP'],
                'rarity': 'mythic'
            }
        },
        'in_battle': False,
        'gates_cleared': 999,
        'dungeons_cleared': 999,
        'pvp_wins': 999,
        'pvp_losses': 0,
        'daily_kills': 999,
        'last_kill_date': datetime.now().strftime('%Y-%m-%d'),
        'creation_date': datetime.now().isoformat(),
        'last_active': datetime.now().isoformat(),
        'special_title': 'Shadow Monarch'
    }
    
    hunters_data[user_id] = jinwoo_stats
    save_hunters_data(hunters_data)
    
    embed = discord.Embed(
        title="👑 Sung Jin-Woo Awakened!",
        description=f"{target.mention} has been transformed into the Shadow Monarch!",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="📊 Monarch Stats",
        value=f"**Level:** 100\n**Rank:** Monarch\n**HP:** 10,000\n**Attack:** 1,000\n**Defense:** 800",
        inline=True
    )
    
    embed.add_field(
        name="👑 Special Status",
        value="• Shadow Monarch Title\n• Legendary Equipment\n• Unlimited Resources\n• Max Level Achieved",
        inline=True
    )
    
    await ctx.send(embed=embed)

@bot.command(name='set_level')
@commands.has_permissions(administrator=True)
async def set_level(ctx, user_id: str, level: int):
    """Admin command to set a specific user's level"""
    hunters_data = load_hunters_data()
    
    if user_id not in hunters_data:
        await ctx.send(f"❌ User ID {user_id} not found in hunter database.")
        return
    
    if level < 1 or level > 100:
        await ctx.send("❌ Level must be between 1 and 100.")
        return
    
    hunter = hunters_data[user_id]
    old_level = hunter.get('level', 1)
    
    # Set the new level
    hunter['level'] = level
    
    # Recalculate stats based on new level
    hunter['max_hp'] = 100 + (level - 1) * 20
    hunter['max_mp'] = 50 + (level - 1) * 10
    hunter['hp'] = hunter['max_hp']  # Full heal
    hunter['mp'] = hunter['max_mp']  # Full mana
    
    # Set EXP to the minimum required for this level
    hunter['exp'] = leveling_system.get_exp_requirement(level)
    
    # Update combat stats
    hunter['attack'] = 25 + (level - 1) * 3
    hunter['defense'] = 15 + (level - 1) * 2
    hunter['agility'] = 10 + (level - 1) * 2
    hunter['intelligence'] = 10 + (level - 1) * 2
    
    # Update rank based on level
    if level >= 100:
        hunter['rank'] = 'Monarch'
    elif level >= 90:
        hunter['rank'] = 'National Level'
    elif level >= 70:
        hunter['rank'] = 'S'
    elif level >= 50:
        hunter['rank'] = 'A'
    elif level >= 30:
        hunter['rank'] = 'B'
    elif level >= 15:
        hunter['rank'] = 'C'
    elif level >= 8:
        hunter['rank'] = 'D'
    else:
        hunter['rank'] = 'E'
    
    save_hunters_data(hunters_data)
    
    # Get the user object for display
    user = bot.get_user(int(user_id))
    user_name = user.display_name if user else f"User {user_id}"
    
    embed = discord.Embed(
        title="📊 Level Updated!",
        description=f"Successfully updated {user_name}'s level.",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="📈 Level Change",
        value=f"**Old Level:** {old_level}\n**New Level:** {level}",
        inline=True
    )
    
    embed.add_field(
        name="🏷️ New Rank",
        value=hunter['rank'],
        inline=True
    )
    
    embed.add_field(
        name="📊 Updated Stats",
        value=f"**HP:** {hunter['hp']}/{hunter['max_hp']}\n**MP:** {hunter['mp']}/{hunter['max_mp']}\n**Attack:** {hunter['attack']}\n**Defense:** {hunter['defense']}",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='reset_levels')
@commands.has_permissions(administrator=True)
async def reset_levels(ctx):
    """Admin command to reset all players to level 1"""
    hunters_data = load_hunters_data()
    
    count = 0
    for user_id, hunter in hunters_data.items():
        if hunter.get('level', 1) > 1:
            hunter['level'] = 1
            hunter['exp'] = 0
            hunter['rank'] = 'E'
            hunter['hp'] = 100
            hunter['max_hp'] = 100
            hunter['mp'] = 50
            hunter['max_mp'] = 50
            hunter['attack'] = 25
            hunter['defense'] = 15
            hunter['agility'] = 10
            hunter['intelligence'] = 10
            count += 1
    
    save_hunters_data(hunters_data)
    
    embed = discord.Embed(
        title="🔄 Mass Level Reset Complete",
        description=f"Reset {count} hunters back to level 1.",
        color=discord.Color.orange()
    )
    
    await ctx.send(embed=embed)

@bot.command(name='migrate_exp')
@commands.has_permissions(administrator=True)
async def migrate_exp_system(ctx):
    """Admin command to migrate player data to new EXP system"""
    hunters_data = load_hunters_data()
    
    migrated_count = 0
    for user_id, hunter in hunters_data.items():
        # Only migrate if not already using new system
        if not hunter.get('migrated_exp_system', False):
            level = hunter.get('level', 1)
            
            # Set EXP based on current level using new system
            hunter['exp'] = leveling_system.get_exp_requirement(level)
            
            # Mark as migrated
            hunter['migrated_exp_system'] = True
            
            migrated_count += 1
    
    save_hunters_data(hunters_data)
    
    embed = discord.Embed(
        title="🔄 EXP System Migration Complete",
        description=f"Migrated {migrated_count} hunters to the new EXP system.",
        color=discord.Color.green()
    )
    
    await ctx.send(embed=embed)

@bot.command(name='exp_info', aliases=['leveling', 'level_guide'])
async def exp_info(ctx):
    """Display detailed leveling system information"""
    embed = discord.Embed(
        title="📊 Solo Leveling EXP System Guide",
        description="*The System's authentic progression mechanics*",
        color=discord.Color.purple()
    )
    
    # EXP requirements by level ranges
    embed.add_field(
        name="📈 EXP Requirements by Level",
        value=(
            "**Levels 1-10:** 100-1,000 EXP (increments of 100)\n"
            "**Levels 11-20:** 1,200-3,000 EXP (increments of 200)\n"
            "**Levels 21-30:** 3,500-8,000 EXP (increments of 500)\n"
            "**Levels 31-40:** 9,000-18,000 EXP (increments of 1,000)\n"
            "**Levels 41-50:** 20,000-38,000 EXP (increments of 2,000)\n"
            "**Levels 51-60:** 42,000-78,000 EXP (increments of 4,000)\n"
            "**Levels 61-80:** 85,000-239,000 EXP (increments of 7,000-11,000)\n"
            "**Levels 81-100:** 255,000-795,000 EXP (steep increases)"
        ),
        inline=False
    )
    
    # Rank progression
    embed.add_field(
        name="🏷️ Hunter Rank Progression",
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
        value="```\n.gates     → Dimensional gates\n.dungeons  → Raid dungeons\n.enter_gate <n>\n.raid <n>```",
        inline=False
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
    
    return True

@bot.command(name='rank', aliases=['check_rank'])
async def check_rank(ctx):
    """Check your hunter rank and progression"""
    user_id = str(ctx.author.id)
    hunters_data = load_hunters_data()
    
    if user_id not in hunters_data:
        await ctx.send("❌ You need to start your journey first! Use `.start` to begin.")
        return
    
    hunter = hunters_data[user_id]
    current_rank = hunter.get('rank', 'E')
    requirements = get_rank_requirements()
    
    embed = discord.Embed(
        title=f"🏷️ Rank Status: {current_rank}",
        color=discord.Color.blue()
    )
    
    # Current rank info
    embed.add_field(
        name="📊 Current Rank",
        value=f"**{current_rank} Rank Hunter**\nLevel: {hunter.get('level', 1)}",
        inline=True
    )
    
    # Check if eligible for rank up
    if check_rank_up(hunter):
        next_rank = requirements[current_rank].get('next_rank')
        embed.add_field(
            name="✅ Rank Up Available!",
            value=f"You can advance to **{next_rank}** rank!\nContact an admin or complete the rank assessment.",
            inline=True
        )
        embed.color = discord.Color.green()
    elif current_rank in requirements and requirements[current_rank].get('next_rank'):
        # Show requirements for next rank
        next_rank = requirements[current_rank]['next_rank']
        next_req = requirements.get(next_rank, {})
        
        req_text = []
        if next_req.get('level'):
            req_text.append(f"Level {next_req['level']} ({hunter.get('level', 1)}/{next_req['level']})")
        if next_req.get('gates_cleared'):
            req_text.append(f"Gates: {hunter.get('gates_cleared', 0)}/{next_req['gates_cleared']}")
        if next_req.get('dungeons_cleared'):
            req_text.append(f"Dungeons: {hunter.get('dungeons_cleared', 0)}/{next_req['dungeons_cleared']}")
        if next_req.get('pvp_wins'):
            req_text.append(f"PvP Wins: {hunter.get('pvp_wins', 0)}/{next_req['pvp_wins']}")
        
        embed.add_field(
            name=f"🎯 Next Rank: {next_rank}",
            value="\n".join(req_text) if req_text else "Requirements not specified",
            inline=True
        )
    else:
        embed.add_field(
            name="👑 Max Rank Achieved",
            value="You have reached the highest hunter rank!",
            inline=True
        )
    
    # Progress stats
    embed.add_field(
        name="📈 Your Progress",
        value=f"**Gates Cleared:** {hunter.get('gates_cleared', 0)}\n**Dungeons Cleared:** {hunter.get('dungeons_cleared', 0)}\n**PvP Wins:** {hunter.get('pvp_wins', 0)}",
        inline=False
    )
    
    await ctx.send(embed=embed)

# Gate battle handlers
async def handle_gate_battle_attack(ctx, user_id, hunter, hunters_data):
    """Handle attack command for gate battles"""
    gates_cog = bot.get_cog('Gates')
    if not gates_cog:
        await ctx.send("❌ Gates system not available")
        return
    
    gate_data = hunter.get('current_gate')
    if not gate_data:
        await ctx.send("❌ No active gate battle")
        return
    
    import random
    
    # Calculate damage
    base_damage = hunter.get('attack', 25)
    damage = random.randint(int(base_damage * 0.8), int(base_damage * 1.2))
    damage = max(1, damage - gate_data.get('defense', 10))
    
    # Apply damage
    gate_data['hp'] = max(0, gate_data['hp'] - damage)
    
    embed = discord.Embed(title="⚔️ Gate Battle - Attack!", color=discord.Color.red())
    embed.add_field(name="💥 Damage Dealt", value=f"{damage}", inline=True)
    embed.add_field(name="🏰 Gate Boss HP", value=f"{gate_data['hp']}/{gate_data['max_hp']}", inline=True)
    
    # Check if boss is defeated
    if gate_data['hp'] <= 0:
        # Gate cleared
        exp_gained = gate_data.get('exp_reward', 100)
        gold_gained = gate_data.get('gold_reward', 50)
        
        # Apply weekend EXP multiplier if active
        event_management = bot.get_cog('EventManagement')
        if event_management and event_management.is_weekend():
            exp_multiplier = event_management.get_exp_multiplier()
            exp_gained = int(exp_gained * exp_multiplier)
        
        hunter['exp'] += exp_gained
        hunter['gold'] += gold_gained
        hunter['gates_cleared'] += 1
        
        # Complete gate exploration
        if hasattr(gates_cog, 'complete_gate_exploration'):
            await gates_cog.complete_gate_exploration(user_id)
        
        embed.add_field(name="🎉 Gate Cleared!", value=f"You have defeated the gate boss!", inline=False)
        embed.add_field(name="🏆 Rewards", value=f"**EXP:** +{exp_gained}\n**Gold:** +{gold_gained}", inline=True)
        embed.color = discord.Color.green()
        
    else:
        # Boss attacks back
        boss_damage = random.randint(int(gate_data.get('attack', 30) * 0.8), int(gate_data.get('attack', 30) * 1.2))
        boss_damage = max(1, boss_damage - hunter.get('defense', 15))
        hunter['hp'] = max(0, hunter['hp'] - boss_damage)
        
        embed.add_field(name="💥 Boss Counter-Attack!", value=f"The gate boss deals {boss_damage} damage!", inline=False)
        embed.add_field(name="💚 Your HP", value=f"{hunter['hp']}/{hunter['max_hp']}", inline=True)
        
        # Check if hunter is defeated
        if hunter['hp'] <= 0:
            # Complete gate exploration with failure
            if hasattr(gates_cog, 'complete_gate_exploration'):
                await gates_cog.complete_gate_exploration(user_id)
            
            hunter['hp'] = 1  # Prevent complete death
            embed.add_field(name="💀 Defeat!", value="You have been defeated by the gate boss!", inline=False)
            embed.color = discord.Color.dark_red()
    
    # Create progress bar function
    def create_progress_bar(current, maximum, length=10):
        if maximum == 0:
            return "░" * length
        filled = int((current / maximum) * length)
        return "█" * filled + "░" * (length - filled)
    
    # Add health bars
    boss_bar = create_progress_bar(gate_data['hp'], gate_data['max_hp'])
    hunter_bar = create_progress_bar(hunter['hp'], hunter['max_hp'])
    
    embed.add_field(
        name="📊 Battle Status",
        value=f"**Boss:** {boss_bar} {gate_data['hp']}/{gate_data['max_hp']}\n**You:** {hunter_bar} {hunter['hp']}/{hunter['max_hp']}",
        inline=False
    )
    
    # Save data
    save_hunters_data(hunters_data)
    await ctx.send(embed=embed)

async def handle_dungeon_battle_attack(ctx, user_id, hunter, hunters_data, dungeon_cog):
    """Handle attack command for dungeon battles"""
    dungeon_data = hunter.get('current_dungeon')
    if not dungeon_data:
        await ctx.send("❌ No active dungeon battle")
        return
    
    import random
    
    # Calculate damage
    base_damage = hunter.get('attack', 25)
    damage = random.randint(int(base_damage * 0.8), int(base_damage * 1.2))
    damage = max(1, damage - dungeon_data.get('defense', 15))
    
    # Apply damage
    dungeon_data['hp'] = max(0, dungeon_data['hp'] - damage)
    
    embed = discord.Embed(title="⚔️ Dungeon Battle - Attack!", color=discord.Color.red())
    embed.add_field(name="💥 Damage Dealt", value=f"{damage}", inline=True)
    embed.add_field(name="🏰 Dungeon Boss HP", value=f"{dungeon_data['hp']}/{dungeon_data['max_hp']}", inline=True)
    
    # Check if boss is defeated
    if dungeon_data['hp'] <= 0:
        # Dungeon cleared
        exp_gained = dungeon_data.get('exp_reward', 150)
        gold_gained = dungeon_data.get('gold_reward', 75)
        
        # Apply weekend EXP multiplier if active
        event_management = bot.get_cog('EventManagement')
        if event_management and event_management.is_weekend():
            exp_multiplier = event_management.get_exp_multiplier()
            exp_gained = int(exp_gained * exp_multiplier)
        
        hunter['exp'] += exp_gained
        hunter['gold'] += gold_gained
        hunter['dungeons_cleared'] += 1
        
        # Complete dungeon exploration
        if hasattr(dungeon_cog, 'complete_dungeon_exploration'):
            await dungeon_cog.complete_dungeon_exploration(user_id)
        
        embed.add_field(name="🎉 Dungeon Cleared!", value=f"You have defeated the dungeon boss!", inline=False)
        embed.add_field(name="🏆 Rewards", value=f"**EXP:** +{exp_gained}\n**Gold:** +{gold_gained}", inline=True)
        embed.color = discord.Color.green()
        
    else:
        # Boss attacks back
        boss_damage = random.randint(int(dungeon_data.get('attack', 40) * 0.8), int(dungeon_data.get('attack', 40) * 1.2))
        boss_damage = max(1, boss_damage - hunter.get('defense', 15))
        hunter['hp'] = max(0, hunter['hp'] - boss_damage)
        
        embed.add_field(name="💥 Boss Counter-Attack!", value=f"The dungeon boss deals {boss_damage} damage!", inline=False)
        embed.add_field(name="💚 Your HP", value=f"{hunter['hp']}/{hunter['max_hp']}", inline=True)
        
        # Check if hunter is defeated
        if hunter['hp'] <= 0:
            # Complete dungeon exploration with failure
            if hasattr(dungeon_cog, 'complete_dungeon_exploration'):
                await dungeon_cog.complete_dungeon_exploration(user_id)
            
            hunter['hp'] = 1  # Prevent complete death
            embed.add_field(name="💀 Defeat!", value="You have been defeated by the dungeon boss!", inline=False)
            embed.color = discord.Color.dark_red()
    
    # Create progress bar function
    def create_progress_bar(current, maximum, length=10):
        if maximum == 0:
            return "░" * length
        filled = int((current / maximum) * length)
        return "█" * filled + "░" * (length - filled)
    
    # Add health bars
    boss_bar = create_progress_bar(dungeon_data['hp'], dungeon_data['max_hp'])
    hunter_bar = create_progress_bar(hunter['hp'], hunter['max_hp'])
    
    embed.add_field(
        name="📊 Battle Status",
        value=f"**Boss:** {boss_bar} {dungeon_data['hp']}/{dungeon_data['max_hp']}\n**You:** {hunter_bar} {hunter['hp']}/{hunter['max_hp']}",
        inline=False
    )
    
    # Save data
    save_hunters_data(hunters_data)
    await ctx.send(embed=embed)

async def handle_gate_battle_defend(ctx, user_id, hunter, hunters_data):
    """Handle defend command for gate battles"""
    gate_data = hunter.get('current_gate')
    if not gate_data:
        await ctx.send("❌ No active gate battle")
        return
    
    import random
    
    # Boss attacks but damage is reduced
    boss_damage = random.randint(int(gate_data.get('attack', 30) * 0.5), int(gate_data.get('attack', 30) * 0.8))
    boss_damage = max(1, boss_damage - hunter.get('defense', 15))
    hunter['hp'] = max(0, hunter['hp'] - boss_damage)
    
    embed = discord.Embed(title="🛡️ Gate Battle - Defend!", color=discord.Color.blue())
    embed.add_field(name="🛡️ Defense Successful!", value=f"You block most of the gate boss attack!", inline=False)
    embed.add_field(name="💥 Reduced Damage", value=f"The gate boss deals only {boss_damage} damage!", inline=True)
    embed.add_field(name="💚 Your HP", value=f"{hunter['hp']}/{hunter['max_hp']}", inline=True)
    
    # Check if hunter is defeated
    if hunter['hp'] <= 0:
        gates_cog = bot.get_cog('Gates')
        if gates_cog and hasattr(gates_cog, 'complete_gate_exploration'):
            await gates_cog.complete_gate_exploration(user_id)
        
        hunter['hp'] = 1  # Prevent complete death
        embed.add_field(name="💀 Defeat!", value="Despite your defense, you have been defeated by the gate boss!", inline=False)
        embed.color = discord.Color.dark_red()
    
    # Create progress bar function
    def create_progress_bar(current, maximum, length=10):
        if maximum == 0:
            return "░" * length
        filled = int((current / maximum) * length)
        return "█" * filled + "░" * (length - filled)
    
    # Add health bars
    boss_bar = create_progress_bar(gate_data['hp'], gate_data['max_hp'])
    hunter_bar = create_progress_bar(hunter['hp'], hunter['max_hp'])
    
    embed.add_field(
        name="📊 Battle Status",
        value=f"**Boss:** {boss_bar} {gate_data['hp']}/{gate_data['max_hp']}\n**You:** {hunter_bar} {hunter['hp']}/{hunter['max_hp']}",
        inline=False
    )
    
    # Save data
    save_hunters_data(hunters_data)
    await ctx.send(embed=embed)

async def handle_dungeon_battle_defend(ctx, user_id, hunter, hunters_data, dungeon_cog):
    """Handle defend command for dungeon battles"""
    dungeon_data = hunter.get('current_dungeon')
    if not dungeon_data:
        await ctx.send("❌ No active dungeon battle")
        return
    
    import random
    
    # Boss attacks but damage is reduced
    boss_damage = random.randint(int(dungeon_data.get('attack', 40) * 0.5), int(dungeon_data.get('attack', 40) * 0.8))
    boss_damage = max(1, boss_damage - hunter.get('defense', 15))
    hunter['hp'] = max(0, hunter['hp'] - boss_damage)
    
    embed = discord.Embed(title="🛡️ Dungeon Battle - Defend!", color=discord.Color.blue())
    embed.add_field(name="🛡️ Defense Successful!", value=f"You block most of the dungeon boss attack!", inline=False)
    embed.add_field(name="💥 Reduced Damage", value=f"The dungeon boss deals only {boss_damage} damage!", inline=True)
    embed.add_field(name="💚 Your HP", value=f"{hunter['hp']}/{hunter['max_hp']}", inline=True)
    
    # Check if hunter is defeated
    if hunter['hp'] <= 0:
        if hasattr(dungeon_cog, 'complete_dungeon_exploration'):
            await dungeon_cog.complete_dungeon_exploration(user_id)
        
        hunter['hp'] = 1  # Prevent complete death
        embed.add_field(name="💀 Defeat!", value="Despite your defense, you have been defeated by the dungeon boss!", inline=False)
        embed.color = discord.Color.dark_red()
    
    # Create progress bar function
    def create_progress_bar(current, maximum, length=10):
        if maximum == 0:
            return "░" * length
        filled = int((current / maximum) * length)
        return "█" * filled + "░" * (length - filled)
    
    # Add health bars
    boss_bar = create_progress_bar(dungeon_data['hp'], dungeon_data['max_hp'])
    hunter_bar = create_progress_bar(hunter['hp'], hunter['max_hp'])
    
    embed.add_field(
        name="📊 Battle Status",
        value=f"**Boss:** {boss_bar} {dungeon_data['hp']}/{dungeon_data['max_hp']}\n**You:** {hunter_bar} {hunter['hp']}/{hunter['max_hp']}",
        inline=False
    )
    
    # Save data
    save_hunters_data(hunters_data)
    await ctx.send(embed=embed)

async def handle_gate_battle_flee(ctx, user_id, hunter, hunters_data):
    """Handle flee command for gate battles"""
    import random
    
    # 70% chance to successfully flee
    if random.random() < 0.7:
        gates_cog = bot.get_cog('Gates')
        if gates_cog and hasattr(gates_cog, 'complete_gate_exploration'):
            await gates_cog.complete_gate_exploration(user_id)
        
        embed = discord.Embed(
            title="🏃 Fled from Gate!",
            description="You managed to escape from the gate battle!",
            color=discord.Color.yellow()
        )
    else:
        # Failed to flee, gate boss gets a free attack
        gate_data = hunter.get('current_gate', {})
        boss_damage = random.randint(int(gate_data.get('attack', 30) * 0.8), int(gate_data.get('attack', 30) * 1.2))
        boss_damage = max(1, boss_damage - hunter.get('defense', 15))
        hunter['hp'] = max(0, hunter['hp'] - boss_damage)
        
        embed = discord.Embed(
            title="🏃 Failed to Flee!",
            description=f"You couldn't escape! The gate boss attacks you as you try to run!",
            color=discord.Color.orange()
        )
        embed.add_field(name="💥 Damage Taken", value=f"{boss_damage}", inline=True)
        embed.add_field(name="💚 Your HP", value=f"{hunter['hp']}/{hunter['max_hp']}", inline=True)
        
        # Check if hunter is defeated
        if hunter['hp'] <= 0:
            gates_cog = bot.get_cog('Gates')
            if gates_cog and hasattr(gates_cog, 'complete_gate_exploration'):
                await gates_cog.complete_gate_exploration(user_id)
            
            hunter['hp'] = 1  # Prevent complete death
            embed.add_field(name="💀 Defeat!", value="The attack knocks you unconscious!", inline=False)
            embed.color = discord.Color.dark_red()
    
    # Save data
    save_hunters_data(hunters_data)
    await ctx.send(embed=embed)

async def handle_dungeon_battle_flee(ctx, user_id, hunter, hunters_data, dungeon_cog):
    """Handle flee command for dungeon battles"""
    import random
    
    # 70% chance to successfully flee
    if random.random() < 0.7:
        if hasattr(dungeon_cog, 'complete_dungeon_exploration'):
            await dungeon_cog.complete_dungeon_exploration(user_id)
        
        embed = discord.Embed(
            title="🏃 Fled from Dungeon!",
            description="You managed to escape from the dungeon battle!",
            color=discord.Color.yellow()
        )
    else:
        # Failed to flee, dungeon boss gets a free attack
        dungeon_data = hunter.get('current_dungeon', {})
        boss_damage = random.randint(int(dungeon_data.get('attack', 40) * 0.8), int(dungeon_data.get('attack', 40) * 1.2))
        boss_damage = max(1, boss_damage - hunter.get('defense', 15))
        hunter['hp'] = max(0, hunter['hp'] - boss_damage)
        
        embed = discord.Embed(
            title="🏃 Failed to Flee!",
            description=f"You couldn't escape! The dungeon boss attacks you as you try to run!",
            color=discord.Color.orange()
        )
        embed.add_field(name="💥 Damage Taken", value=f"{boss_damage}", inline=True)
        embed.add_field(name="💚 Your HP", value=f"{hunter['hp']}/{hunter['max_hp']}", inline=True)
        
        # Check if hunter is defeated
        if hunter['hp'] <= 0:
            if hasattr(dungeon_cog, 'complete_dungeon_exploration'):
                await dungeon_cog.complete_dungeon_exploration(user_id)
            
            hunter['hp'] = 1  # Prevent complete death
            embed.add_field(name="💀 Defeat!", value="The attack knocks you unconscious!", inline=False)
            embed.color = discord.Color.dark_red()
    
    # Save data
    save_hunters_data(hunters_data)
    await ctx.send(embed=embed)

async def handle_event_battle_attack(ctx, user_id, hunter, hunters_data):
    """Handle attack command for event battles"""
    event_management = bot.get_cog('EventManagement')
    if not event_management:
        await ctx.send("❌ Event system not available")
        return
    
    # This would be handled by the event system
    await ctx.send("⚔️ Event battle attack! Check your event channel for combat.")

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `.help {ctx.command}` for usage info.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument provided. Use `.help {ctx.command}` for usage info.")
    else:
        # Log unexpected errors
        print(f"Unexpected error in command {ctx.command}: {error}")
        await ctx.send("❌ An unexpected error occurred. Please try again later.")

# Main function to run the bot
async def main():
    async with bot:
        await bot.start(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    asyncio.run(main())