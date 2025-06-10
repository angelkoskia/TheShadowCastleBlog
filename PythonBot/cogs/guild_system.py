import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import json
import asyncio

class GuildSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_guild_raids = {}
        self.active_guild_wars = {}
        self.guild_data = {}

    def load_hunters_data(self):
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_hunters_data(self, data):
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    @commands.command(name='guildwar')
    async def guild_war(self, ctx, opponent_guild: discord.Role):
        """Start a guild war with member matching and modern UI."""
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.send(embed=discord.Embed(description="Only guild leaders can start wars!", color=discord.Color.red()))
            return

        # Create war UI with member matching
        embed = discord.Embed(title="⚔️ Guild War", description=f"{ctx.guild.name} vs {opponent_guild.name}", color=discord.Color.red())
        embed.add_field(name="Status", value="Matching members...", inline=False)

        class GuildWarView(View):
            def __init__(self):
                super().__init__(timeout=300)
                self.matches = []

            @discord.ui.button(label="Accept War", style=discord.ButtonStyle.danger)
            async def accept_war(self, interaction: discord.Interaction, button: Button):
                await self.match_members(interaction)

            @discord.ui.button(label="Cancel War", style=discord.ButtonStyle.secondary)
            async def cancel_war(self, interaction: discord.Interaction, button: Button):
                await interaction.response.send_message("Guild war cancelled.", ephemeral=True)
                self.stop()

            async def match_members(self, interaction):
                # Match members by level/rank
                hunters_data = self.cog.load_hunters_data()
                # ... member matching logic ...
                await interaction.response.edit_message(embed=embed.set_field_at(0, name="Status", value="War started! Check #guildwar-battles"))

        await ctx.send(embed=embed, view=GuildWarView())

    @commands.command(name='guildraid')
    async def guild_raid(self, ctx, *, raid_name: str):
        """Start a coordinated guild raid with modern UI."""
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.send(embed=discord.Embed(description="Only guild leaders can start raids!", color=discord.Color.red()))
            return

        embed = discord.Embed(title="🏰 Guild Raid", description=f"Raid Target: {raid_name}", color=discord.Color.purple())
        embed.add_field(name="Status", value="Gathering raiders...", inline=False)

        class GuildRaidView(View):
            def __init__(self):
                super().__init__(timeout=180)
                self.raiders = set()

            @discord.ui.button(label="Join Raid", style=discord.ButtonStyle.success)
            async def join_raid(self, interaction: discord.Interaction, button: Button):
                self.raiders.add(interaction.user.id)
                await interaction.response.send_message(f"Joined the raid against {raid_name}!", ephemeral=True)

            @discord.ui.button(label="Start Raid", style=discord.ButtonStyle.primary)
            async def start_raid(self, interaction: discord.Interaction, button: Button):
                if len(self.raiders) < 3:
                    await interaction.response.send_message("Need at least 3 raiders!", ephemeral=True)
                    return
                # Start the raid with gathered members
                await self.begin_raid(interaction)

            async def begin_raid(self, interaction):
                raid_embed = discord.Embed(title="🏰 Raid Started!", description=f"Raiding: {raid_name}", color=discord.Color.gold())
                await interaction.response.edit_message(embed=raid_embed, view=None)

        await ctx.send(embed=embed, view=GuildRaidView())

async def setup(bot):
    await bot.add_cog(GuildSystem(bot))
