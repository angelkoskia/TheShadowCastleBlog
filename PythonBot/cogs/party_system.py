import discord
from discord.ext import commands
from discord.ui import View, Button
import json

class PartySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_parties = {}  # {party_id: {leader, members, invited, dungeon, state}}

    def load_hunters_data(self):
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_hunters_data(self, data):
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    @commands.command(name='startparty')
    async def start_party(self, ctx, *members: discord.Member):
        """Start a party and invite members (modern UI)"""
        leader_id = str(ctx.author.id)
        if leader_id in self.active_parties:
            await ctx.send("You are already leading a party.")
            return
        party_id = leader_id
        party = {
            'leader': leader_id,
            'members': [leader_id],
            'invited': [str(m.id) for m in members],
            'dungeon': None,
            'state': 'waiting',
            'finished': set()
        }
        self.active_parties[party_id] = party
        embed = discord.Embed(title="Party Invitation", description=f"{ctx.author.mention} has invited: " + ", ".join(m.mention for m in members), color=discord.Color.blue())
        view = PartyInviteView(self, party_id, members)
        await ctx.send(embed=embed, view=view)

    @commands.command(name='accept')
    async def accept_party(self, ctx):
        """Accept a party invitation"""
        user_id = str(ctx.author.id)
        for party_id, party in self.active_parties.items():
            if user_id in party['invited']:
                party['invited'].remove(user_id)
                party['members'].append(user_id)
                await ctx.send(f"{ctx.author.mention} joined the party!")
                return
        await ctx.send("You have no pending party invites.")

    @commands.command(name='decline')
    async def decline_party(self, ctx):
        """Decline a party invitation"""
        user_id = str(ctx.author.id)
        for party_id, party in self.active_parties.items():
            if user_id in party['invited']:
                party['invited'].remove(user_id)
                await ctx.send(f"{ctx.author.mention} declined the party invite.")
                return
        await ctx.send("You have no pending party invites.")

    async def display_party_stats(self, ctx, party):
        """Display party stats in an embed after each turn."""
        hunters_data = self.load_hunters_data()
        embed = discord.Embed(title="Party Stats", color=discord.Color.green())
        for member_id in party['members']:
            hunter = hunters_data.get(member_id)
            if hunter:
                embed.add_field(
                    name=hunter.get('name', f'User {member_id}'),
                    value=f"HP: {hunter.get('hp', 100)} | MP: {hunter.get('mp', 50)} | Level: {hunter.get('level', 1)}",
                    inline=False
                )
        await ctx.send(embed=embed)

    @commands.command(name='refuse')
    async def refuse_party(self, ctx):
        """Refuse a party or dungeon invitation (alias for decline)"""
        await self.decline_party(ctx)

    @commands.command(name='finished')
    async def finished_turn(self, ctx):
        """Mark your turn as finished in party/guild combat. Auto-disbands party after battle."""
        user_id = str(ctx.author.id)
        for party_id, party in list(self.active_parties.items()):
            if user_id in party['members']:
                party['finished'].add(user_id)
                await ctx.send(f"{ctx.author.mention} is ready!")
                await self.display_party_stats(ctx, party)
                # If all members are finished, progress turn and disband party
                if set(party['members']) == party['finished']:
                    await ctx.send("All party members are ready! The turn progresses. Party will now disband.")
                    del self.active_parties[party_id]  # Auto-disband the party
                return
        await ctx.send("You are not in a party.")

    @commands.command(name='dungeons')
    async def view_dungeons(self, ctx):
        """View available dungeon raids (party/guild only)"""
        user_id = str(ctx.author.id)
        for party_id, party in self.active_parties.items():
            if user_id in party['members']:
                # Example dungeons
                dungeons = ["Spider Nest", "Demon Castle", "Red Gate"]
                embed = discord.Embed(title="Available Dungeons", description="Select a dungeon to enter:", color=discord.Color.purple())
                for d in dungeons:
                    embed.add_field(name=d, value="Danger: High", inline=False)
                await ctx.send(embed=embed)
                return
        await ctx.send("You must be in a party to view dungeons.")

    @commands.command(name='enterdungeon')
    async def enter_dungeon(self, ctx, *, dungeon_name: str):
        """Enter a dungeon as party leader"""
        user_id = str(ctx.author.id)
        if user_id not in self.active_parties:
            await ctx.send("You are not leading a party.")
            return
        party = self.active_parties[user_id]
        if party['leader'] != user_id:
            await ctx.send("Only the party leader can start a dungeon.")
            return
        party['dungeon'] = dungeon_name
        party['state'] = 'in_dungeon'
        await ctx.send(f"Party has entered the dungeon: {dungeon_name}!")

    @commands.command(name='exitdungeon')
    async def exit_dungeon(self, ctx):
        """Flee the dungeon with all party members"""
        user_id = str(ctx.author.id)
        for party_id, party in list(self.active_parties.items()):
            if user_id in party['members'] and party['state'] == 'in_dungeon':
                await ctx.send("The party has fled the dungeon!")
                del self.active_parties[party_id]
                return
        await ctx.send("You are not in a dungeon with your party.")

    class CombatView(View):
        def __init__(self, cog, party_id):
            super().__init__(timeout=180)
            self.cog = cog
            self.party_id = party_id

        @discord.ui.button(label="Attack", style=discord.ButtonStyle.danger, emoji="⚔️")
        async def attack_button(self, interaction: discord.Interaction, button: Button):
            await self.handle_combat_action(interaction, "attack")

        @discord.ui.button(label="Defend", style=discord.ButtonStyle.primary, emoji="🛡️")
        async def defend_button(self, interaction: discord.Interaction, button: Button):
            await self.handle_combat_action(interaction, "defend")

        @discord.ui.button(label="Use Ability", style=discord.ButtonStyle.success, emoji="✨")
        async def ability_button(self, interaction: discord.Interaction, button: Button):
            await self.handle_combat_action(interaction, "ability")

        async def handle_combat_action(self, interaction: discord.Interaction, action_type: str):
            party = self.cog.active_parties.get(self.party_id)
            if not party:
                await interaction.response.send_message("Party no longer exists!", ephemeral=True)
                return
            if str(interaction.user.id) not in party['members']:
                await interaction.response.send_message("You're not in this party!", ephemeral=True)
                return
            # Handle the combat action
            await interaction.response.defer()
            await self.cog.display_party_stats(await self.cog.bot.get_context(interaction.message), party)
            # Update turn status
            await interaction.followup.send(f"{interaction.user.mention} used {action_type}!", ephemeral=False)

    @commands.command(name='startcombat')
    async def start_combat(self, ctx):
        """Start party combat with modern UI"""
        user_id = str(ctx.author.id)
        for party_id, party in self.active_parties.items():
            if user_id in party['members']:
                embed = discord.Embed(title="⚔️ Party Combat", color=discord.Color.blue())
                embed.add_field(name="Status", value="Combat started! Choose your actions.", inline=False)
                view = self.CombatView(self, party_id)
                await ctx.send(embed=embed, view=view)
                return
        await ctx.send("You must be in a party to start combat!")

class PartyInviteView(View):
    def __init__(self, cog, party_id, members):
        super().__init__(timeout=60)
        self.cog = cog
        self.party_id = party_id
        self.members = members
        for m in members:
            self.add_item(Button(label=f"Accept ({m.display_name})", style=discord.ButtonStyle.success, custom_id=f"accept_{m.id}"))
            self.add_item(Button(label=f"Decline ({m.display_name})", style=discord.ButtonStyle.danger, custom_id=f"decline_{m.id}"))
    async def interaction_check(self, interaction):
        return str(interaction.user.id) in [str(m.id) for m in self.members]
    async def on_timeout(self):
        pass
    async def on_error(self, error, item, interaction):
        await interaction.response.send_message("An error occurred.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(PartySystem(bot))
