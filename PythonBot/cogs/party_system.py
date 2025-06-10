import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import json
import asyncio

class PartySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_parties = {}
        self.party_invites = {}

    def load_hunters_data(self):
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_hunters_data(self, data):
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    class PartyInviteView(View):
        def __init__(self, cog, leader_id, invited_ids):
            super().__init__(timeout=60)
            self.cog = cog
            self.leader_id = leader_id
            self.invited_ids = invited_ids
            self.accepted = set()
            self.declined = set()

        @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅")
        async def accept_button(self, interaction: discord.Interaction, button: Button):
            if str(interaction.user.id) not in self.invited_ids:
                await interaction.response.send_message("This invite is not for you!", ephemeral=True)
                return

            self.accepted.add(str(interaction.user.id))
            await interaction.response.send_message(f"You accepted the party invitation!", ephemeral=True)

            # Check if all members have responded
            if len(self.accepted) + len(self.declined) == len(self.invited_ids):
                await self.finalize_party(interaction)

        @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger, emoji="❌")
        async def decline_button(self, interaction: discord.Interaction, button: Button):
            if str(interaction.user.id) not in self.invited_ids:
                await interaction.response.send_message("This invite is not for you!", ephemeral=True)
                return

            self.declined.add(str(interaction.user.id))
            await interaction.response.send_message(f"You declined the party invitation!", ephemeral=True)

            # Check if all members have responded
            if len(self.accepted) + len(self.declined) == len(self.invited_ids):
                await self.finalize_party(interaction)

        async def finalize_party(self, interaction):
            if len(self.accepted) > 0:
                # Create the party
                party_members = [self.leader_id] + list(self.accepted)
                self.cog.active_parties[self.leader_id] = {
                    "members": party_members,
                    "leader": self.leader_id,
                    "status": "active"
                }

                members_mention = " ".join([f"<@{mid}>" for mid in party_members])
                embed = discord.Embed(
                    title="🎉 Party Formed!",
                    description=f"Party Members:\n{members_mention}",
                    color=discord.Color.green()
                )
                await interaction.channel.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Party Formation Failed",
                    description="All invites were declined.",
                    color=discord.Color.red()
                )
                await interaction.channel.send(embed=embed)

    @commands.command(name='startparty')
    async def startparty(self, ctx, *members: discord.Member):
        """Start a party with mentioned members"""
        if not members:
            await ctx.send("You must mention at least one member to start a party!")
            return

        if str(ctx.author.id) in self.active_parties:
            await ctx.send("You're already in a party!")
            return

        invited_ids = [str(member.id) for member in members]

        # Check if invited members are already in parties
        for member_id in invited_ids:
            if member_id in self.active_parties:
                await ctx.send(f"<@{member_id}> is already in a party!")
                return

        embed = discord.Embed(
            title="🤝 Party Invitation",
            description=f"{ctx.author.mention} wants to form a party!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Invited Members",
            value=" ".join([member.mention for member in members])
        )

        view = self.PartyInviteView(self, str(ctx.author.id), invited_ids)
        await ctx.send(embed=embed, view=view)

    @commands.command(name='leaveparty')
    async def leaveparty(self, ctx):
        """Leave your current party"""
        user_id = str(ctx.author.id)

        # Find the party the user is in
        party = None
        party_leader = None
        for leader_id, p in self.active_parties.items():
            if user_id in p['members']:
                party = p
                party_leader = leader_id
                break

        if not party:
            await ctx.send("You're not in a party!")
            return

        if user_id == party_leader:
            # Leader is leaving, disband the party
            del self.active_parties[party_leader]
            embed = discord.Embed(
                title="👋 Party Disbanded",
                description="The party leader has left. Party disbanded.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            # Member is leaving
            party['members'].remove(user_id)
            embed = discord.Embed(
                title="👋 Member Left",
                description=f"{ctx.author.mention} has left the party.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)

    @commands.command(name='partyinfo')
    async def partyinfo(self, ctx):
        """View information about your current party"""
        user_id = str(ctx.author.id)

        # Find the party the user is in
        party = None
        for p in self.active_parties.values():
            if user_id in p['members']:
                party = p
                break

        if not party:
            await ctx.send("You're not in a party!")
            return

        # Get hunter data for all party members
        hunters_data = self.load_hunters_data()

        embed = discord.Embed(
            title="👥 Party Information",
            color=discord.Color.blue()
        )

        for member_id in party['members']:
            hunter = hunters_data.get(member_id, {})
            member = ctx.guild.get_member(int(member_id))
            if member and hunter:
                member_info = f"Level {hunter.get('level', 1)} | HP: {hunter.get('hp', 0)}/{hunter.get('max_hp', 100)}"
                embed.add_field(
                    name=f"{'👑 ' if member_id == party['leader'] else ''}{member.display_name}",
                    value=member_info,
                    inline=False
                )

        await ctx.send(embed=embed)

    @commands.command(name='finished')
    async def finished(self, ctx):
        """Mark yourself as ready in party combat"""
        user_id = str(ctx.author.id)

        # Find the party the user is in
        party = None
        for p in self.active_parties.values():
            if user_id in p['members']:
                party = p
                break

        if not party:
            await ctx.send("You're not in a party!")
            return

        if not hasattr(party, 'ready_members'):
            party['ready_members'] = set()

        party['ready_members'].add(user_id)

        # Check if all members are ready
        if len(party['ready_members']) == len(party['members']):
            embed = discord.Embed(
                title="✅ All Members Ready!",
                description="The party can now proceed!",
                color=discord.Color.green()
            )
            party['ready_members'].clear()  # Reset for next round
            await ctx.send(embed=embed)
        else:
            waiting_for = [m for m in party['members'] if m not in party['ready_members']]
            embed = discord.Embed(
                title="⏳ Waiting for Members",
                description=f"Still waiting for: {' '.join([f'<@{m}>' for m in waiting_for])}",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PartySystem(bot))
