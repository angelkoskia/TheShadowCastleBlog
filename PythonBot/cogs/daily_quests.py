import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import json
import random
import asyncio
from datetime import datetime, timedelta

class DailyQuests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('data/quests.json', 'r') as f:
            self.quest_templates = json.load(f)

    def load_hunters_data(self):
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_hunters_data(self, data):
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    class QuestView(View):
        def __init__(self, cog):
            super().__init__(timeout=60)
            self.cog = cog

        @discord.ui.button(label="Claim Rewards", style=discord.ButtonStyle.success, emoji="🎁")
        async def claim_rewards(self, interaction: discord.Interaction, button: Button):
            await self.cog.claim_quest_rewards(interaction)

        @discord.ui.button(label="Refresh", style=discord.ButtonStyle.primary, emoji="🔄")
        async def refresh_quests(self, interaction: discord.Interaction, button: Button):
            await self.cog.show_quests(interaction)

    @commands.command(name='daily')
    async def daily(self, ctx):
        """Claim daily rewards and view daily quests"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use #start")
            return

        hunter = hunters_data[user_id]
        now = datetime.utcnow()

        # Check daily reward cooldown
        last_daily = datetime.fromisoformat(hunter.get('last_daily', '2000-01-01T00:00:00'))
        if (now - last_daily).total_seconds() < 86400:
            next_daily = last_daily + timedelta(days=1)
            time_left = next_daily - now
            hours = int(time_left.total_seconds() // 3600)
            minutes = int((time_left.total_seconds() % 3600) // 60)

            embed = discord.Embed(
                title="⏳ Daily Reward Not Ready",
                description=f"Next daily reward available in {hours}h {minutes}m",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return

        # Grant daily rewards
        gold_reward = 250
        exp_reward = 100
        hunter['gold'] = hunter.get('gold', 0) + gold_reward
        hunter['exp'] = hunter.get('exp', 0) + exp_reward
        hunter['last_daily'] = now.isoformat()

        # Generate new daily quests if needed
        if 'daily_quests' not in hunter or now.date() > datetime.fromisoformat(hunter.get('last_quest_reset', '2000-01-01T00:00:00')).date():
            hunter['daily_quests'] = self.generate_daily_quests()
            hunter['last_quest_reset'] = now.isoformat()

        self.save_hunters_data(hunters_data)

        # Show rewards and quests
        embed = discord.Embed(
            title="🎁 Daily Rewards Claimed!",
            description=f"You received:\n🪙 {gold_reward} gold\n⭐ {exp_reward} EXP",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        await self.show_quests(ctx)

    def generate_daily_quests(self):
        """Generate new daily quests"""
        quest_pool = self.quest_templates['daily']
        selected_quests = random.sample(quest_pool, 3)

        quests = []
        for quest in selected_quests:
            quests.append({
                'type': quest['type'],
                'description': quest['description'],
                'target': random.randint(quest['min_target'], quest['max_target']),
                'progress': 0,
                'rewards': {
                    'gold': quest['base_gold'],
                    'exp': quest['base_exp']
                },
                'completed': False
            })
        return quests

    @commands.command(name='dailyquest')
    async def dailyquest(self, ctx):
        """View daily quests"""
        await self.show_quests(ctx)

    async def show_quests(self, ctx):
        """Display daily quests"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use #start")
            return

        hunter = hunters_data[user_id]
        if 'daily_quests' not in hunter:
            hunter['daily_quests'] = self.generate_daily_quests()
            hunter['last_quest_reset'] = datetime.utcnow().isoformat()
            self.save_hunters_data(hunters_data)

        embed = discord.Embed(
            title="📜 Daily Quests",
            color=discord.Color.blue()
        )

        # Calculate time until reset
        now = datetime.utcnow()
        next_reset = datetime.fromisoformat(hunter['last_quest_reset']).date() + timedelta(days=1)
        time_left = next_reset - now.date()

        embed.add_field(
            name="Time Until Reset",
            value=f"Resets in {time_left.days} day(s)",
            inline=False
        )

        # Show quests
        for i, quest in enumerate(hunter['daily_quests'], 1):
            progress_bar = self.create_progress_bar(quest['progress'], quest['target'])
            status = "✅ Complete!" if quest['completed'] else f"Progress: {progress_bar} ({quest['progress']}/{quest['target']})"

            embed.add_field(
                name=f"Quest {i}: {quest['description']}",
                value=f"{status}\nRewards: 🪙 {quest['rewards']['gold']} gold | ⭐ {quest['rewards']['exp']} EXP",
                inline=False
            )

        await ctx.send(embed=embed, view=self.QuestView(self))

    def create_progress_bar(self, current, maximum, length=10):
        """Create a visual progress bar"""
        filled = int((current / maximum) * length)
        return "█" * filled + "░" * (length - filled)

    async def claim_quest_rewards(self, interaction):
        """Claim rewards for completed quests"""
        hunters_data = self.load_hunters_data()
        user_id = str(interaction.user.id)

        if user_id not in hunters_data:
            await interaction.response.send_message("You need to start your journey first! Use #start", ephemeral=True)
            return

        hunter = hunters_data[user_id]
        if 'daily_quests' not in hunter:
            await interaction.response.send_message("No quests available!", ephemeral=True)
            return

        # Calculate rewards from completed quests
        total_gold = 0
        total_exp = 0
        claimed_quests = []

        for i, quest in enumerate(hunter['daily_quests']):
            if quest['completed'] and not quest.get('claimed', False):
                total_gold += quest['rewards']['gold']
                total_exp += quest['rewards']['exp']
                hunter['daily_quests'][i]['claimed'] = True
                claimed_quests.append(quest)

        if not claimed_quests:
            await interaction.response.send_message("No completed quests to claim!", ephemeral=True)
            return

        # Grant rewards
        hunter['gold'] = hunter.get('gold', 0) + total_gold
        hunter['exp'] = hunter.get('exp', 0) + total_exp
        self.save_hunters_data(hunters_data)

        # Show claim message
        embed = discord.Embed(
            title="🎁 Quest Rewards Claimed!",
            description=f"You received:\n🪙 {total_gold} gold\n⭐ {total_exp} EXP",
            color=discord.Color.green()
        )

        for quest in claimed_quests:
            embed.add_field(
                name="Completed Quest",
                value=quest['description'],
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Track quest progress from messages"""
        if message.author.bot:
            return

        # Update quest progress based on actions
        hunters_data = self.load_hunters_data()
        user_id = str(message.author.id)

        if user_id not in hunters_data or 'daily_quests' not in hunters_data[user_id]:
            return

        hunter = hunters_data[user_id]
        updated = False

        for i, quest in enumerate(hunter['daily_quests']):
            if quest['completed']:
                continue

            # Update progress based on quest type and message content
            if self.should_update_quest(quest, message):
                hunter['daily_quests'][i]['progress'] += 1
                if hunter['daily_quests'][i]['progress'] >= quest['target']:
                    hunter['daily_quests'][i]['completed'] = True
                updated = True

        if updated:
            self.save_hunters_data(hunters_data)

    def should_update_quest(self, quest, message):
        """Check if a message should update quest progress"""
        content = message.content.lower()

        if quest['type'] == 'hunt' and content.startswith('#hunt'):
            return True
        elif quest['type'] == 'pvp' and content.startswith('#pvp'):
            return True
        elif quest['type'] == 'gate' and (content.startswith('#entergate') or content.startswith('#enterredgate')):
            return True

        return False

async def setup(bot):
    await bot.add_cog(DailyQuests(bot))
