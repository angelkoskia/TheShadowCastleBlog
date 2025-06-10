import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import json
import asyncio
import random

class GuildSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_guilds = {}
        self.guild_raids = {}
        self.guild_wars = {}

    def load_hunters_data(self):
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_hunters_data(self, data):
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    class GuildView(View):
        def __init__(self, cog):
            super().__init__(timeout=60)
            self.cog = cog

        @discord.ui.button(label="Guild Raid", style=discord.ButtonStyle.primary, emoji="🏰")
        async def guild_raid_button(self, interaction: discord.Interaction, button: Button):
            await self.cog.start_guild_raid(interaction)

        @discord.ui.button(label="Guild War", style=discord.ButtonStyle.danger, emoji="⚔️")
        async def guild_war_button(self, interaction: discord.Interaction, button: Button):
            await self.cog.start_guild_war(interaction)

    @commands.command(name='createguild')
    async def createguild(self, ctx, *, name: str):
        """Create a new guild"""
        user_id = str(ctx.author.id)
        hunters_data = self.load_hunters_data()

        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use #start")
            return

        if any(g['leader'] == user_id for g in self.active_guilds.values()):
            await ctx.send("You already lead a guild!")
            return

        for guild in self.active_guilds.values():
            if user_id in guild['members']:
                await ctx.send("You're already in a guild!")
                return

        guild_id = str(len(self.active_guilds) + 1)
        self.active_guilds[guild_id] = {
            'name': name,
            'leader': user_id,
            'members': [user_id],
            'level': 1,
            'exp': 0
        }

        embed = discord.Embed(
            title="🏰 Guild Created!",
            description=f"Guild '{name}' has been established!",
            color=discord.Color.gold()
        )
        embed.add_field(name="Leader", value=ctx.author.mention)
        await ctx.send(embed=embed)

    @commands.command(name='guildinfo')
    async def guildinfo(self, ctx):
        """View information about your guild"""
        user_id = str(ctx.author.id)

        # Find user's guild
        guild = None
        guild_id = None
        for gid, g in self.active_guilds.items():
            if user_id in g['members']:
                guild = g
                guild_id = gid
                break

        if not guild:
            await ctx.send("You're not in a guild!")
            return

        embed = discord.Embed(
            title=f"🏰 {guild['name']}",
            description=f"Guild Level: {guild['level']}",
            color=discord.Color.gold()
        )

        # List members with their roles
        members_text = ""
        for member_id in guild['members']:
            member = ctx.guild.get_member(int(member_id))
            if member:
                role = "👑 Leader" if member_id == guild['leader'] else "👤 Member"
                members_text += f"{role} {member.mention}\n"

        embed.add_field(name="Members", value=members_text, inline=False)
        embed.add_field(name="Experience", value=f"⭐ {guild['exp']}", inline=True)

        await ctx.send(embed=embed, view=self.GuildView(self))

    @commands.command(name='guildraid')
    async def guildraid(self, ctx, *, gate_name: str = None):
        """Start a guild raid on a gate"""
        user_id = str(ctx.author.id)

        # Find user's guild
        guild = None
        guild_id = None
        for gid, g in self.active_guilds.items():
            if user_id in g['members']:
                guild = g
                guild_id = gid
                break

        if not guild:
            await ctx.send("You're not in a guild!")
            return

        if user_id != guild['leader']:
            await ctx.send("Only the guild leader can start raids!")
            return

        if not gate_name:
            await ctx.send("Please specify a gate name!")
            return

        # Start the raid
        raid_id = f"raid_{guild_id}_{len(self.guild_raids) + 1}"
        self.guild_raids[raid_id] = {
            'guild_id': guild_id,
            'gate': gate_name,
            'participants': [],
            'status': 'preparing'
        }

        embed = discord.Embed(
            title="🏰 Guild Raid Starting!",
            description=f"Raid on {gate_name} is being prepared!",
            color=discord.Color.purple()
        )
        embed.add_field(
            name="Instructions",
            value="All guild members can join using #joinraid"
        )
        await ctx.send(embed=embed)

    @commands.command(name='joinraid')
    async def joinraid(self, ctx):
        """Join an active guild raid"""
        user_id = str(ctx.author.id)

        # Find user's guild
        guild = None
        guild_id = None
        for gid, g in self.active_guilds.items():
            if user_id in g['members']:
                guild = g
                guild_id = gid
                break

        if not guild:
            await ctx.send("You're not in a guild!")
            return

        # Find active raid for this guild
        raid = None
        for r in self.guild_raids.values():
            if r['guild_id'] == guild_id and r['status'] == 'preparing':
                raid = r
                break

        if not raid:
            await ctx.send("No active raid found for your guild!")
            return

        if user_id in raid['participants']:
            await ctx.send("You've already joined this raid!")
            return

        raid['participants'].append(user_id)
        embed = discord.Embed(
            title="✅ Joined Raid",
            description=f"You've joined the raid on {raid['gate']}!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name='guildwar')
    async def guildwar(self, ctx, *, target_guild: str = None):
        """Start a guild war"""
        user_id = str(ctx.author.id)

        # Find user's guild
        guild = None
        guild_id = None
        for gid, g in self.active_guilds.items():
            if user_id in g['members']:
                guild = g
                guild_id = gid
                break

        if not guild:
            await ctx.send("You're not in a guild!")
            return

        if user_id != guild['leader']:
            await ctx.send("Only the guild leader can declare war!")
            return

        if not target_guild:
            # Show available guilds
            other_guilds = [g for gid, g in self.active_guilds.items() if gid != guild_id]
            if not other_guilds:
                await ctx.send("No other guilds available for war!")
                return

            options = [
                discord.SelectOption(
                    label=g['name'],
                    description=f"Level {g['level']} Guild"
                ) for g in other_guilds
            ]

            select = Select(
                placeholder="Choose a guild to challenge...",
                options=options
            )

            async def select_callback(interaction):
                await self.start_guild_war(interaction, select.values[0])

            select.callback = select_callback
            view = View()
            view.add_item(select)

            embed = discord.Embed(
                title="⚔️ Declare Guild War",
                description="Select a guild to challenge:",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, view=view)
        else:
            # Start war with specified guild
            target = None
            target_id = None
            for gid, g in self.active_guilds.items():
                if g['name'].lower() == target_guild.lower():
                    target = g
                    target_id = gid
                    break

            if not target:
                await ctx.send(f"Guild '{target_guild}' not found!")
                return

            await self.start_guild_war(ctx, target_id)

    async def start_guild_war(self, ctx, target_guild_id):
        """Internal method to start a guild war"""
        war_id = f"war_{len(self.guild_wars) + 1}"
        self.guild_wars[war_id] = {
            'challenger': ctx.guild_id,
            'target': target_guild_id,
            'status': 'preparing',
            'participants': {
                'challenger': [],
                'target': []
            }
        }

        challenger = self.active_guilds[ctx.guild_id]
        target = self.active_guilds[target_guild_id]

        embed = discord.Embed(
            title="⚔️ Guild War Declared!",
            description=f"{challenger['name']} has declared war on {target['name']}!",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Instructions",
            value="Members can join using #joinwar"
        )
        await ctx.send(embed=embed)

    @commands.command(name='joinwar')
    async def joinwar(self, ctx):
        """Join an active guild war"""
        user_id = str(ctx.author.id)

        # Find user's guild
        guild = None
        guild_id = None
        for gid, g in self.active_guilds.items():
            if user_id in g['members']:
                guild = g
                guild_id = gid
                break

        if not guild:
            await ctx.send("You're not in a guild!")
            return

        # Find active war for this guild
        war = None
        side = None
        for w in self.guild_wars.values():
            if w['status'] == 'preparing':
                if w['challenger'] == guild_id:
                    war = w
                    side = 'challenger'
                    break
                elif w['target'] == guild_id:
                    war = w
                    side = 'target'
                    break

        if not war:
            await ctx.send("No active war found for your guild!")
            return

        if user_id in war['participants'][side]:
            await ctx.send("You've already joined this war!")
            return

        war['participants'][side].append(user_id)
        embed = discord.Embed(
            title="✅ Joined War",
            description="You've joined the guild war!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(GuildSystem(bot))
