import discord
from discord.ext import commands
import json
import random
import asyncio

class ShadowArmy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Load monster data for shadow extraction
        with open('data/monsters.json', 'r') as f:
            self.monsters_data = json.load(f)

    def load_hunters_data(self):
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_hunters_data(self, data):
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    def calculate_shadow_grade(self, monster_rank):
        """Calculate shadow grade based on monster rank and RNG"""
        grades = {
            'E': ['Normal', 'Rare'],
            'D': ['Normal', 'Rare', 'Elite'],
            'C': ['Rare', 'Elite', 'Unique'],
            'B': ['Elite', 'Unique', 'Legend'],
            'A': ['Unique', 'Legend', 'Myth'],
            'S': ['Legend', 'Myth', 'National']
        }

        available_grades = grades.get(monster_rank, ['Normal'])
        weights = [0.6, 0.3, 0.1][:len(available_grades)]
        return random.choices(available_grades, weights=weights, k=1)[0]

    @commands.command(name='extract')
    async def extract_shadow(self, ctx, *, monster_name: str):
        """Attempt to extract a shadow from a defeated monster"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send(embed=discord.Embed(description="You haven't started your journey yet! Use #start first.", color=discord.Color.red()))
            return

        # Find monster in data
        monster_data = None
        for category in self.monsters_data:
            for monster_id, data in self.monsters_data[category].items():
                if data['name'].lower() == monster_name.lower():
                    monster_data = data
                    break
            if monster_data:
                break

        if not monster_data:
            await ctx.send(embed=discord.Embed(description="Monster not found!", color=discord.Color.orange()))
            return

        # Check if extraction is successful
        if random.random() > monster_data['shadow_chance']:
            await ctx.send(embed=discord.Embed(description="Shadow extraction failed! The monster's soul was too weak.", color=discord.Color.red()))
            return

        # Generate shadow
        shadow_grade = self.calculate_shadow_grade(monster_data['rank'])
        shadow = {
            'name': monster_data['name'],
            'grade': shadow_grade,
            'level': 1,
            'exp': 0,
            'stats': {
                'hp': monster_data['hp'] // 2,
                'attack': monster_data['attack'] // 2,
                'defense': monster_data['defense'] // 2
            }
        }

        # Add shadow to hunter's army
        if 'shadows' not in hunters_data[user_id]:
            hunters_data[user_id]['shadows'] = []
        hunters_data[user_id]['shadows'].append(shadow)
        self.save_hunters_data(hunters_data)

        embed = discord.Embed(
            title="🎉 Shadow Extraction Successful!",
            description=f"Extracted a {shadow_grade} grade shadow from {monster_data['name']}!",
            color=discord.Color.green()
        )
        embed.add_field(name="Stats", value=f"HP: {shadow['stats']['hp']}\nAttack: {shadow['stats']['attack']}\nDefense: {shadow['stats']['defense']}")
        await ctx.send(embed=embed)

    @commands.command(name='train')
    async def train_shadow(self, ctx, index: int):
        """Train a shadow to increase its stats"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send(embed=discord.Embed(description="You haven't started your journey yet! Use #start first.", color=discord.Color.red()))
            return

        shadows = hunters_data[user_id].get('shadows', [])
        if not shadows or index > len(shadows) or index <= 0:
            await ctx.send(embed=discord.Embed(description="Invalid shadow index!", color=discord.Color.orange()))
            return

        shadow = shadows[index-1]

        # Training costs gold
        training_cost = 100 * shadow['level']
        if hunters_data[user_id].get('gold', 0) < training_cost:
            await ctx.send(embed=discord.Embed(description=f"You need {training_cost} gold to train this shadow!", color=discord.Color.red()))
            return

        # Training process
        hunters_data[user_id]['gold'] -= training_cost

        msg = await ctx.send("Training in progress...")
        for i in range(3):
            await asyncio.sleep(1)
            await msg.edit(content=f"Training in progress{'.'*(i+1)}")

        # Improve stats
        exp_gain = random.randint(10, 20)
        shadow['exp'] += exp_gain

        # Level up check
        while shadow['exp'] >= shadow['level'] * 100:
            shadow['exp'] -= shadow['level'] * 100
            shadow['level'] += 1
            shadow['stats']['hp'] += random.randint(5, 10)
            shadow['stats']['attack'] += random.randint(2, 5)
            shadow['stats']['defense'] += random.randint(2, 5)

        self.save_hunters_data(hunters_data)

        embed = discord.Embed(
            title="Training Complete!",
            description=f"{shadow['name']} gained {exp_gain} experience!",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Updated Stats",
            value=f"Level: {shadow['level']}\nEXP: {shadow['exp']}/{shadow['level']*100}\nHP: {shadow['stats']['hp']}\nAttack: {shadow['stats']['attack']}\nDefense: {shadow['stats']['defense']}"
        )
        await msg.edit(content="", embed=embed)

async def setup(bot):
    await bot.add_cog(ShadowArmy(bot))
