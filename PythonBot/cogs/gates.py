import discord
from discord.ext import commands
import random
import json
import asyncio
from datetime import datetime, timedelta
from discord.ui import View, Button, Select

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
            await ctx.send(embed=discord.Embed(description="You must be a registered hunter to scan for gates. Use #start first!", color=discord.Color.red()))
            return

        hunter = hunters_data[user_id]

        # Check if hunter is already in a gate
        if user_id in self.active_gates:
            await ctx.send(embed=discord.Embed(description="You are already in a gate! Complete or leave it first.", color=discord.Color.orange()))
            return

        # Determine available gate ranks based on hunter's level
        available_ranks = []
        for rank, data in self.gate_levels.items():
            if hunter['level'] >= data['min_level']:
                available_ranks.append(rank)

        if not available_ranks:
            await ctx.send(embed=discord.Embed(description="No gates available for your level!", color=discord.Color.red()))
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
                color=discord.Color.green()
            )
            embed.add_field(name="Time Limit", value="30 minutes", inline=False)
            embed.add_field(name="Status", value="Available", inline=False)
            embed.set_footer(text="Click below to enter the gate!")

            class EnterGateView(View):
                def __init__(self, parent, ctx):
                    super().__init__(timeout=60)
                    self.parent = parent
                    self.ctx = ctx

                @discord.ui.button(label="Enter Gate", style=discord.ButtonStyle.primary, emoji="⚔️")
                async def enter_button(self, interaction: discord.Interaction, button: Button):
                    if interaction.user.id != ctx.author.id:
                        await interaction.response.send_message("This isn't your gate!", ephemeral=True)
                        return
                    await interaction.response.defer()
                    await self.parent._enter_gate(ctx, interaction)
                    self.stop()

            await ctx.send(embed=embed, view=EnterGateView(self, ctx))
        else:
            await ctx.send(embed=discord.Embed(description="No gates found in your area. Try again later!", color=discord.Color.blurple()))

    async def _enter_gate(self, ctx, interaction=None):
        user_id = str(ctx.author.id)
        hunters_data = self.load_hunters_data()

        if user_id not in hunters_data:
            msg = "You must be a registered hunter to enter gates!"
            if interaction:
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        if user_id not in self.active_gates:
            msg = "No gate available! Use #scan to find a gate first."
            if interaction:
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        gate = self.active_gates[user_id]
        hunter = hunters_data[user_id]

        if datetime.now() > gate['expires']:
            del self.active_gates[user_id]
            msg = "The gate has expired! Use #scan to find a new gate."
            if interaction:
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        embed = discord.Embed(
            title="⚔️ Entering Gate",
            description=f"You've entered a Rank {gate['rank']} gate!",
            color=discord.Color.blue()
        )
        if interaction:
            await interaction.followup.send(embed=embed)
        else:
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
                    color=discord.Color.red()
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
            color=discord.Color.green()
        )
        completion_embed.add_field(name="EXP Gained", value=str(exp_gain), inline=True)
        if level_up:
            completion_embed.add_field(name="Level Up!", value=f"New Level: {hunter['level']}", inline=True)

        await ctx.send(embed=completion_embed)

        # Update hunter data
        self.save_hunters_data(hunters_data)
        del self.active_gates[user_id]

    @commands.command(name='awaken')
    async def awaken(self, ctx):
        """Begin your hunter journey at the awakening-gate (can only be used once)"""
        user_id = str(ctx.author.id)
        hunters_data = self.load_hunters_data()
        if user_id in hunters_data and hunters_data[user_id].get('awakened', False):
            await ctx.send(embed=discord.Embed(description="You have already awakened! This can only be done once.", color=discord.Color.red()))
            return
        # Simulate awakening-gate event
        hunters_data[user_id] = {
            'name': ctx.author.name,
            'level': 1,
            'exp': 0,
            'gold': 100,
            'hp': 100,
            'mp': 50,
            'strength': 10,
            'agility': 10,
            'abilities': {},
            'equipment': {},
            'inventory': [],
            'awakened': True,
            'pvp_wins': 0,
            'pvp_losses': 0,
            'monster_kills': 0,
            'deaths': 0,
            'successful_raids': 0,
            'failed_raids': 0
        }
        self.save_hunters_data(hunters_data)
        embed = discord.Embed(title="Awakening Gate", description=f"{ctx.author.mention}, you have awakened as a Hunter! Your journey begins now.", color=discord.Color.blue())
        await ctx.send(embed=embed)

    async def handle_red_gate_completion(self, ctx, user_id, victory=False):
        """Handle red gate completion or death."""
        if user_id in self.active_gates and self.active_gates[user_id]['type'] == 'red':
            gate = self.active_gates[user_id]
            if victory:
                embed = discord.Embed(
                    title="🏆 Red Gate Cleared!",
                    description="You have successfully cleared the red gate and automatically exited!",
                    color=discord.Color.gold()
                )
            else:
                embed = discord.Embed(
                    title="💀 Defeated in Red Gate",
                    description="You have been defeated and automatically ejected from the red gate!",
                    color=discord.Color.red()
                )
            del self.active_gates[user_id]
            await ctx.send(embed=embed)

    @commands.command(name='viewgates')
    async def view_gates(self, ctx):
        """View available dimensional gates with modern UI"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        if user_id not in hunters_data:
            await ctx.send(embed=discord.Embed(description="You must be registered to view gates!", color=discord.Color.red()))
            return

        hunter = hunters_data[user_id]
        available_ranks = []
        for rank, data in self.gate_levels.items():
            if hunter['level'] >= data['min_level']:
                available_ranks.append(rank)

        embed = discord.Embed(title="🌀 Available Gates", color=discord.Color.blue())
        for rank in available_ranks:
            embed.add_field(
                name=f"Rank {rank} Gate",
                value=f"Level: {self.gate_levels[rank]['min_level']}-{self.gate_levels[rank]['max_level']}\nRewards: {self.gate_levels[rank]['rewards'][0]}-{self.gate_levels[rank]['rewards'][1]} exp",
                inline=False
            )

        class GateView(View):
            def __init__(self):
                super().__init__(timeout=60)
                self.add_item(Select(
                    placeholder="Choose a gate...",
                    options=[discord.SelectOption(label=f"Rank {r} Gate", value=r) for r in available_ranks]
                ))

        await ctx.send(embed=embed, view=GateView())

    @commands.command(name='viewredgates')
    async def view_red_gates(self, ctx):
        """View all known red gates based on player rank."""
        user_id = str(ctx.author.id)
        hunters_data = self.load_hunters_data()
        if user_id not in hunters_data:
            await ctx.send(embed=discord.Embed(description="You must be a registered hunter to view red gates. Use #start first!", color=discord.Color.red()))
            return
        # Example: Red gates are only available for level 20+
        hunter = hunters_data[user_id]
        if hunter['level'] < 20:
            await ctx.send(embed=discord.Embed(description="Red gates are only available for level 20 and above!", color=discord.Color.orange()))
            return
        embed = discord.Embed(title="Known Red Gates", description="Danger: EXTREME", color=discord.Color.red())
        embed.add_field(name="Red Gate Alpha", value="Level 20+ | Boss: Blood Demon", inline=False)
        embed.add_field(name="Red Gate Omega", value="Level 30+ | Boss: Crimson Monarch", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name='entergate')
    async def enter_gate(self, ctx, *, gate_name: str):
        """Enter a basic gate by name."""
        user_id = str(ctx.author.id)
        if user_id in self.active_gates:
            await ctx.send(embed=discord.Embed(description="You are already in a gate!", color=discord.Color.orange()))
            return
        # Simulate entering a gate
        self.active_gates[user_id] = {'name': gate_name, 'type': 'normal', 'entered': True}
        embed = discord.Embed(title="Gate Entered", description=f"You have entered the gate: {gate_name}", color=discord.Color.blue())
        await ctx.send(embed=embed)

    @commands.command(name='enterredgate')
    async def enter_red_gate(self, ctx, *, gate_name: str):
        """Enter a red gate by name (restrictions apply)."""
        user_id = str(ctx.author.id)
        hunters_data = self.load_hunters_data()
        if user_id in self.active_gates:
            await ctx.send(embed=discord.Embed(description="You are already in a gate!", color=discord.Color.orange()))
            return
        hunter = hunters_data.get(user_id, {})
        if hunter.get('level', 1) < 20:
            await ctx.send(embed=discord.Embed(description="Red gates are only available for level 20 and above!", color=discord.Color.red()))
            return
        self.active_gates[user_id] = {'name': gate_name, 'type': 'red', 'entered': True}
        embed = discord.Embed(title="Red Gate Entered", description=f"You have entered the RED gate: {gate_name}. Escape is only possible if the boss is defeated or you die!", color=discord.Color.red())
        await ctx.send(embed=embed)

    @commands.command(name='exitgate')
    async def exit_gate(self, ctx):
        """Exit the current gate (restrictions for red gates)."""
        user_id = str(ctx.author.id)
        if user_id not in self.active_gates:
            await ctx.send(embed=discord.Embed(description="You are not in a gate!", color=discord.Color.orange()))
            return
        gate = self.active_gates[user_id]
        if gate['type'] == 'red':
            await ctx.send(embed=discord.Embed(description="You cannot exit a red gate unless the boss is defeated or you die!", color=discord.Color.red()))
            return
        del self.active_gates[user_id]
        await ctx.send(embed=discord.Embed(description="You have exited the gate.", color=discord.Color.green()))

    def auto_leave_red_gate(self, user_id):
        """Auto-leave a red gate after win/death."""
        if user_id in self.active_gates and self.active_gates[user_id]['type'] == 'red':
            del self.active_gates[user_id]

async def setup(bot):
    await bot.add_cog(Gates(bot))
