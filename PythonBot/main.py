import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv
import asyncio
from discord.ui import View, Button, Select
from typing import Optional

# Load environment variables
load_dotenv()

# Bot configuration
COMMAND_PREFIX = '#'
intents = discord.Intents.all()  # We need all intents for full functionality

# Remove default help command before creating the bot instance
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)

# Load or create hunters data
def load_hunters_data():
    try:
        with open('hunters_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_hunters_data(data):
    with open('hunters_data.json', 'w') as f:
        json.dump(data, f, indent=4)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(embed=discord.Embed(
            title="Command Not Found",
            description="Use #help to see available commands",
            color=discord.Color.red()
        ))
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=discord.Embed(
            title="Permission Denied",
            description="You don't have permission to use this command",
            color=discord.Color.red()
        ))
    else:
        await ctx.send(embed=discord.Embed(
            title="Error",
            description=str(error),
            color=discord.Color.red()
        ))

async def load_cogs():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Loaded cog: {filename[:-3]}')
            except Exception as e:
                print(f'Failed to load cog {filename}: {str(e)}')

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    await load_cogs()
    await bot.change_presence(activity=discord.Game(name="#help | Solo Leveling RPG"))
    print('Bot is ready!')

    # Create necessary data files if they don't exist
    if not os.path.exists('hunters_data.json'):
        save_hunters_data({})

class HelpView(View):
    def __init__(self):
        super().__init__(timeout=60)
        # Create category selection dropdown
        self.add_item(Select(
            placeholder="Select a category",
            options=[
                discord.SelectOption(label="Gates", description="Gate and dungeon commands", emoji="🌀"),
                discord.SelectOption(label="Combat", description="Battle system commands", emoji="⚔️"),
                discord.SelectOption(label="Party", description="Party and guild commands", emoji="👥"),
                discord.SelectOption(label="System", description="Basic commands", emoji="⚙️"),
                discord.SelectOption(label="Arena", description="PvP commands", emoji="🏆")
            ],
            custom_id="help_category_select"
        ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

@bot.command(name='help')
async def help_command(ctx):
    """Show all available commands"""
    embed = discord.Embed(
        title="Solo Leveling RPG Help",
        description="Select a category below to view specific commands",
        color=discord.Color.blue()
    )

    # Add quick reference for most common commands
    embed.add_field(
        name="Quick Start",
        value="```\n#start - Begin your journey\n#status - View your stats\n#hunt - Fight monsters\n#daily - Daily rewards```",
        inline=False
    )

    embed.add_field(
        name="Categories",
        value="🌀 Gates - Explore gates and dungeons\n⚔️ Combat - Battle commands\n👥 Party - Group activities\n🏆 Arena - PvP system\n⚙️ System - Basic commands",
        inline=False
    )

    embed.set_footer(text="Use the dropdown menu below to see detailed commands for each category")

    await ctx.send(embed=embed, view=HelpView())

@bot.command(name='start')
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
        "mp": 50,
        "strength": 10,
        "agility": 10,
        "intelligence": 10,
        "inventory": [],
        "shadows": [],
        "equipment": {
            "weapon": None,
            "armor": None,
            "accessory": None
        }
    }

    save_hunters_data(hunters_data)
    await ctx.send(f"Welcome, Hunter {ctx.author.name}! Your journey in the world of hunters begins now.")

@bot.command(name='status')
async def status(ctx):
    """Check your hunter status"""
    hunters_data = load_hunters_data()
    user_id = str(ctx.author.id)

    if user_id not in hunters_data:
        await ctx.send("You haven't started your journey yet! Use #start to begin.")
        return

    hunter = hunters_data[user_id]

    # Calculate progress bars
    def create_progress_bar(current, maximum, length=10):
        filled = int((current / maximum) * length)
        return "█" * filled + "░" * (length - filled)

    # Calculate exp progress
    exp_needed = hunter['level'] * 100
    exp_progress = hunter['exp']
    exp_percentage = (exp_progress / exp_needed) * 100

    status_embed = discord.Embed(
        title=f"👤 Hunter {ctx.author.name}'s Status",
        description=f"**Rank {hunter['rank']} Hunter**",
        color=discord.Color.from_rgb(
            int(255 * (1 - hunter['hp']/100)),  # More red when HP is low
            int(255 * (hunter['hp']/100)),      # More green when HP is high
            0
        )
    )

    # Health and Mana bars
    hp_bar = create_progress_bar(hunter['hp'], 100)
    mp_bar = create_progress_bar(hunter['mp'], 50)
    status_embed.add_field(
        name="Health & Mana",
        value=f"❤️ HP: {hp_bar} {hunter['hp']}/100\n💠 MP: {mp_bar} {hunter['mp']}/50",
        inline=False
    )

    # Level and Experience
    exp_bar = create_progress_bar(exp_progress, exp_needed)
    status_embed.add_field(
        name="Level & Experience",
        value=f"📊 Level: {hunter['level']}\n⭐ EXP: {exp_bar} {exp_progress}/{exp_needed} ({exp_percentage:.1f}%)",
        inline=False
    )

    # Combat Stats
    status_embed.add_field(
        name="Combat Stats",
        value=f"⚔️ Strength: {hunter['strength']}\n🏃 Agility: {hunter['agility']}\n🧠 Intelligence: {hunter['intelligence']}",
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
        value=f"🪙 Gold: {hunter.get('gold', 0)}\n👻 Shadows: {len(hunter.get('shadows', []))}\n📦 Items: {len(hunter.get('inventory', []))}",
        inline=True
    )

    status_embed.set_footer(text="Use #help to see available commands")

    # Modern UI: Add buttons for quick actions
    class StatusView(View):
        def __init__(self):
            super().__init__(timeout=60)
            self.add_item(Button(label="Inventory", style=discord.ButtonStyle.primary, emoji="📦", custom_id="inventory"))
            self.add_item(Button(label="Shop", style=discord.ButtonStyle.success, emoji="🛒", custom_id="shop"))
            self.add_item(Button(label="PvP", style=discord.ButtonStyle.danger, emoji="⚔️", custom_id="pvp"))
            self.add_item(Button(label="Quests", style=discord.ButtonStyle.secondary, emoji="📜", custom_id="quests"))

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            return interaction.user.id == ctx.author.id

        @discord.ui.button(label="Inventory", style=discord.ButtonStyle.primary, emoji="📦", custom_id="inventory")
        async def inventory_button(self, interaction: discord.Interaction, button: Button):
            await interaction.response.send_message("(Inventory UI coming soon!)", ephemeral=True)

        @discord.ui.button(label="Shop", style=discord.ButtonStyle.success, emoji="🛒", custom_id="shop")
        async def shop_button(self, interaction: discord.Interaction, button: Button):
            await interaction.response.send_message("(Shop UI coming soon!)", ephemeral=True)

        @discord.ui.button(label="PvP", style=discord.ButtonStyle.danger, emoji="⚔️", custom_id="pvp")
        async def pvp_button(self, interaction: discord.Interaction, button: Button):
            await interaction.response.send_message("(PvP UI coming soon!)", ephemeral=True)

        @discord.ui.button(label="Quests", style=discord.ButtonStyle.secondary, emoji="📜", custom_id="quests")
        async def quests_button(self, interaction: discord.Interaction, button: Button):
            await interaction.response.send_message("(Quests UI coming soon!)", ephemeral=True)

    await ctx.send(embed=status_embed, view=StatusView())

@bot.command(name='daily')
async def daily(ctx):
    """Claim your daily reward (24-hour reset)"""
    import datetime
    hunters_data = load_hunters_data()
    user_id = str(ctx.author.id)
    now = datetime.datetime.utcnow()
    if user_id not in hunters_data:
        await ctx.send(embed=discord.Embed(description="You haven't started your journey yet! Use #start first.", color=discord.Color.red()))
        return
    hunter = hunters_data[user_id]
    last_claim = hunter.get('last_daily_claim')
    if last_claim:
        last_claim_time = datetime.datetime.fromisoformat(last_claim)
        delta = now - last_claim_time
        if delta.total_seconds() < 86400:
            hours = int((86400 - delta.total_seconds()) // 3600)
            minutes = int(((86400 - delta.total_seconds()) % 3600) // 60)
            embed = discord.Embed(
                title="⏳ Daily Reward Not Ready",
                description=f"You can claim your next daily reward in {hours}h {minutes}m.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
    # Grant reward
    gold_reward = 250
    exp_reward = 100
    hunter['gold'] = hunter.get('gold', 0) + gold_reward
    hunter['exp'] = hunter.get('exp', 0) + exp_reward
    hunter['last_daily_claim'] = now.isoformat()
    save_hunters_data(hunters_data)
    embed = discord.Embed(
        title="🎁 Daily Reward Claimed!",
        description=f"You received 🪙 {gold_reward} gold and ⭐ {exp_reward} EXP!",
        color=discord.Color.green()
    )
    embed.set_footer(text="Come back in 24 hours for your next reward.")
    await ctx.send(embed=embed)

# --- PARTY & GATE SYSTEM STUBS ---
@bot.command(name='startparty')
async def startparty(ctx, *members: discord.Member):
    """Start a party with invited members (stub/in development)"""
    if not members:
        await ctx.send("You must mention at least one member to start a party.")
        return
    mentions = ', '.join(m.mention for m in members)
    await ctx.send(f"{ctx.author.mention} has invited {mentions} to a party! (Party system is in development.)")

@bot.command(name='accept')
async def accept(ctx):
    """Accept a party, dungeon, or PvP invitation (stub/in development)"""
    await ctx.send(f"{ctx.author.mention} accepted the invitation! (Party system is in development.)")

@bot.command(name='decline')
async def decline(ctx):
    """Decline a party, dungeon, or PvP invitation (stub/in development)"""
    await ctx.send(f"{ctx.author.mention} declined the invitation! (Party system is in development.)")

@bot.command(name='finished')
async def finished(ctx):
    """Mark your turn as finished in party/guild combat (stub/in development)"""
    await ctx.send(f"{ctx.author.mention} is ready! (Party system is in development.)")

@bot.command(name='viewgates')
async def viewgates(ctx):
    """View available dimensional gates based on your rank (stub/in development)"""
    await ctx.send("Gate viewing is in development. Use #scan for now.")

@bot.command(name='viewredgates')
async def viewredgates(ctx):
    """View all known red gates based on player rank (stub/in development)"""
    await ctx.send("Red gate viewing is in development.")

@bot.command(name='entergate')
async def entergate(ctx, *, name: str = None):
    """Enter a basic gate (stub/in development)"""
    await ctx.send(f"Entering gate '{name}' (feature in development). Use #scan for now.")

@bot.command(name='enterredgate')
async def enterredgate(ctx, *, name: str = None):
    """Enter a red gate (stub/in development)"""
    await ctx.send(f"Entering red gate '{name}' (feature in development).")

@bot.command(name='exitgate')
async def exitgate(ctx):
    """Exit the current gate (stub/in development)"""
    await ctx.send("Exiting gate (feature in development). Use #scan for now.")

@bot.command(name='dungeons')
async def dungeons(ctx):
    """View available dungeon raids (stub/in development)"""
    await ctx.send("Dungeon viewing is in development. Use #dungeon for now.")

@bot.command(name='refuse')
async def refuse(ctx):
    """Refuse a party/dungeon invitation (stub/in development)"""
    await ctx.send(f"{ctx.author.mention} refused the invitation! (Party system is in development.)")

@bot.command(name='exitdungeon')
async def exitdungeon(ctx):
    """Flee the dungeon with all party members (stub/in development)"""
    await ctx.send("Exiting dungeon (feature in development). Use #dungeon for now.")

@bot.command(name='dodge')
async def dodge(ctx):
    """Attempt to dodge an attack (stub/in development)"""
    await ctx.send("Dodge feature is in development.")

@bot.command(name='ability')
async def ability(ctx, *, name: str = None):
    """Use an ability/skill (with UI selection)"""
    hunters_data = load_hunters_data()
    user_id = str(ctx.author.id)
    if user_id not in hunters_data:
        await ctx.send(embed=discord.Embed(description="You haven't started your journey yet! Use #start first.", color=discord.Color.red()))
        return
    # Demo ability list (could be expanded per class/job)
    abilities = [
        {"name": "Power Strike", "desc": "Deal heavy physical damage.", "effect": "+20 STR"},
        {"name": "Heal", "desc": "Restore some HP.", "effect": "+30 HP"},
        {"name": "Shadow Veil", "desc": "Increase dodge chance for 1 turn.", "effect": "+50% Dodge"},
        {"name": "Mana Burst", "desc": "Deal magic damage and restore MP.", "effect": "+15 INT, +20 MP"}
    ]
    class AbilitySelect(discord.ui.Select):
        def __init__(self):
            options = [discord.SelectOption(label=a["name"], description=a["desc"]) for a in abilities]
            super().__init__(placeholder="Choose an ability...", min_values=1, max_values=1, options=options)
        async def callback(self, interaction: discord.Interaction):
            selected = self.values[0]
            ability = next(a for a in abilities if a["name"] == selected)
            embed = discord.Embed(
                title=f"🌀 Ability Used: {ability['name']}",
                description=f"{ability['desc']}\nEffect: {ability['effect']}",
                color=discord.Color.purple()
            )
            await interaction.response.send_message(embed=embed)
    class AbilityView(View):
        def __init__(self):
            super().__init__(timeout=30)
            self.add_item(AbilitySelect())
    await ctx.send(embed=discord.Embed(title="Choose an Ability", description="Select an ability to use:", color=discord.Color.purple()), view=AbilityView())

@bot.command(name='awaken')
async def awaken(ctx):
    """Begin your hunter journey at the awakening gate (one-time use)"""
    hunters_data = load_hunters_data()
    user_id = str(ctx.author.id)
    if user_id in hunters_data and hunters_data[user_id].get('awakened', False):
        embed = discord.Embed(
            title="Awakening Failed",
            description="You have already awakened! This can only be done once.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    # If not started, initialize hunter data
    if user_id not in hunters_data:
        hunters_data[user_id] = {
            "level": 1,
            "exp": 0,
            "rank": "E",
            "hp": 100,
            "mp": 50,
            "strength": 10,
            "agility": 10,
            "intelligence": 10,
            "inventory": [],
            "shadows": [],
            "equipment": {
                "weapon": None,
                "armor": None,
                "accessory": None
            }
        }
    hunters_data[user_id]['awakened'] = True
    save_hunters_data(hunters_data)
    embed = discord.Embed(
        title="🌌 Awakening Gate",
        description=f"{ctx.author.mention}, you have awakened as a Hunter! Your journey begins now.",
        color=discord.Color.blue()
    )
    embed.add_field(name="Next Steps", value="Use #status to view your profile, #start to begin your journey, or #help for all commands.")
    await ctx.send(embed=embed)

@bot.command(name='topserver')
async def topserver(ctx):
    """Display top players, ranks, and PvP stats (stub/in development)"""
    await ctx.send("Top server leaderboard is in development.")

@bot.command(name='rank')
async def rank(ctx):
    """Show experience bar and progress to next rank (stub/in development)"""
    await ctx.send("Rank progress feature is in development.")

@bot.command(name='dailyquest')
async def dailyquest(ctx):
    """Alias for #daily (shows daily quests)"""
    await ctx.invoke(bot.get_command('daily'))

@bot.command(name='guildwar')
async def guildwar(ctx):
    """Start a guild war (stub/in development)"""
    await ctx.send("Guild war feature is in development.")

@bot.command(name='guildraid')
async def guildraid(ctx, *, name: str = None):
    """Start a guild raid on a gate, red gate, or dungeon (stub/in development)"""
    await ctx.send(f"Guild raid '{name}' feature is in development.")

# Run the bot
def run_bot():
    bot.run(os.getenv('DISCORD_TOKEN'))

if __name__ == "__main__":
    asyncio.run(run_bot())
