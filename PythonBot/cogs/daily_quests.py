import discord
from discord.ext import commands
import json
from datetime import datetime

class DailyQuests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def load_hunters_data(self):
        """Load hunter data from JSON file"""
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_hunters_data(self, data):
        """Save hunter data to JSON file"""
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)
    
    @commands.command(name='daily_quests', aliases=['daily'])
    async def show_daily_quests(self, ctx):
        """Display daily quests"""
        user_id = str(ctx.author.id)
        
        # Check if player is resting
        from main import check_if_resting
        is_resting, rest_message = check_if_resting(user_id)
        if is_resting:
            from utils.theme_utils import get_error_embed
            embed = get_error_embed(ctx.author.id, rest_message)
            await ctx.send(embed=embed)
            return
        
        hunters_data = self.load_hunters_data()
        
        if user_id not in hunters_data:
            from utils.theme_utils import get_error_embed
            embed = get_error_embed(ctx.author.id, "You need to start your journey first! Use `.start`")
            await ctx.send(embed=embed)
            return
        
        hunter = hunters_data[user_id]
        
        # Check and reset daily quests if needed
        from daily_quest_system import should_reset_daily_quests, generate_daily_quests
        
        quests = hunter.get('quests', {})
        last_reset = quests.get('last_daily_reset', '')
        
        if should_reset_daily_quests(last_reset):
            # Generate new daily quests
            daily_quests = generate_daily_quests(hunter['level'])
            if 'quests' not in hunter:
                hunter['quests'] = {}
            hunter['quests']['daily'] = daily_quests
            hunter['quests']['last_daily_reset'] = datetime.now().strftime("%Y-%m-%d")
            self.save_hunters_data(hunters_data)
        
        daily_quests = hunter.get('quests', {}).get('daily', {})
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        embed = discord.Embed(
            title="📋 Daily Quests",
            description="Complete these quests for daily rewards",
            color=discord.Color(colors['accent'])
        )
        
        if not daily_quests:
            embed.add_field(
                name="No Daily Quests",
                value="Daily quests will be generated automatically",
                inline=False
            )
        else:
            for quest_id, quest in daily_quests.items():
                status_emoji = "✅" if quest.get('completed', False) else "🔄"
                claimed_text = " (Claimed)" if quest.get('claimed', False) else ""
                
                progress_percent = (quest.get('progress', 0) / quest['target']) * 100
                
                quest_info = (f"{status_emoji} **{quest['name']}**{claimed_text}\n"
                             f"{quest['description']}\n"
                             f"Progress: {quest.get('progress', 0)}/{quest['target']} ({progress_percent:.1f}%)\n"
                             f"Rewards: {quest.get('reward_gold', 0)} Gold, {quest.get('reward_exp', 0)} EXP")
                
                embed.add_field(name=f"Quest {quest_id.replace('_', ' ').title()}", value=quest_info, inline=False)
        
        # Add navigation info
        embed.add_field(
            name="Other Quest Types",
            value="📅 Use `.weekly_quests` for weekly challenges\n🗝️ Use `.special_quests` for legendary quests",
            inline=False
        )
        
        embed.set_footer(text="Daily quests reset every day • Use .claim to claim completed quests")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(DailyQuests(bot))