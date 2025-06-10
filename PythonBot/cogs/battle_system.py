import discord
from discord.ext import commands
import json
import random
import asyncio
from datetime import datetime

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

    @commands.command(name='hunt')
    async def start_hunting(self, ctx):
        """Start hunting for monsters"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You haven't started your journey yet! Use !start first.")
            return

        if user_id in self.active_battles:
            await ctx.send("You're already in a battle! Finish it first.")
            return

        hunter = hunters_data[user_id]
        monster = self.get_random_monster(hunter['level'])

        if not monster:
            await ctx.send("No suitable monsters found for your level!")
            return

        # Initialize battle
        self.active_battles[user_id] = {
            'monster': monster,
            'monster_hp': monster['hp'],
            'hunter_hp': hunter['hp'],
            'hunter_mp': hunter['mp'],
            'status_effects': {}
        }

        embed = discord.Embed(
            title="🎯 Monster Encountered!",
            description=f"You found a level {monster['level']} {monster['name']}!",
            color=0xff0000
        )
        embed.add_field(name="Monster HP", value=f"{monster['hp']}/{monster['hp']}")
        embed.add_field(name="Your HP", value=f"{hunter['hp']}/{100}")
        embed.set_footer(text="Use !attack, !defend, or !flee")

        await ctx.send(embed=embed)

    @commands.command(name='attack')
    async def attack_monster(self, ctx):
        """Attack the current monster"""
        user_id = str(ctx.author.id)

        if user_id not in self.active_battles:
            await ctx.send("You're not in a battle! Use !hunt to find a monster.")
            return

        battle = self.active_battles[user_id]
        hunters_data = self.load_hunters_data()
        hunter = hunters_data[user_id]

        # Calculate damage
        hunter_damage = max(1, hunter.get('strength', 10) + hunter.get('attack_bonus', 0) - battle['monster']['defense']//2)
        monster_damage = max(1, battle['monster']['attack'] - hunter.get('defense_bonus', 0))

        # Apply hunter's attack
        battle['monster_hp'] -= hunter_damage
        await ctx.send(f"You dealt {hunter_damage} damage to {battle['monster']['name']}!")

        # Check if monster is defeated
        if battle['monster_hp'] <= 0:
            # Calculate rewards
            exp_gain = battle['monster']['exp_reward']
            gold_gain = battle['monster']['gold_reward']

            hunter['exp'] += exp_gain
            hunter['gold'] = hunter.get('gold', 0) + gold_gain

            # Level up check
            while hunter['exp'] >= hunter['level'] * 100:
                hunter['exp'] -= hunter['level'] * 100
                hunter['level'] += 1
                stat_increase = random.randint(2, 5)
                hunter['strength'] += stat_increase
                await ctx.send(f"🎉 Level Up! You are now level {hunter['level']}!")

            embed = discord.Embed(
                title="Victory!",
                description=f"You defeated the {battle['monster']['name']}!",
                color=0x00ff00
            )
            embed.add_field(name="Rewards", value=f"EXP: {exp_gain}\nGold: {gold_gain}")

            # Check for shadow extraction chance
            if random.random() < battle['monster'].get('shadow_chance', 0):
                embed.add_field(name="Shadow Chance!", value="Use !extract to attempt shadow extraction!")

            await ctx.send(embed=embed)
            del self.active_battles[user_id]
            self.save_hunters_data(hunters_data)
            return

        # Monster's turn
        battle['hunter_hp'] -= monster_damage
        await ctx.send(f"{battle['monster']['name']} dealt {monster_damage} damage to you!")

        # Check if hunter is defeated
        if battle['hunter_hp'] <= 0:
            embed = discord.Embed(
                title="Defeat!",
                description=f"You were defeated by the {battle['monster']['name']}!",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            del self.active_battles[user_id]

            # Partial HP recovery after defeat
            hunter['hp'] = 50
            self.save_hunters_data(hunters_data)
            return

        # Update battle status
        embed = discord.Embed(title="Battle Status", color=0x00ff00)
        embed.add_field(
            name=battle['monster']['name'],
            value=f"HP: {battle['monster_hp']}/{battle['monster']['hp']}"
        )
        embed.add_field(
            name=ctx.author.name,
            value=f"HP: {battle['hunter_hp']}/{100}"
        )
        await ctx.send(embed=embed)

    @commands.command(name='defend')
    async def defend_action(self, ctx):
        """Take a defensive stance in battle"""
        user_id = str(ctx.author.id)

        if user_id not in self.active_battles:
            await ctx.send("You're not in a battle! Use !hunt to find a monster.")
            return

        battle = self.active_battles[user_id]
        battle['status_effects']['defending'] = True

        # Reduce incoming damage by 50%
        monster_damage = max(1, battle['monster']['attack'] // 2)
        battle['hunter_hp'] -= monster_damage

        await ctx.send(f"You take a defensive stance! {battle['monster']['name']} dealt {monster_damage} damage!")

        if battle['hunter_hp'] <= 0:
            hunters_data = self.load_hunters_data()
            hunter = hunters_data[user_id]
            hunter['hp'] = 50  # Partial recovery
            self.save_hunters_data(hunters_data)

            await ctx.send("You were defeated despite your defensive stance!")
            del self.active_battles[user_id]
            return

        embed = discord.Embed(title="Battle Status", color=0x00ff00)
        embed.add_field(
            name=battle['monster']['name'],
            value=f"HP: {battle['monster_hp']}/{battle['monster']['hp']}"
        )
        embed.add_field(
            name=ctx.author.name,
            value=f"HP: {battle['hunter_hp']}/{100} (Defending)"
        )
        await ctx.send(embed=embed)

    @commands.command(name='flee')
    async def flee_battle(self, ctx):
        """Attempt to flee from battle"""
        user_id = str(ctx.author.id)

        if user_id not in self.active_battles:
            await ctx.send("You're not in a battle! Use !hunt to find a monster.")
            return

        # 50% chance to successfully flee
        if random.random() < 0.5:
            del self.active_battles[user_id]
            await ctx.send("You successfully fled from battle!")
        else:
            # Take damage for failed escape
            battle = self.active_battles[user_id]
            damage = max(1, battle['monster']['attack'] - 5)
            battle['hunter_hp'] -= damage

            await ctx.send(f"Failed to escape! {battle['monster']['name']} dealt {damage} damage!")

            if battle['hunter_hp'] <= 0:
                hunters_data = self.load_hunters_data()
                hunter = hunters_data[user_id]
                hunter['hp'] = 50  # Partial recovery
                self.save_hunters_data(hunters_data)

                await ctx.send("You were defeated while trying to escape!")
                del self.active_battles[user_id]

async def setup(bot):
    await bot.add_cog(BattleSystem(bot))
