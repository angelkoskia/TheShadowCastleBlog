import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import json
import random
import asyncio

class PvPSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_duels = {}
        self.duel_invites = {}

    def load_hunters_data(self):
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_hunters_data(self, data):
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    class DuelView(View):
        def __init__(self, cog, challenger_id, target_id):
            super().__init__(timeout=60)
            self.cog = cog
            self.challenger_id = challenger_id
            self.target_id = target_id

        @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="⚔️")
        async def accept_duel(self, interaction: discord.Interaction, button: Button):
            if str(interaction.user.id) != self.target_id:
                await interaction.response.send_message("This duel is not for you!", ephemeral=True)
                return
            await self.cog.start_duel(interaction, self.challenger_id, self.target_id)

        @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger, emoji="❌")
        async def decline_duel(self, interaction: discord.Interaction, button: Button):
            if str(interaction.user.id) != self.target_id:
                await interaction.response.send_message("This duel is not for you!", ephemeral=True)
                return
            await interaction.response.send_message(f"<@{self.target_id}> declined the duel!")

    class DuelCombatView(View):
        def __init__(self, cog, duel_id):
            super().__init__(timeout=180)
            self.cog = cog
            self.duel_id = duel_id

        @discord.ui.button(label="Attack", style=discord.ButtonStyle.danger, emoji="⚔️")
        async def attack(self, interaction: discord.Interaction, button: Button):
            await self.cog.process_duel_action(interaction, self.duel_id, "attack")

        @discord.ui.button(label="Defend", style=discord.ButtonStyle.primary, emoji="🛡️")
        async def defend(self, interaction: discord.Interaction, button: Button):
            await self.cog.process_duel_action(interaction, self.duel_id, "defend")

        @discord.ui.button(label="Ability", style=discord.ButtonStyle.success, emoji="✨")
        async def ability(self, interaction: discord.Interaction, button: Button):
            await self.cog.process_duel_action(interaction, self.duel_id, "ability")

    @commands.command(name='pvp')
    async def pvp(self, ctx, target: discord.Member = None):
        """Challenge another hunter to PvP"""
        if not target:
            await ctx.send("Please mention a hunter to challenge! Usage: #pvp @user")
            return

        if target.id == ctx.author.id:
            await ctx.send("You cannot duel yourself!")
            return

        hunters_data = self.load_hunters_data()
        challenger_id = str(ctx.author.id)
        target_id = str(target.id)

        # Check if both players are hunters
        if challenger_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use #start")
            return
        if target_id not in hunters_data:
            await ctx.send(f"{target.mention} needs to start their journey first!")
            return

        # Check if either player is already in a duel
        if challenger_id in self.active_duels or target_id in self.active_duels:
            await ctx.send("One of the players is already in a duel!")
            return

        # Create duel invite
        embed = discord.Embed(
            title="⚔️ Duel Challenge",
            description=f"{ctx.author.mention} has challenged {target.mention} to a duel!",
            color=discord.Color.red()
        )

        # Add player stats
        challenger = hunters_data[challenger_id]
        target_hunter = hunters_data[target_id]

        embed.add_field(
            name=f"{ctx.author.display_name}",
            value=f"Level: {challenger['level']}\nRank: {challenger['rank']}\nWins: {challenger.get('pvp_wins', 0)}",
            inline=True
        )
        embed.add_field(
            name=f"{target.display_name}",
            value=f"Level: {target_hunter['level']}\nRank: {target_hunter['rank']}\nWins: {target_hunter.get('pvp_wins', 0)}",
            inline=True
        )

        await ctx.send(embed=embed, view=self.DuelView(self, challenger_id, target_id))

    async def start_duel(self, interaction, challenger_id, target_id):
        """Start a duel between two players"""
        hunters_data = self.load_hunters_data()

        # Create duel session
        duel_id = f"duel_{challenger_id}_{target_id}"
        self.active_duels[duel_id] = {
            'challenger': challenger_id,
            'target': target_id,
            'turn': challenger_id,
            'round': 1,
            'actions': {}
        }

        # Get player data
        challenger = hunters_data[challenger_id]
        target_hunter = hunters_data[target_id]

        # Create duel status embed
        embed = discord.Embed(
            title="⚔️ Duel Started!",
            description=f"<@{challenger_id}> vs <@{target_id}>",
            color=discord.Color.gold()
        )

        # Show health bars
        def create_health_bar(current, maximum=100, length=10):
            filled = int((current / maximum) * length)
            return "█" * filled + "░" * (length - filled)

        embed.add_field(
            name=f"{self.bot.get_user(int(challenger_id)).display_name}",
            value=f"HP: {create_health_bar(challenger['hp'])} {challenger['hp']}/100",
            inline=False
        )
        embed.add_field(
            name=f"{self.bot.get_user(int(target_id)).display_name}",
            value=f"HP: {create_health_bar(target_hunter['hp'])} {target_hunter['hp']}/100",
            inline=False
        )

        embed.add_field(
            name="Turn",
            value=f"<@{challenger_id}>'s turn!",
            inline=False
        )

        await interaction.response.send_message(embed=embed, view=self.DuelCombatView(self, duel_id))

    async def process_duel_action(self, interaction, duel_id, action):
        """Process a duel action"""
        user_id = str(interaction.user.id)
        duel = self.active_duels.get(duel_id)

        if not duel:
            await interaction.response.send_message("This duel has ended!", ephemeral=True)
            return

        if user_id != duel['turn']:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        hunters_data = self.load_hunters_data()
        attacker = hunters_data[user_id]
        defender_id = duel['target'] if user_id == duel['challenger'] else duel['challenger']
        defender = hunters_data[defender_id]

        # Process action
        damage = 0
        action_text = ""

        if action == "attack":
            damage = max(1, attacker.get('strength', 10) + random.randint(1, 10) - defender.get('defense_bonus', 0))
            defender['hp'] -= damage
            action_text = f"⚔️ <@{user_id}> attacks for {damage} damage!"
        elif action == "defend":
            attacker['defense_bonus'] = attacker.get('defense_bonus', 0) + 5
            action_text = f"🛡️ <@{user_id}> takes a defensive stance!"
        elif action == "ability":
            # Show ability selection menu
            abilities = [
                {"name": "Power Strike", "damage": 20, "description": "A powerful attack"},
                {"name": "Quick Slash", "damage": 15, "description": "A fast attack"},
                {"name": "Shield Bash", "damage": 10, "description": "A defensive attack"}
            ]

            options = [
                discord.SelectOption(
                    label=ability["name"],
                    description=ability["description"],
                    value=str(i)
                ) for i, ability in enumerate(abilities)
            ]

            class AbilitySelect(Select):
                def __init__(self):
                    super().__init__(placeholder="Choose an ability...", options=options)

                async def callback(self, interaction: discord.Interaction):
                    ability = abilities[int(self.values[0])]
                    damage = ability["damage"]
                    defender['hp'] -= damage
                    await interaction.response.send_message(f"✨ <@{user_id}> uses {ability['name']} for {damage} damage!")
                    await self.cog.update_duel_status(interaction, duel_id)

            view = View()
            view.add_item(AbilitySelect())
            await interaction.response.send_message("Choose your ability:", view=view, ephemeral=True)
            return

        # Save changes
        self.save_hunters_data(hunters_data)

        # Switch turns
        duel['turn'] = defender_id
        duel['round'] += 1

        # Check for victory
        if defender['hp'] <= 0:
            await self.end_duel(interaction, duel_id, user_id)
            return

        # Update duel status
        await self.update_duel_status(interaction, duel_id, action_text)

    async def update_duel_status(self, interaction, duel_id, action_text=None):
        """Update the duel status display"""
        duel = self.active_duels[duel_id]
        hunters_data = self.load_hunters_data()

        challenger = hunters_data[duel['challenger']]
        target = hunters_data[duel['target']]

        embed = discord.Embed(
            title="⚔️ Duel Status",
            description=f"Round {duel['round']}",
            color=discord.Color.gold()
        )

        def create_health_bar(current, maximum=100, length=10):
            filled = int((current / maximum) * length)
            return "█" * filled + "░" * (length - filled)

        embed.add_field(
            name=f"{self.bot.get_user(int(duel['challenger'])).display_name}",
            value=f"HP: {create_health_bar(challenger['hp'])} {challenger['hp']}/100",
            inline=False
        )
        embed.add_field(
            name=f"{self.bot.get_user(int(duel['target'])).display_name}",
            value=f"HP: {create_health_bar(target['hp'])} {target['hp']}/100",
            inline=False
        )

        if action_text:
            embed.add_field(name="Last Action", value=action_text, inline=False)

        embed.add_field(
            name="Turn",
            value=f"<@{duel['turn']}>'s turn!",
            inline=False
        )

        await interaction.channel.send(embed=embed, view=self.DuelCombatView(self, duel_id))

    async def end_duel(self, interaction, duel_id, winner_id):
        """End a duel and process rewards"""
        duel = self.active_duels[duel_id]
        hunters_data = self.load_hunters_data()

        winner = hunters_data[winner_id]
        loser_id = duel['target'] if winner_id == duel['challenger'] else duel['challenger']
        loser = hunters_data[loser_id]

        # Update PvP stats
        winner['pvp_wins'] = winner.get('pvp_wins', 0) + 1
        winner['exp'] += 100  # PvP experience reward
        winner['gold'] = winner.get('gold', 0) + 50  # PvP gold reward

        loser['pvp_losses'] = loser.get('pvp_losses', 0) + 1

        self.save_hunters_data(hunters_data)

        # Create victory embed
        embed = discord.Embed(
            title="🏆 Duel Ended!",
            description=f"<@{winner_id}> is victorious!",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="Rewards",
            value=f"Experience: +100\nGold: +50",
            inline=False
        )
        embed.add_field(
            name="Stats Updated",
            value=f"Winner: {winner.get('pvp_wins', 1)} wins\nLoser: {loser.get('pvp_losses', 1)} losses",
            inline=False
        )

        # Remove duel from active duels
        del self.active_duels[duel_id]

        await interaction.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PvPSystem(bot))
