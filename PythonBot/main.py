import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()

# Bot configuration
COMMAND_PREFIX = '!'
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

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

async def load_cogs():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')
            print(f'Loaded cog: {filename[:-3]}')

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    await load_cogs()
    print('Bot is ready!')

    # Create necessary data files if they don't exist
    if not os.path.exists('hunters_data.json'):
        save_hunters_data({})

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
        await ctx.send("You haven't started your journey yet! Use !start to begin.")
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

    status_embed.set_footer(text="Use !help to see available commands")
    await ctx.send(embed=status_embed)

# Run the bot
async def main():
    async with bot:
        await bot.start(os.getenv('DISCORD_TOKEN'))

if __name__ == "__main__":
    asyncio.run(main())
