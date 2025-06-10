import discord
from discord.ext import commands
import json
import random
import asyncio
from discord.ui import View, Button

class PvPSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_duels = {}

    def load_hunters_data(self):
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_hunters_data(self, data):
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    def calculate_damage(self, attacker, defender, is_shadow=False):
        """Calculate damage based on stats"""
        if is_shadow:
            attack = attacker['stats']['attack']
            defense = defender['stats']['defense']
        else:
            attack = attacker.get('strength', 10) + attacker.get('attack_bonus', 0)
            defense = defender.get('defense_bonus', 0) + defender.get('agility', 10) // 2
        base_damage = attack - (defense // 2)
        variance = random.uniform(0.8, 1.2)
        return max(1, int(base_damage * variance))

    @commands.command(name='pvp')
    async def initiate_pvp(self, ctx, opponent: discord.Member):
        """Challenge another hunter to a PvP battle"""
        if opponent.bot:
            await ctx.send(embed=discord.Embed(description="You can't challenge a bot to a duel!", color=discord.Color.red()))
            return
        if opponent == ctx.author:
            await ctx.send(embed=discord.Embed(description="You can't duel yourself!", color=discord.Color.orange()))
            return
        hunters_data = self.load_hunters_data()
        challenger_id = str(ctx.author.id)
        opponent_id = str(opponent.id)
        if challenger_id not in hunters_data:
            await ctx.send(embed=discord.Embed(description="You haven't started your journey yet! Use #start first.", color=discord.Color.red()))
            return
        if opponent_id not in hunters_data:
            await ctx.send(embed=discord.Embed(description=f"{opponent.name} hasn't started their journey yet!", color=discord.Color.orange()))
            return
        # Check if either player is in an active duel
        if challenger_id in self.active_duels or opponent_id in self.active_duels:
            await ctx.send(embed=discord.Embed(description="One of the players is already in a duel!", color=discord.Color.orange()))
            return
        # Send challenge with buttons
        class ChallengeView(View):
            def __init__(self, parent, ctx, challenger, opponent):
                super().__init__(timeout=30)
                self.parent = parent
                self.ctx = ctx
                self.challenger = challenger
                self.opponent = opponent
                self.value = None
            @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅")
            async def accept(self, interaction: discord.Interaction, button: Button):
                if interaction.user.id != self.opponent.id:
                    await interaction.response.send_message("You are not the challenged player!", ephemeral=True)
                    return
                self.value = True
                await interaction.response.defer()
                self.stop()
            @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger, emoji="❌")
            async def decline(self, interaction: discord.Interaction, button: Button):
                if interaction.user.id != self.opponent.id:
                    await interaction.response.send_message("You are not the challenged player!", ephemeral=True)
                    return
                self.value = False
                await interaction.response.defer()
                self.stop()
        challenge_embed = discord.Embed(
            title="⚔️ PvP Challenge!",
            description=f"{opponent.mention}, you have been challenged to a duel by {ctx.author.mention}!",
            color=discord.Color.red()
        )
        view = ChallengeView(self, ctx, ctx.author, opponent)
        challenge_msg = await ctx.send(embed=challenge_embed, view=view)
        await view.wait()
        if view.value is None:
            await ctx.send(embed=discord.Embed(description="Challenge timed out!", color=discord.Color.orange()))
            return
        if not view.value:
            await ctx.send(embed=discord.Embed(description=f"{opponent.name} declined the duel!", color=discord.Color.orange()))
            return
        # Start the duel
        self.active_duels[challenger_id] = opponent_id
        self.active_duels[opponent_id] = challenger_id
        challenger = hunters_data[challenger_id]
        opponent_data = hunters_data[opponent_id]
        # Initialize battle stats
        battle_state = {
            challenger_id: {
                'hp': challenger.get('hp', 100),
                'mp': challenger.get('mp', 50),
                'data': challenger
            },
            opponent_id: {
                'hp': opponent_data.get('hp', 100),
                'mp': opponent_data.get('mp', 50),
                'data': opponent_data
            }
        }
        current_turn = challenger_id
        battle_msg = None
        # Modern UI: PvP battle loop with buttons
        while True:
            embed = discord.Embed(title="⚔️ PvP Battle", color=0xff0000)
            for pid, data in battle_state.items():
                user = self.bot.get_user(int(pid))
                embed.add_field(
                    name=f"{user.name}'s Status",
                    value=f"HP: {data['hp']}/100\nMP: {data['mp']}/50",
                    inline=True
                )
            if battle_msg:
                await battle_msg.edit(embed=embed)
            else:
                battle_msg = await ctx.send(embed=embed)
            # Get action from current player
            current_user = self.bot.get_user(int(current_turn))
            class ActionView(View):
                def __init__(self, parent, ctx, current_turn, opponent_id, battle_state):
                    super().__init__(timeout=30)
                    self.parent = parent
                    self.ctx = ctx
                    self.current_turn = current_turn
                    self.opponent_id = opponent_id
                    self.battle_state = battle_state
                    self.value = None
                @discord.ui.button(label="Attack", style=discord.ButtonStyle.primary, emoji="⚔️")
                async def attack(self, interaction: discord.Interaction, button: Button):
                    if interaction.user.id != int(self.current_turn):
                        await interaction.response.send_message("It's not your turn!", ephemeral=True)
                        return
                    self.value = 'attack'
                    await interaction.response.defer()
                    self.stop()
                @discord.ui.button(label="Use Shadow", style=discord.ButtonStyle.secondary, emoji="👻")
                async def shadow(self, interaction: discord.Interaction, button: Button):
                    if interaction.user.id != int(self.current_turn):
                        await interaction.response.send_message("It's not your turn!", ephemeral=True)
                        return
                    self.value = 'shadow'
                    await interaction.response.defer()
                    self.stop()
                @discord.ui.button(label="Defend", style=discord.ButtonStyle.success, emoji="🛡️")
                async def defend(self, interaction: discord.Interaction, button: Button):
                    if interaction.user.id != int(self.current_turn):
                        await interaction.response.send_message("It's not your turn!", ephemeral=True)
                        return
                    self.value = 'defend'
                    await interaction.response.defer()
                    self.stop()
            action_view = ActionView(self, ctx, current_turn, opponent_id if current_turn == challenger_id else challenger_id, battle_state)
            action_msg = await ctx.send(f"{current_user.mention}'s turn! Choose your action:", view=action_view)
            await action_view.wait()
            action = action_view.value
            if not action:
                await ctx.send(embed=discord.Embed(description=f"{current_user.name} took too long! Skipping turn...", color=discord.Color.orange()))
                current_turn = opponent_id if current_turn == challenger_id else challenger_id
                continue
            # Process action
            attacker = battle_state[current_turn]['data']
            defender_id = opponent_id if current_turn == challenger_id else challenger_id
            defender = battle_state[defender_id]['data']
            if action == 'attack':
                damage = self.calculate_damage(attacker, defender)
                battle_state[defender_id]['hp'] = max(0, battle_state[defender_id]['hp'] - damage)
                await ctx.send(f"{current_user.mention} attacks and deals {damage} damage!")
            elif action == 'shadow':
                # For now, treat as a special attack
                damage = self.calculate_damage(attacker, defender, is_shadow=True)
                battle_state[defender_id]['hp'] = max(0, battle_state[defender_id]['hp'] - damage)
                await ctx.send(f"{current_user.mention} uses a Shadow attack and deals {damage} damage!")
            elif action == 'defend':
                battle_state[current_turn]['hp'] = min(100, battle_state[current_turn]['hp'] + 10)
                await ctx.send(f"{current_user.mention} defends and recovers 10 HP!")
            # Check for win condition
            if battle_state[defender_id]['hp'] <= 0:
                winner = self.bot.get_user(int(current_turn))
                loser = self.bot.get_user(int(defender_id))
                await ctx.send(embed=discord.Embed(title="🏆 PvP Result", description=f"{winner.mention} has defeated {loser.mention}!", color=discord.Color.green()))
                del self.active_duels[challenger_id]
                del self.active_duels[opponent_id]
                break
            # Next turn
            current_turn = defender_id

    @commands.command(name='pvpstats')
    async def show_pvp_stats(self, ctx):
        """Show your PvP statistics"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You haven't started your journey yet! Use !start first.")
            return

        hunter = hunters_data[user_id]
        embed = discord.Embed(title=f"{ctx.author.name}'s PvP Statistics", color=0x00ff00)
        embed.add_field(name="Wins", value=str(hunter.get('pvp_wins', 0)))
        await ctx.send(embed=embed)

    @commands.command(name='accept')
    async def accept_pvp(self, ctx):
        """Accept a pending PvP challenge via command."""
        user_id = str(ctx.author.id)
        # Find a challenge where this user is the opponent
        for challenger_id, opponent_id in list(self.active_duels.items()):
            if opponent_id == user_id:
                # Simulate button accept
                await ctx.send(f"{ctx.author.mention} accepted the PvP challenge!")
                # Optionally, trigger the duel start logic here
                # For now, just remove the duel from active_duels
                del self.active_duels[challenger_id]
                del self.active_duels[opponent_id]
                return
        await ctx.send("You have no pending PvP challenges to accept.")

    @commands.command(name='decline')
    async def decline_pvp(self, ctx):
        """Decline a pending PvP challenge via command."""
        user_id = str(ctx.author.id)
        for challenger_id, opponent_id in list(self.active_duels.items()):
            if opponent_id == user_id:
                await ctx.send(f"{ctx.author.mention} declined the PvP challenge.")
                del self.active_duels[challenger_id]
                del self.active_duels[opponent_id]
                return
        await ctx.send("You have no pending PvP challenges to decline.")

async def setup(bot):
    await bot.add_cog(PvPSystem(bot))
