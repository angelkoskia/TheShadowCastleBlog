import discord
from discord.ext import commands
import json
import random
from datetime import datetime, timedelta

class DailyQuests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('data/quests.json', 'r') as f:
            self.quests_data = json.load(f)

    def load_hunters_data(self):
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_hunters_data(self, data):
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    def generate_daily_quests(self):
        """Generate a set of daily quests"""
        daily_quests = {}
        for quest_id, quest in self.quests_data['daily'].items():
            variant = random.choice(quest['variants'])
            daily_quests[quest_id] = {
                'name': quest['name'],
                'description': quest['description'].format(count=variant['count']),
                'target': variant['count'],
                'progress': 0,
                'reward_gold': variant['reward_gold'],
                'reward_exp': variant['reward_exp'],
                'completed': False
            }
        return daily_quests

    def generate_weekly_quests(self):
        """Generate a set of weekly quests"""
        weekly_quests = {}
        for quest_id, quest in self.quests_data['weekly'].items():
            variant = random.choice(quest['variants'])
            weekly_quests[quest_id] = {
                'name': quest['name'],
                'description': quest['description'].format(count=variant['count']),
                'target': variant['count'],
                'progress': 0,
                'reward_gold': variant['reward_gold'],
                'reward_exp': variant['reward_exp'],
                'completed': False
            }
        return weekly_quests

    @commands.command(name='daily')
    async def show_daily_quests(self, ctx):
        """Display your daily quests"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You haven't started your journey yet! Use !start first.")
            return

        hunter = hunters_data[user_id]
        current_date = datetime.now().strftime('%Y-%m-%d')

        # Check if daily quests need to be reset
        if not hunter.get('quests') or hunter['quests'].get('last_daily_reset') != current_date:
            hunter['quests'] = hunter.get('quests', {})
            hunter['quests']['daily'] = self.generate_daily_quests()
            hunter['quests']['last_daily_reset'] = current_date
            self.save_hunters_data(hunters_data)

        embed = discord.Embed(
            title="📋 Daily Quests",
            description="Complete these quests for rewards!",
            color=0x00ff00
        )

        for quest_id, quest in hunter['quests']['daily'].items():
            status = "✅" if quest['completed'] else "❌"
            progress = f"{quest['progress']}/{quest['target']}"
            rewards = f"🪙 {quest['reward_gold']} gold, ⭐ {quest['reward_exp']} exp"

            embed.add_field(
                name=f"{status} {quest['name']}",
                value=f"{quest['description']}\nProgress: {progress}\nRewards: {rewards}",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name='weekly')
    async def show_weekly_quests(self, ctx):
        """Display your weekly quests"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You haven't started your journey yet! Use !start first.")
            return

        hunter = hunters_data[user_id]
        current_week = datetime.now().strftime('%Y-%W')

        # Check if weekly quests need to be reset
        if not hunter.get('quests') or hunter['quests'].get('last_weekly_reset') != current_week:
            hunter['quests'] = hunter.get('quests', {})
            hunter['quests']['weekly'] = self.generate_weekly_quests()
            hunter['quests']['last_weekly_reset'] = current_week
            self.save_hunters_data(hunters_data)

        embed = discord.Embed(
            title="📋 Weekly Quests",
            description="Complete these quests for greater rewards!",
            color=0x0000ff
        )

        for quest_id, quest in hunter['quests']['weekly'].items():
            status = "✅" if quest['completed'] else "❌"
            progress = f"{quest['progress']}/{quest['target']}"
            rewards = f"🪙 {quest['reward_gold']} gold, ⭐ {quest['reward_exp']} exp"

            embed.add_field(
                name=f"{status} {quest['name']}",
                value=f"{quest['description']}\nProgress: {progress}\nRewards: {rewards}",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name='dailyquest')
    async def show_daily_quests(self, ctx):
        """View your current daily quests"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        if user_id not in hunters_data:
            await ctx.send(embed=discord.Embed(description="You haven't started your journey yet! Use #awaken first.", color=discord.Color.red()))
            return
        hunter = hunters_data[user_id]
        if 'daily_quests' not in hunter or not hunter['daily_quests']:
            # Generate new daily quests if none exist
            hunter['daily_quests'] = self.generate_daily_quests()
            self.save_hunters_data(hunters_data)
        embed = discord.Embed(title=f"{ctx.author.name}'s Daily Quests", color=discord.Color.green())
        for quest_id, quest in hunter['daily_quests'].items():
            status = '✅ Completed' if quest['completed'] else f"{quest['progress']}/{quest['target']}"
            embed.add_field(
                name=quest['name'],
                value=f"{quest['description']}\nProgress: {status}\nReward: {quest['reward_gold']} Gold, {quest['reward_exp']} EXP",
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.command(name='daily')
    async def claim_daily(self, ctx):
        """Claim your daily gold and EXP (24-hour reset)"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        if user_id not in hunters_data:
            await ctx.send(embed=discord.Embed(description="You haven't started your journey yet! Use #awaken first.", color=discord.Color.red()))
            return
        hunter = hunters_data[user_id]
        now = datetime.now()
        last_claim = hunter.get('last_daily_claim')
        if last_claim:
            last_claim_dt = datetime.strptime(last_claim, '%Y-%m-%d')
            if last_claim_dt.date() == now.date():
                await ctx.send(embed=discord.Embed(description="You have already claimed your daily reward today! Come back tomorrow.", color=discord.Color.orange()))
                return
        gold_reward = 100 + hunter.get('level', 1) * 10
        exp_reward = 50 + hunter.get('level', 1) * 5
        hunter['gold'] = hunter.get('gold', 0) + gold_reward
        hunter['exp'] = hunter.get('exp', 0) + exp_reward
        hunter['last_daily_claim'] = now.strftime('%Y-%m-%d')
        self.save_hunters_data(hunters_data)
        embed = discord.Embed(title="Daily Reward Claimed!", description=f"You received 🪙 {gold_reward} gold and ⭐ {exp_reward} EXP!", color=discord.Color.green())
        await ctx.send(embed=embed)

    def update_quest_progress(self, user_id, quest_type, amount=1):
        """Update quest progress for a specific type"""
        hunters_data = self.load_hunters_data()
        if user_id not in hunters_data:
            return

        hunter = hunters_data[user_id]
        if 'quests' not in hunter:
            return

        updated = False
        for period in ['daily', 'weekly']:
            if period not in hunter['quests']:
                continue

            for quest_id, quest in hunter['quests'][period].items():
                if quest_id == quest_type and not quest['completed']:
                    quest['progress'] += amount
                    if quest['progress'] >= quest['target']:
                        quest['completed'] = True
                        hunter['gold'] = hunter.get('gold', 0) + quest['reward_gold']
                        hunter['exp'] = hunter.get('exp', 0) + quest['reward_exp']
                        updated = True

        if updated:
            self.save_hunters_data(hunters_data)

    @commands.Cog.listener()
    async def on_command(self, ctx):
        """Listen for commands to update relevant quests"""
        if ctx.command.name in ['hunt', 'dungeon']:
            self.update_quest_progress(str(ctx.author.id), 'monster_hunt')
        elif ctx.command.name == 'enter':
            self.update_quest_progress(str(ctx.author.id), 'gate_clear')
        elif ctx.command.name == 'train':
            self.update_quest_progress(str(ctx.author.id), 'shadow_training')
        elif ctx.command.name == 'pvp' and not ctx.command_failed:
            self.update_quest_progress(str(ctx.author.id), 'pvp_battles')

async def setup(bot):
    await bot.add_cog(DailyQuests(bot))
