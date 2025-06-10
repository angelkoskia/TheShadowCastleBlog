import discord
from discord.ext import commands
import json
import random
import asyncio

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
            await ctx.send("You can't challenge a bot to a duel!")
            return

        if opponent == ctx.author:
            await ctx.send("You can't duel yourself!")
            return

        hunters_data = self.load_hunters_data()
        challenger_id = str(ctx.author.id)
        opponent_id = str(opponent.id)

        if challenger_id not in hunters_data:
            await ctx.send("You haven't started your journey yet! Use !start first.")
            return

        if opponent_id not in hunters_data:
            await ctx.send(f"{opponent.name} hasn't started their journey yet!")
            return

        # Check if either player is in an active duel
        if challenger_id in self.active_duels or opponent_id in self.active_duels:
            await ctx.send("One of the players is already in a duel!")
            return

        # Send challenge
        challenge_msg = await ctx.send(
            f"{opponent.mention}, you have been challenged to a duel by {ctx.author.mention}!\n"
            f"React with ✅ to accept or ❌ to decline. (30 seconds to respond)"
        )
        await challenge_msg.add_reaction("✅")
        await challenge_msg.add_reaction("❌")

        def check(reaction, user):
            return user == opponent and str(reaction.emoji) in ["✅", "❌"]

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Challenge timed out!")
            return

        if str(reaction.emoji) == "❌":
            await ctx.send(f"{opponent.name} declined the duel!")
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

        # Battle loop
        current_turn = challenger_id
        battle_msg = None

        while True:
            # Update battle display
            embed = discord.Embed(title="⚔️ PvP Battle", color=0xff0000)

            for pid, data in battle_state.items():
                user = self.bot.get_user(int(pid))
                embed.add_field(
                    name=f"{user.name}'s Status",
                    value=f"HP: {data['hp']}/{100}\nMP: {data['mp']}/{50}",
                    inline=True
                )

            if battle_msg:
                await battle_msg.edit(embed=embed)
            else:
                battle_msg = await ctx.send(embed=embed)

            # Get action from current player
            current_user = self.bot.get_user(int(current_turn))
            action_msg = await ctx.send(
                f"{current_user.mention}'s turn!\n"
                "Choose your action:\n"
                "1️⃣ Attack\n"
                "2️⃣ Use Shadow (if available)\n"
                "3️⃣ Defend"
            )

            for emoji in ["1️⃣", "2️⃣", "3️⃣"]:
                await action_msg.add_reaction(emoji)

            def action_check(reaction, user):
                return user.id == int(current_turn) and str(reaction.emoji) in ["1️⃣", "2️⃣", "3️⃣"]

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=action_check)
            except asyncio.TimeoutError:
                await ctx.send(f"{current_user.name} took too long! Skipping turn...")
                current_turn = opponent_id if current_turn == challenger_id else challenger_id
                continue

            # Process action
            opponent_id_in_turn = opponent_id if current_turn == challenger_id else challenger_id

            if str(reaction.emoji) == "1️⃣":  # Attack
                damage = self.calculate_damage(
                    battle_state[current_turn]['data'],
                    battle_state[opponent_id_in_turn]['data']
                )
                battle_state[opponent_id_in_turn]['hp'] -= damage
                await ctx.send(f"{current_user.name} dealt {damage} damage!")

            elif str(reaction.emoji) == "2️⃣":  # Use Shadow
                if not battle_state[current_turn]['data'].get('shadows'):
                    await ctx.send("You don't have any shadows!")
                else:
                    # Select shadow
                    shadow = battle_state[current_turn]['data']['shadows'][0]  # Use first shadow for simplicity
                    damage = self.calculate_damage(shadow, battle_state[opponent_id_in_turn]['data'], is_shadow=True)
                    battle_state[opponent_id_in_turn]['hp'] -= damage
                    await ctx.send(f"{current_user.name}'s {shadow['name']} dealt {damage} damage!")

            else:  # Defend
                battle_state[current_turn]['data']['defense_bonus'] = 10
                await ctx.send(f"{current_user.name} took a defensive stance!")

            # Check for victory
            if battle_state[opponent_id_in_turn]['hp'] <= 0:
                winner = current_user
                loser = self.bot.get_user(int(opponent_id_in_turn))
                break

            # Switch turns
            current_turn = opponent_id if current_turn == challenger_id else challenger_id

        # End battle and give rewards
        await ctx.send(f"🎉 {winner.mention} wins the duel!")

        # Update stats and give rewards
        winner_data = hunters_data[str(winner.id)]
        winner_data['pvp_wins'] = winner_data.get('pvp_wins', 0) + 1
        winner_data['gold'] = winner_data.get('gold', 0) + 100

        self.save_hunters_data(hunters_data)

        # Clear active duels
        del self.active_duels[challenger_id]
        del self.active_duels[opponent_id]

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

async def setup(bot):
    await bot.add_cog(PvPSystem(bot))
