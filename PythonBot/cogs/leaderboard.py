import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import json
from typing import Dict, List
import asyncio

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_hunters_data(self) -> Dict:
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    class LeaderboardView(View):
        def __init__(self, cog):
            super().__init__(timeout=60)
            self.cog = cog
            self.add_item(self.CategorySelect())

        class CategorySelect(Select):
            def __init__(self):
                options = [
                    discord.SelectOption(label="PvP Rankings", value="pvp", emoji="⚔️"),
                    discord.SelectOption(label="Level Rankings", value="level", emoji="📊"),
                    discord.SelectOption(label="Hunter Ranks", value="rank", emoji="🎯"),
                    discord.SelectOption(label="Wealth Rankings", value="gold", emoji="💰")
                ]
                super().__init__(placeholder="Select ranking category...", options=options)

            async def callback(self, interaction: discord.Interaction):
                await self.view.cog.show_leaderboard(interaction, self.values[0])

    @commands.command(name='topserver')
    async def topserver(self, ctx):
        """Display top players and rankings"""
        embed = discord.Embed(
            title="🏆 Solo Leveling Leaderboards",
            description="Select a category to view rankings",
            color=discord.Color.gold()
        )

        # Quick stats summary
        hunters_data = self.load_hunters_data()
        total_hunters = len(hunters_data)
        total_pvp_matches = sum(hunter.get('pvp_wins', 0) + hunter.get('pvp_losses', 0)
                              for hunter in hunters_data.values())

        embed.add_field(
            name="Server Stats",
            value=f"Total Hunters: {total_hunters}\nPvP Matches: {total_pvp_matches}",
            inline=False
        )

        embed.set_footer(text="Use the dropdown menu to view specific rankings")
        await ctx.send(embed=embed, view=self.LeaderboardView(self))

    async def show_leaderboard(self, interaction: discord.Interaction, category: str):
        """Show leaderboard for specific category"""
        hunters_data = self.load_hunters_data()

        if not hunters_data:
            await interaction.response.send_message("No hunters found!", ephemeral=True)
            return

        # Sort hunters based on category
        if category == "pvp":
            sorted_hunters = sorted(
                hunters_data.items(),
                key=lambda x: (x[1].get('pvp_wins', 0), -x[1].get('pvp_losses', 0)),
                reverse=True
            )
            title = "⚔️ PvP Rankings"
            description = "Top PvP fighters"
        elif category == "level":
            sorted_hunters = sorted(
                hunters_data.items(),
                key=lambda x: (x[1].get('level', 1), x[1].get('exp', 0)),
                reverse=True
            )
            title = "📊 Level Rankings"
            description = "Highest level hunters"
        elif category == "rank":
            rank_order = {'S': 6, 'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1}
            sorted_hunters = sorted(
                hunters_data.items(),
                key=lambda x: (rank_order.get(x[1].get('rank', 'E'), 0), x[1].get('level', 1)),
                reverse=True
            )
            title = "🎯 Hunter Ranks"
            description = "Top ranked hunters"
        else:  # gold
            sorted_hunters = sorted(
                hunters_data.items(),
                key=lambda x: x[1].get('gold', 0),
                reverse=True
            )
            title = "💰 Wealth Rankings"
            description = "Richest hunters"

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.gold()
        )

        # Add top 10 players
        for i, (user_id, hunter) in enumerate(sorted_hunters[:10], 1):
            user = self.bot.get_user(int(user_id))
            if not user:
                continue

            if category == "pvp":
                value = f"Wins: {hunter.get('pvp_wins', 0)} | Losses: {hunter.get('pvp_losses', 0)}"
            elif category == "level":
                value = f"Level {hunter.get('level', 1)} | EXP: {hunter.get('exp', 0)}"
            elif category == "rank":
                value = f"Rank {hunter.get('rank', 'E')} | Level {hunter.get('level', 1)}"
            else:  # gold
                value = f"🪙 {hunter.get('gold', 0)} gold"

            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
            embed.add_field(
                name=f"{medal} {user.display_name}",
                value=value,
                inline=False
            )

        # Add navigation buttons
        class NavigationView(View):
            def __init__(self):
                super().__init__(timeout=60)

            @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, emoji="⬅️")
            async def previous(self, interaction: discord.Interaction, button: Button):
                # Implementation for pagination if needed
                await interaction.response.send_message("Previous page coming soon!", ephemeral=True)

            @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, emoji="➡️")
            async def next(self, interaction: discord.Interaction, button: Button):
                # Implementation for pagination if needed
                await interaction.response.send_message("Next page coming soon!", ephemeral=True)

            @discord.ui.button(label="Refresh", style=discord.ButtonStyle.primary, emoji="🔄")
            async def refresh(self, interaction: discord.Interaction, button: Button):
                await self.view.cog.show_leaderboard(interaction, category)

        await interaction.response.send_message(embed=embed, view=NavigationView())

    @commands.command(name='rank')
    async def rank(self, ctx):
        """Show your rank progress"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use #start")
            return

        hunter = hunters_data[user_id]
        current_rank = hunter.get('rank', 'E')

        # Calculate rank progress
        rank_requirements = {
            'E': {'exp': 1000, 'next': 'D'},
            'D': {'exp': 3000, 'next': 'C'},
            'C': {'exp': 7000, 'next': 'B'},
            'B': {'exp': 15000, 'next': 'A'},
            'A': {'exp': 30000, 'next': 'S'}
        }

        current_req = rank_requirements.get(current_rank)
        if current_req:
            next_rank = current_req['next']
            exp_needed = current_req['exp']
            current_exp = hunter.get('exp', 0)
            progress = min(100, (current_exp / exp_needed) * 100)
        else:
            next_rank = None
            progress = 100

        # Create progress bar
        def create_progress_bar(percentage, length=20):
            filled = int((percentage / 100) * length)
            return "█" * filled + "░" * (length - filled)

        embed = discord.Embed(
            title=f"🎯 Hunter Rank - {ctx.author.display_name}",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Current Rank",
            value=f"**{current_rank}**-Rank Hunter",
            inline=False
        )

        if next_rank:
            embed.add_field(
                name="Progress to Next Rank",
                value=f"{create_progress_bar(progress)} {progress:.1f}%\n"
                      f"EXP: {current_exp}/{exp_needed}\n"
                      f"Next Rank: {next_rank}",
                inline=False
            )
        else:
            embed.add_field(
                name="Status",
                value="Maximum rank achieved! (S-Rank)",
                inline=False
            )

        # Add stats
        embed.add_field(
            name="Stats",
            value=f"Level: {hunter.get('level', 1)}\n"
                  f"Total EXP: {hunter.get('exp', 0)}\n"
                  f"PvP Record: {hunter.get('pvp_wins', 0)}W/{hunter.get('pvp_losses', 0)}L",
            inline=False
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
