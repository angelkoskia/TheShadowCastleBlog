import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import json
import random
import asyncio

class BattleSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_battles = {}
        with open('data/monsters.json', 'r') as f:
            self.monsters_data = json.load(f)

    def load_hunters_data(self):
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_hunters_data(self, data):
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    def get_random_monster(self, hunter_level):
        """Get a random monster appropriate for the hunter's level"""
        suitable_monsters = []
        for category, monsters in self.monsters_data.items():
            for monster_id, monster in monsters.items():
                if abs(monster['level'] - hunter_level) <= 5:
                    monster['id'] = monster_id
                    suitable_monsters.append(monster)

        return random.choice(suitable_monsters) if suitable_monsters else None

    class BattleView(View):
        def __init__(self, battle_instance):
            super().__init__(timeout=30)
            self.battle = battle_instance

        @discord.ui.button(label="Attack", style=discord.ButtonStyle.danger, emoji="⚔️")
        async def attack_button(self, interaction: discord.Interaction, button: Button):
            await self.battle.process_attack(interaction)

        @discord.ui.button(label="Defend", style=discord.ButtonStyle.primary, emoji="🛡️")
        async def defend_button(self, interaction: discord.Interaction, button: Button):
            await self.battle.process_defend(interaction)

        @discord.ui.button(label="Use Item", style=discord.ButtonStyle.success, emoji="🎒")
        async def item_button(self, interaction: discord.Interaction, button: Button):
            await self.battle.show_inventory(interaction)

        @discord.ui.button(label="Flee", style=discord.ButtonStyle.secondary, emoji="🏃")
        async def flee_button(self, interaction: discord.Interaction, button: Button):
            await self.battle.attempt_flee(interaction)

    @commands.command(name='hunt')
    async def hunt(self, ctx):
        """Start hunting monsters in the current gate/dungeon"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use #start")
            return

        if user_id in self.active_battles:
            await ctx.send("You're already in battle!")
            return

        monster = self.get_random_monster(hunters_data[user_id]['level'])

        if not monster:
            await ctx.send("No suitable monsters found for your level!")
            return

        battle_embed = discord.Embed(
            title="⚔️ Battle Started!",
            description=f"You encountered a Level {monster['level']} {monster['name']}!",
            color=discord.Color.red()
        )
        battle_embed.add_field(name="Monster HP", value=f"❤️ {monster['hp']}/100")
        battle_embed.add_field(name="Your HP", value=f"❤️ {hunters_data[user_id]['hp']}/100")

        self.active_battles[user_id] = {
            "monster": monster,
            "player": hunters_data[user_id],
            "turns": 0
        }

        await ctx.send(embed=battle_embed, view=self.BattleView(self))

    async def process_attack(self, interaction):
        user_id = str(interaction.user.id)
        battle = self.active_battles.get(user_id)

        if not battle:
            await interaction.response.send_message("You're not in battle!", ephemeral=True)
            return

        hunters_data = self.load_hunters_data()
        hunter = hunters_data[user_id]

        # Calculate damage
        player_damage = max(1, hunter.get('strength', 10) + hunter.get('attack_bonus', 0) - battle['monster']['defense']//2)
        monster_damage = max(1, battle['monster']['attack'] - hunter.get('defense_bonus', 0))

        # Apply damage
        battle['monster']['hp'] -= player_damage
        battle['player']['hp'] -= monster_damage

        # Update battle status
        battle_embed = discord.Embed(
            title="⚔️ Battle Round",
            description=f"You dealt {player_damage} damage!\nThe {battle['monster']['name']} dealt {monster_damage} damage!",
            color=discord.Color.blue()
        )
        battle_embed.add_field(name="Monster HP", value=f"❤️ {max(0, battle['monster']['hp'])}/100")
        battle_embed.add_field(name="Your HP", value=f"❤️ {max(0, battle['player']['hp'])}/100")

        # Check for battle end
        if battle["monster"]["hp"] <= 0:
            await self.end_battle(interaction, True)
            return

        if battle["player"]["hp"] <= 0:
            await self.end_battle(interaction, False)
            return

        await interaction.response.send_message(embed=battle_embed, view=self.BattleView(self))

    async def process_defend(self, interaction):
        user_id = str(interaction.user.id)
        battle = self.active_battles.get(user_id)

        if not battle:
            await interaction.response.send_message("You're not in battle!", ephemeral=True)
            return

        hunters_data = self.load_hunters_data()
        hunter = hunters_data[user_id]

        # Reduce incoming damage
        monster_damage = max(1, battle["monster"]["attack"] // 2)
        battle["player"]["hp"] -= monster_damage

        defend_embed = discord.Embed(
            title="🛡️ Defensive Stance",
            description=f"You blocked some damage!\nThe {battle['monster']['name']} dealt {monster_damage} damage!",
            color=discord.Color.blue()
        )
        defend_embed.add_field(name="Monster HP", value=f"❤️ {battle['monster']['hp']}/100")
        defend_embed.add_field(name="Your HP", value=f"❤️ {battle['player']['hp']}/100")

        if battle["player"]["hp"] <= 0:
            await self.end_battle(interaction, False)
            return

        await interaction.response.send_message(embed=defend_embed, view=self.BattleView(self))

    async def attempt_flee(self, interaction):
        user_id = str(interaction.user.id)
        battle = self.active_battles.get(user_id)

        if not battle:
            await interaction.response.send_message("You're not in battle!", ephemeral=True)
            return

        # 50% chance to flee
        if random.random() > 0.5:
            del self.active_battles[user_id]
            flee_embed = discord.Embed(
                title="🏃 Escaped!",
                description="You successfully fled from battle!",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=flee_embed)
        else:
            # Take damage for failed flee attempt
            damage = battle["monster"]["damage"]
            battle["player"]["hp"] -= damage

            flee_embed = discord.Embed(
                title="❌ Flee Failed!",
                description=f"You couldn't escape!\nTook {damage} damage!",
                color=discord.Color.red()
            )
            flee_embed.add_field(name="Your HP", value=f"❤️ {battle['player']['hp']}/100")

            if battle["player"]["hp"] <= 0:
                await self.end_battle(interaction, False)
                return

            await interaction.response.send_message(embed=flee_embed, view=self.BattleView(self))

    async def end_battle(self, interaction, victory):
        user_id = str(interaction.user.id)
        battle = self.active_battles[user_id]
        hunters_data = self.load_hunters_data()

        # Update hunter data
        hunters_data[user_id]["hp"] = battle["player"]["hp"]

        if victory:
            exp_gain = battle['monster']['exp_reward']
            gold_gain = battle['monster']['gold_reward']
            hunters_data[user_id]["exp"] = hunters_data[user_id].get("exp", 0) + exp_gain
            hunters_data[user_id]["gold"] = hunters_data[user_id].get("gold", 0) + gold_gain

            victory_embed = discord.Embed(
                title="🎉 Victory!",
                description=f"You defeated the {battle['monster']['name']}!",
                color=discord.Color.green()
            )
            victory_embed.add_field(name="Rewards", value=f"⭐ EXP: +{exp_gain}\n🪙 Gold: +{gold_gain}")

            # Check for shadow extraction chance
            if random.random() < battle['monster'].get('shadow_chance', 0):
                victory_embed.add_field(name="Shadow Chance!", value="Use !extract to attempt shadow extraction!")

            await interaction.response.send_message(embed=victory_embed)
        else:
            defeat_embed = discord.Embed(
                title="💀 Defeat",
                description=f"You were defeated by the {battle['monster']['name']}!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=defeat_embed)

        self.save_hunters_data(hunters_data)
        del self.active_battles[user_id]

    @commands.command(name='attack')
    async def attack(self, ctx):
        """Attack the current monster"""
        user_id = str(ctx.author.id)
        if user_id not in self.active_battles:
            await ctx.send("You're not in battle! Use #hunt to find monsters.")
            return
        await self.process_attack(await self.bot.get_context(ctx.message))

    @commands.command(name='defend')
    async def defend(self, ctx):
        """Take a defensive stance"""
        user_id = str(ctx.author.id)
        if user_id not in self.active_battles:
            await ctx.send("You're not in battle! Use #hunt to find monsters.")
            return
        await self.process_defend(await self.bot.get_context(ctx.message))

    @commands.command(name='flee')
    async def flee(self, ctx):
        """Try to escape from battle"""
        user_id = str(ctx.author.id)
        if user_id not in self.active_battles:
            await ctx.send("You're not in battle! Use #hunt to find monsters.")
            return
        await self.attempt_flee(await self.bot.get_context(ctx.message))

async def setup(bot):
    await bot.add_cog(BattleSystem(bot))
