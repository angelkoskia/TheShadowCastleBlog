import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import json
import random
import asyncio

class GatesSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_gates = {}
        self.red_gates = {}
        self.dungeon_sessions = {}

    def load_hunters_data(self):
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_hunters_data(self, data):
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    class GateView(View):
        def __init__(self, cog, user_id, gate_type="normal"):
            super().__init__(timeout=60)
            self.cog = cog
            self.user_id = user_id
            self.gate_type = gate_type

        @discord.ui.button(label="Enter Gate", style=discord.ButtonStyle.primary, emoji="🌀")
        async def enter_gate(self, interaction: discord.Interaction, button: Button):
            if str(interaction.user.id) != self.user_id:
                await interaction.response.send_message("This gate is not for you!", ephemeral=True)
                return
            await self.cog.process_gate_entry(interaction, self.gate_type)

        @discord.ui.button(label="Information", style=discord.ButtonStyle.secondary, emoji="ℹ️")
        async def gate_info(self, interaction: discord.Interaction, button: Button):
            await self.cog.show_gate_info(interaction, self.gate_type)

    @commands.command(name='viewgates')
    async def viewgates(self, ctx):
        """View available dimensional gates based on your rank"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use #start")
            return

        hunter = hunters_data[user_id]
        rank = hunter['rank']

        # Generate available gates based on rank
        available_gates = self.generate_gates(rank)

        embed = discord.Embed(
            title="🌀 Available Gates",
            description=f"Current Rank: {rank}",
            color=discord.Color.blue()
        )

        for gate in available_gates:
            embed.add_field(
                name=f"Gate {gate['id']}",
                value=f"Level: {gate['level']}\nDifficulty: {gate['difficulty']}\nStatus: {gate['status']}",
                inline=True
            )

        embed.set_footer(text="Use #entergate <id> to enter a gate")
        await ctx.send(embed=embed, view=self.GateView(self, user_id))

    @commands.command(name='viewredgates')
    async def viewredgates(self, ctx):
        """View all known red gates based on player rank"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use #start")
            return

        hunter = hunters_data[user_id]
        rank = hunter['rank']

        # Generate red gates based on rank
        red_gates = self.generate_red_gates(rank)

        if not red_gates:
            await ctx.send("No red gates detected in your area!")
            return

        embed = discord.Embed(
            title="🔴 Red Gates Detected",
            description="Warning: Red Gates are extremely dangerous!",
            color=discord.Color.red()
        )

        for gate in red_gates:
            embed.add_field(
                name=f"Red Gate {gate['id']}",
                value=f"Level: {gate['level']}\nThreat Level: {gate['threat']}\nStatus: {gate['status']}",
                inline=True
            )

        embed.set_footer(text="Use #enterredgate <id> to enter a red gate")
        await ctx.send(embed=embed, view=self.GateView(self, user_id, "red"))

    @commands.command(name='entergate')
    async def entergate(self, ctx, gate_id: str = None):
        """Enter a basic gate"""
        if not gate_id:
            await ctx.send("Please specify a gate ID! Use #viewgates to see available gates.")
            return

        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use #start")
            return

        # Check if player is already in a gate
        if user_id in self.active_gates:
            await ctx.send("You're already in a gate! Use #exitgate first.")
            return

        # Start gate session
        self.active_gates[user_id] = {
            'gate_id': gate_id,
            'level': 1,
            'monsters_defeated': 0,
            'rewards': {
                'exp': 0,
                'gold': 0,
                'items': []
            }
        }

        embed = discord.Embed(
            title="🌀 Gate Entry",
            description=f"You've entered Gate {gate_id}!",
            color=discord.Color.blue()
        )
        embed.add_field(name="Instructions", value="Use #hunt to find monsters\nUse #exitgate to leave")
        await ctx.send(embed=embed)

    @commands.command(name='enterredgate')
    async def enterredgate(self, ctx, gate_id: str = None):
        """Enter a red gate"""
        if not gate_id:
            await ctx.send("Please specify a red gate ID! Use #viewredgates to see available gates.")
            return

        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use #start")
            return

        hunter = hunters_data[user_id]
        if hunter['rank'] not in ['S', 'A']:
            await ctx.send("Your rank is too low to enter red gates! Only S and A rank hunters can enter.")
            return

        # Check if player is already in a gate
        if user_id in self.active_gates or user_id in self.red_gates:
            await ctx.send("You're already in a gate!")
            return

        # Start red gate session
        self.red_gates[user_id] = {
            'gate_id': gate_id,
            'level': 1,
            'boss_alive': True,
            'monsters_defeated': 0,
            'rewards': {
                'exp': 0,
                'gold': 0,
                'items': []
            }
        }

        embed = discord.Embed(
            title="🔴 Red Gate Entry",
            description=f"You've entered Red Gate {gate_id}!\nWarning: You cannot exit until the boss is defeated!",
            color=discord.Color.red()
        )
        embed.add_field(name="Instructions", value="Use #hunt to find monsters\nDefeat the boss to escape!")
        await ctx.send(embed=embed)

    @commands.command(name='exitgate')
    async def exitgate(self, ctx):
        """Exit the current gate"""
        user_id = str(ctx.author.id)

        # Check red gates first
        if user_id in self.red_gates:
            if self.red_gates[user_id]['boss_alive']:
                embed = discord.Embed(
                    title="❌ Cannot Exit",
                    description="You must defeat the boss to exit a red gate!",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
            else:
                gate_data = self.red_gates[user_id]
                del self.red_gates[user_id]
        elif user_id in self.active_gates:
            gate_data = self.active_gates[user_id]
            del self.active_gates[user_id]
        else:
            await ctx.send("You're not in any gate!")
            return

        # Calculate final rewards
        hunters_data = self.load_hunters_data()
        if user_id in hunters_data:
            hunter = hunters_data[user_id]
            hunter['exp'] += gate_data['rewards']['exp']
            hunter['gold'] = hunter.get('gold', 0) + gate_data['rewards']['gold']

            # Add items to inventory
            if 'inventory' not in hunter:
                hunter['inventory'] = []
            hunter['inventory'].extend(gate_data['rewards']['items'])

            self.save_hunters_data(hunters_data)

        embed = discord.Embed(
            title="🚪 Gate Exit",
            description="You've successfully left the gate!",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Final Rewards",
            value=f"EXP: {gate_data['rewards']['exp']}\nGold: {gate_data['rewards']['gold']}\nItems: {len(gate_data['rewards']['items'])}",
            inline=False
        )
        embed.add_field(
            name="Statistics",
            value=f"Monsters Defeated: {gate_data['monsters_defeated']}\nLevels Cleared: {gate_data['level']}",
            inline=False
        )
        await ctx.send(embed=embed)

    def generate_gates(self, rank):
        """Generate available gates based on hunter rank"""
        rank_levels = {
            'S': range(80, 101),
            'A': range(60, 81),
            'B': range(40, 61),
            'C': range(20, 41),
            'D': range(10, 21),
            'E': range(1, 11)
        }

        levels = rank_levels.get(rank, range(1, 11))
        gates = []

        for i in range(3):  # Generate 3 gates
            level = random.choice(list(levels))
            gates.append({
                'id': f"{rank}{i+1}",
                'level': level,
                'difficulty': self.calculate_difficulty(level),
                'status': random.choice(['Active', 'Unstable', 'Stable'])
            })

        return gates

    def generate_red_gates(self, rank):
        """Generate red gates based on hunter rank"""
        if rank not in ['S', 'A']:
            return []

        red_gates = []
        base_level = 90 if rank == 'S' else 70

        for i in range(2):  # Generate 2 red gates
            level = base_level + random.randint(0, 10)
            red_gates.append({
                'id': f"R{rank}{i+1}",
                'level': level,
                'threat': 'Catastrophic' if level > 95 else 'Extreme',
                'status': random.choice(['Unstable', 'Volatile', 'Critical'])
            })

        return red_gates

    def calculate_difficulty(self, level):
        """Calculate gate difficulty based on level"""
        if level >= 90:
            return 'Extreme'
        elif level >= 70:
            return 'Very Hard'
        elif level >= 50:
            return 'Hard'
        elif level >= 30:
            return 'Medium'
        else:
            return 'Easy'

    async def process_gate_entry(self, interaction, gate_type):
        """Process gate entry request"""
        user_id = str(interaction.user.id)
        hunters_data = self.load_hunters_data()

        if user_id not in hunters_data:
            await interaction.response.send_message("You need to start your journey first! Use #start", ephemeral=True)
            return

        if gate_type == "red" and hunters_data[user_id]['rank'] not in ['S', 'A']:
            await interaction.response.send_message("Your rank is too low to enter red gates!", ephemeral=True)
            return

        if user_id in self.active_gates or user_id in self.red_gates:
            await interaction.response.send_message("You're already in a gate!", ephemeral=True)
            return

        # Create gate session
        if gate_type == "red":
            self.red_gates[user_id] = {
                'gate_id': f"R{hunters_data[user_id]['rank']}1",
                'level': 1,
                'boss_alive': True,
                'monsters_defeated': 0,
                'rewards': {'exp': 0, 'gold': 0, 'items': []}
            }
            color = discord.Color.red()
            title = "🔴 Red Gate Entry"
        else:
            self.active_gates[user_id] = {
                'gate_id': f"{hunters_data[user_id]['rank']}1",
                'level': 1,
                'monsters_defeated': 0,
                'rewards': {'exp': 0, 'gold': 0, 'items': []}
            }
            color = discord.Color.blue()
            title = "🌀 Gate Entry"

        embed = discord.Embed(
            title=title,
            description="You've entered the gate!\nUse #hunt to find monsters",
            color=color
        )
        await interaction.response.send_message(embed=embed)

    async def show_gate_info(self, interaction, gate_type):
        """Show detailed gate information"""
        user_id = str(interaction.user.id)
        hunters_data = self.load_hunters_data()

        if user_id not in hunters_data:
            await interaction.response.send_message("You need to start your journey first! Use #start", ephemeral=True)
            return

        rank = hunters_data[user_id]['rank']
        if gate_type == "red":
            gates = self.generate_red_gates(rank)
            color = discord.Color.red()
            title = "🔴 Red Gate Information"
        else:
            gates = self.generate_gates(rank)
            color = discord.Color.blue()
            title = "🌀 Gate Information"

        embed = discord.Embed(title=title, color=color)
        for gate in gates:
            info = f"Level: {gate['level']}\n"
            info += f"{'Threat' if gate_type == 'red' else 'Difficulty'}: {gate.get('threat', gate.get('difficulty'))}\n"
            info += f"Status: {gate['status']}"
            embed.add_field(name=f"Gate {gate['id']}", value=info, inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(GatesSystem(bot))
