import discord
from discord.ext import commands
from discord.ui import View, Select
import json

CLASSES = [
    ("Summoner", "Summon and control shadows or beasts."),
    ("Mage", "Cast powerful spells and elemental attacks."),
    ("Fighter", "Excel in close combat and physical strength."),
    ("Assassin", "Stealth, speed, and critical strikes."),
    ("Tank", "Absorb damage and protect allies."),
    ("Healer", "Restore health and support the party."),
]

class ClassSelection(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_hunters_data(self):
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_hunters_data(self, data):
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    @commands.command(name='class')
    async def choose_class(self, ctx):
        """Choose your hunter class (one-time selection)"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        if user_id not in hunters_data:
            await ctx.send(embed=discord.Embed(description="You haven't started your journey yet! Use #awaken first.", color=discord.Color.red()))
            return
        if 'class' in hunters_data[user_id]:
            await ctx.send(embed=discord.Embed(description=f"You have already chosen the class: {hunters_data[user_id]['class']}", color=discord.Color.orange()))
            return
        options = [discord.SelectOption(label=cls, description=desc) for cls, desc in CLASSES]
        class ClassSelectView(View):
            @discord.ui.select(placeholder="Choose your class...", min_values=1, max_values=1, options=options)
            async def select_callback(self, interaction: discord.Interaction, select: Select):
                chosen = select.values[0]
                hunters_data[user_id]['class'] = chosen
                self.cog.save_hunters_data(hunters_data)
                await interaction.response.send_message(f"Class selected: **{chosen}**!", ephemeral=True)
                self.stop()
        view = ClassSelectView()
        view.cog = self
        await ctx.send(embed=discord.Embed(title="Class Selection", description="Choose your hunter class:", color=discord.Color.blue()), view=view)

async def setup(bot):
    await bot.add_cog(ClassSelection(bot))

