import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import json
import random
import asyncio

class DungeonRaids(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_dungeons = {}
        self.dungeon_invites = {}

    def load_hunters_data(self):
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_hunters_data(self, data):
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    class DungeonView(View):
        def __init__(self, cog, leader_id, dungeon_data):
            super().__init__(timeout=60)
            self.cog = cog
            self.leader_id = leader_id
            self.dungeon_data = dungeon_data

        @discord.ui.button(label="Enter Dungeon", style=discord.ButtonStyle.danger, emoji="🏰")
        async def enter_dungeon(self, interaction: discord.Interaction, button: Button):
            if str(interaction.user.id) != self.leader_id:
                await interaction.response.send_message("Only the party leader can start the dungeon!", ephemeral=True)
                return
            await self.cog.process_dungeon_entry(interaction, self.dungeon_data)

        @discord.ui.button(label="Information", style=discord.ButtonStyle.secondary, emoji="ℹ️")
        async def dungeon_info(self, interaction: discord.Interaction, button: Button):
            await self.cog.show_dungeon_info(interaction, self.dungeon_data)

    @commands.command(name='dungeons')
    async def dungeons(self, ctx):
        """View available dungeon raids"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use #start")
            return

        # Check if user is in a party
        party_cog = self.bot.get_cog('PartySystem')
        if not party_cog or not party_cog.is_in_party(user_id):
            await ctx.send("You need to be in a party to view dungeons! Use #startparty to create one.")
            return

        # Check if user is party leader
        if not party_cog.is_party_leader(user_id):
            await ctx.send("Only the party leader can view dungeons!")
            return

        hunter = hunters_data[user_id]
        rank = hunter['rank']

        # Generate available dungeons based on party average level
        party_members = party_cog.get_party_members(user_id)
        avg_level = self.calculate_party_average_level(party_members)
        available_dungeons = self.generate_dungeons(rank, avg_level)

        embed = discord.Embed(
            title="🏰 Available Dungeons",
            description=f"Party Average Level: {avg_level}",
            color=discord.Color.purple()
        )

        for dungeon in available_dungeons:
            embed.add_field(
                name=f"{dungeon['name']}",
                value=f"Level: {dungeon['level']}\nFloors: {dungeon['floors']}\nDifficulty: {dungeon['difficulty']}\nStatus: {dungeon['status']}",
                inline=True
            )

        embed.set_footer(text="Use #enterdungeon <name> to enter a dungeon")
        await ctx.send(embed=embed, view=self.DungeonView(self, user_id, available_dungeons[0]))

    @commands.command(name='enterdungeon')
    async def enterdungeon(self, ctx, *, dungeon_name: str = None):
        """Enter a dungeon raid"""
        if not dungeon_name:
            await ctx.send("Please specify a dungeon name! Use #dungeons to see available dungeons.")
            return

        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        party_cog = self.bot.get_cog('PartySystem')
        if not party_cog or not party_cog.is_in_party(user_id):
            await ctx.send("You need to be in a party to enter dungeons!")
            return

        if not party_cog.is_party_leader(user_id):
            await ctx.send("Only the party leader can initiate dungeon entry!")
            return

        # Get party members and create dungeon session
        party_members = party_cog.get_party_members(user_id)
        dungeon_id = f"dungeon_{user_id}_{len(self.active_dungeons) + 1}"

        self.active_dungeons[dungeon_id] = {
            'name': dungeon_name,
            'leader': user_id,
            'members': party_members,
            'floor': 1,
            'status': 'active',
            'ready_members': set(),
            'rewards': {
                'exp': 0,
                'gold': 0,
                'items': []
            }
        }

        embed = discord.Embed(
            title="🏰 Dungeon Entry",
            description=f"Entering {dungeon_name}!\nAll party members must type #accept to begin.",
            color=discord.Color.purple()
        )
        embed.add_field(
            name="Party Members",
            value="\n".join([f"<@{m}>" for m in party_members]),
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command(name='exitdungeon')
    async def exitdungeon(self, ctx):
        """Flee the current dungeon"""
        user_id = str(ctx.author.id)

        # Find user's dungeon
        dungeon_id = None
        for d_id, dungeon in self.active_dungeons.items():
            if user_id in dungeon['members']:
                dungeon_id = d_id
                break

        if not dungeon_id:
            await ctx.send("You're not in a dungeon!")
            return

        dungeon = self.active_dungeons[dungeon_id]
        if user_id != dungeon['leader']:
            await ctx.send("Only the party leader can initiate dungeon exit!")
            return

        # Create confirmation message
        embed = discord.Embed(
            title="⚠️ Dungeon Exit",
            description="Are you sure you want to flee the dungeon? All progress will be lost!",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="Current Progress",
            value=f"Floor: {dungeon['floor']}\nRewards accumulated:\n- EXP: {dungeon['rewards']['exp']}\n- Gold: {dungeon['rewards']['gold']}\n- Items: {len(dungeon['rewards']['items'])}",
            inline=False
        )

        # Add confirmation buttons
        class ConfirmView(View):
            def __init__(self):
                super().__init__(timeout=30)

            @discord.ui.button(label="Confirm Exit", style=discord.ButtonStyle.danger)
            async def confirm(self, interaction: discord.Interaction, button: Button):
                if str(interaction.user.id) != dungeon['leader']:
                    await interaction.response.send_message("Only the party leader can confirm exit!", ephemeral=True)
                    return

                # Process dungeon exit
                del self.active_dungeons[dungeon_id]
                embed = discord.Embed(
                    title="🚪 Dungeon Exited",
                    description="Your party has fled the dungeon.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, interaction: discord.Interaction, button: Button):
                if str(interaction.user.id) != dungeon['leader']:
                    await interaction.response.send_message("Only the party leader can cancel!", ephemeral=True)
                    return
                await interaction.response.send_message("Dungeon exit cancelled.", ephemeral=True)

        await ctx.send(embed=embed, view=ConfirmView())

    def calculate_party_average_level(self, member_ids):
        """Calculate average party level"""
        hunters_data = self.load_hunters_data()
        total_level = 0
        valid_members = 0

        for member_id in member_ids:
            if member_id in hunters_data:
                total_level += hunters_data[member_id].get('level', 1)
                valid_members += 1

        return max(1, total_level // valid_members)

    def generate_dungeons(self, rank, avg_level):
        """Generate available dungeons based on party rank and level"""
        dungeons = []
        rank_multiplier = {
            'S': 2.0,
            'A': 1.5,
            'B': 1.2,
            'C': 1.0,
            'D': 0.8,
            'E': 0.6
        }

        multiplier = rank_multiplier.get(rank, 0.6)
        base_level = avg_level * multiplier

        dungeon_types = [
            ("Ancient Ruins", 1.0),
            ("Dark Cave", 1.2),
            ("Demon Castle", 1.5),
            ("Dragon's Lair", 2.0)
        ]

        for name, difficulty_mult in dungeon_types:
            level = int(base_level * difficulty_mult)
            dungeons.append({
                'name': name,
                'level': level,
                'floors': random.randint(3, 7),
                'difficulty': self.calculate_difficulty(level),
                'status': random.choice(['Active', 'Unstable', 'Dangerous']),
                'rewards_multiplier': difficulty_mult
            })

        return dungeons

    def calculate_difficulty(self, level):
        """Calculate dungeon difficulty based on level"""
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

    async def process_dungeon_entry(self, interaction, dungeon_data):
        """Process dungeon entry request"""
        user_id = str(interaction.user.id)
        party_cog = self.bot.get_cog('PartySystem')

        if not party_cog or not party_cog.is_party_leader(user_id):
            await interaction.response.send_message("Only the party leader can enter dungeons!", ephemeral=True)
            return

        # Create embed for party confirmation
        embed = discord.Embed(
            title="🏰 Dungeon Entry Request",
            description=f"Preparing to enter {dungeon_data['name']}",
            color=discord.Color.purple()
        )
        embed.add_field(
            name="Dungeon Info",
            value=f"Level: {dungeon_data['level']}\nFloors: {dungeon_data['floors']}\nDifficulty: {dungeon_data['difficulty']}",
            inline=False
        )

        # Add party confirmation UI
        class ConfirmView(View):
            def __init__(self):
                super().__init__(timeout=60)
                self.ready_members = set()

            @discord.ui.button(label="Ready", style=discord.ButtonStyle.success)
            async def ready(self, interaction: discord.Interaction, button: Button):
                member_id = str(interaction.user.id)
                if member_id not in party_cog.get_party_members(user_id):
                    await interaction.response.send_message("You're not in this party!", ephemeral=True)
                    return

                self.ready_members.add(member_id)
                await interaction.response.send_message(f"Ready! ({len(self.ready_members)}/{len(party_cog.get_party_members(user_id))})", ephemeral=True)

                # Check if all members are ready
                if self.ready_members == set(party_cog.get_party_members(user_id)):
                    await self.start_dungeon(interaction)

            async def start_dungeon(self, interaction):
                dungeon_id = f"dungeon_{user_id}_{len(self.active_dungeons) + 1}"
                self.active_dungeons[dungeon_id] = {
                    'name': dungeon_data['name'],
                    'data': dungeon_data,
                    'leader': user_id,
                    'members': list(self.ready_members),
                    'floor': 1,
                    'status': 'active'
                }

                embed = discord.Embed(
                    title="🏰 Dungeon Started!",
                    description=f"Your party has entered {dungeon_data['name']}!",
                    color=discord.Color.green()
                )
                await interaction.channel.send(embed=embed)

        await interaction.response.send_message(embed=embed, view=ConfirmView())

    async def show_dungeon_info(self, interaction, dungeon_data):
        """Show detailed dungeon information"""
        embed = discord.Embed(
            title=f"🏰 {dungeon_data['name']} Information",
            color=discord.Color.purple()
        )

        embed.add_field(
            name="Basic Info",
            value=f"Level: {dungeon_data['level']}\nFloors: {dungeon_data['floors']}\nDifficulty: {dungeon_data['difficulty']}",
            inline=False
        )

        embed.add_field(
            name="Rewards",
            value=f"EXP Multiplier: {dungeon_data['rewards_multiplier']}x\nGold Multiplier: {dungeon_data['rewards_multiplier']}x",
            inline=False
        )

        embed.add_field(
            name="Status",
            value=f"Current Status: {dungeon_data['status']}",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(DungeonRaids(bot))
