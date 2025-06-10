import discord
from discord.ext import commands
import random
import json
import asyncio
from datetime import datetime, timedelta

class Gates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_gates = {}
        self.gate_levels = {
            'E': {'min_level': 1, 'max_level': 10, 'rewards': (50, 150)},
            'D': {'min_level': 11, 'max_level': 20, 'rewards': (150, 300)},
            'C': {'min_level': 21, 'max_level': 30, 'rewards': (300, 600)},
            'B': {'min_level': 31, 'max_level': 40, 'rewards': (600, 1200)},
            'A': {'min_level': 41, 'max_level': 50, 'rewards': (1200, 2400)},
            'S': {'min_level': 51, 'max_level': 60, 'rewards': (2400, 5000)}
        }

    def load_hunters_data(self):
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_hunters_data(self, data):
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    @commands.command(name='scan')
    async def scan_for_gates(self, ctx):
        """Scan the area for gates"""
        user_id = str(ctx.author.id)
        hunters_data = self.load_hunters_data()

        if user_id not in hunters_data:
            await ctx.send("You must be a registered hunter to scan for gates. Use !start first!")
            return

        hunter = hunters_data[user_id]

        # Check if hunter is already in a gate
        if user_id in self.active_gates:
            await ctx.send("You are already in a gate! Complete or leave it first.")
            return

        # Determine available gate ranks based on hunter's level
        available_ranks = []
        for rank, data in self.gate_levels.items():
            if hunter['level'] >= data['min_level']:
                available_ranks.append(rank)

        if not available_ranks:
            await ctx.send("No gates available for your level!")
            return

        # Random chance to find a gate
        if random.random() < 0.7:  # 70% chance to find a gate
            rank = random.choice(available_ranks)
            gate_level = random.randint(
                self.gate_levels[rank]['min_level'],
                self.gate_levels[rank]['max_level']
            )

            self.active_gates[user_id] = {
                'rank': rank,
                'level': gate_level,
                'status': 'available',
                'expires': datetime.now() + timedelta(minutes=30)
            }

            embed = discord.Embed(
                title="🌀 Gate Detected!",
                description=f"A Rank {rank} gate has appeared!\nGate Level: {gate_level}",
                color=0x00ff00
            )
            embed.add_field(name="Time Limit", value="30 minutes", inline=False)
            embed.add_field(name="Status", value="Available", inline=False)
            embed.set_footer(text="Use !enter to enter the gate")

            await ctx.send(embed=embed)
        else:
            await ctx.send("No gates found in your area. Try again later!")

    @commands.command(name='enter')
    async def enter_gate(self, ctx):
        """Enter an available gate"""
        user_id = str(ctx.author.id)
        hunters_data = self.load_hunters_data()

        if user_id not in hunters_data:
            await ctx.send("You must be a registered hunter to enter gates!")
            return

        if user_id not in self.active_gates:
            await ctx.send("No gate available! Use !scan to find a gate first.")
            return

        gate = self.active_gates[user_id]
        hunter = hunters_data[user_id]

        if datetime.now() > gate['expires']:
            del self.active_gates[user_id]
            await ctx.send("The gate has expired! Use !scan to find a new gate.")
            return

        # Start the dungeon sequence
        embed = discord.Embed(
            title="⚔️ Entering Gate",
            description=f"You've entered a Rank {gate['rank']} gate!",
            color=0x0000ff
        )
        await ctx.send(embed=embed)

        # Simulate dungeon progress
        progress_msg = await ctx.send("Progress: 0%")
        for i in range(5):
            await asyncio.sleep(3)
            await progress_msg.edit(content=f"Progress: {(i+1)*20}%")

            # Random encounter
            if random.random() < 0.5:
                monster_level = gate['level']
                damage_taken = random.randint(5, 15)
                hunter['hp'] = max(0, hunter['hp'] - damage_taken)

                encounter_embed = discord.Embed(
                    title="⚔️ Monster Encountered!",
                    description=f"You took {damage_taken} damage!",
                    color=0xff0000
                )
                await ctx.send(embed=encounter_embed)

                if hunter['hp'] <= 0:
                    await ctx.send("You have been defeated! You'll need to rest and recover.")
                    hunter['hp'] = 50  # Partial recovery
                    self.save_hunters_data(hunters_data)
                    del self.active_gates[user_id]
                    return

        # Gate completion rewards
        exp_gain = random.randint(
            self.gate_levels[gate['rank']]['rewards'][0],
            self.gate_levels[gate['rank']]['rewards'][1]
        )
        hunter['exp'] += exp_gain

        # Level up check
        level_up = False
        while hunter['exp'] >= (hunter['level'] * 100):
            hunter['exp'] -= (hunter['level'] * 100)
            hunter['level'] += 1
            level_up = True

        completion_embed = discord.Embed(
            title="🎉 Gate Cleared!",
            description=f"Congratulations! You've cleared the Rank {gate['rank']} gate!",
            color=0x00ff00
        )
        completion_embed.add_field(name="EXP Gained", value=str(exp_gain), inline=True)
        if level_up:
            completion_embed.add_field(name="Level Up!", value=f"New Level: {hunter['level']}", inline=True)

        await ctx.send(embed=completion_embed)

        # Update hunter data
        self.save_hunters_data(hunters_data)
        del self.active_gates[user_id]

async def setup(bot):
    await bot.add_cog(Gates(bot))
