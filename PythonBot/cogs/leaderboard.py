import discord
from discord.ext import commands
import json

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_hunters_data(self):
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    @commands.command(name='topserver')
    async def top_server(self, ctx):
        """Display the top hunters on the server by level and experience."""
        hunters_data = self.load_hunters_data()
        leaderboard = sorted(
            hunters_data.values(),
            key=lambda h: (h.get('level', 1), h.get('exp', 0)),
            reverse=True
        )
        embed = discord.Embed(title="🏆 Top Hunters (Server Leaderboard)", color=discord.Color.gold())
        for i, hunter in enumerate(leaderboard[:10], 1):
            embed.add_field(
                name=f"#{i} {hunter.get('name', 'Unknown')}",
                value=f"Level: {hunter.get('level', 1)} | EXP: {hunter.get('exp', 0)} | PvP Wins: {hunter.get('pvp_wins', 0)}",
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.command(name='rank')
    async def show_rank(self, ctx):
        """Show your experience bar and progress to the next rank."""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        if user_id not in hunters_data:
            await ctx.send(embed=discord.Embed(description="You haven't started your journey yet! Use #awaken first.", color=discord.Color.red()))
            return
        hunter = hunters_data[user_id]
        level = hunter.get('level', 1)
        exp = hunter.get('exp', 0)
        next_level_exp = level * 100
        percent = int((exp / next_level_exp) * 100)
        bar = '█' * (percent // 10) + '░' * (10 - percent // 10)
        embed = discord.Embed(title=f"{ctx.author.name}'s Rank Progress", color=discord.Color.purple())
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="EXP", value=f"{exp}/{next_level_exp}", inline=True)
        embed.add_field(name="Progress", value=f"{bar} {percent}%", inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))

