import discord
from discord.ext import commands
import json
import random
import asyncio
from datetime import datetime, timedelta

class DungeonRaids(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_raids = {}
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

    def get_dungeon_monsters(self, floor, hunter_level):
        """Generate monsters for a dungeon floor based on hunter's level"""
        monster_pool = []
        for category, monsters in self.monsters_data.items():
            for monster_id, monster in monsters.items():
                if abs(monster['level'] - hunter_level) <= 5:
                    monster_pool.append(monster)

        return random.sample(monster_pool, min(floor + 2, len(monster_pool)))

    @commands.command(name='dungeon')
    async def start_dungeon(self, ctx, floors: int = 3):
        """Start a dungeon raid with specified number of floors"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send(embed=discord.Embed(description="You haven't started your journey yet! Use #start first.", color=discord.Color.red()))
            return

        if user_id in self.active_raids:
            await ctx.send(embed=discord.Embed(description="You're already in a dungeon! Complete or abandon it first.", color=discord.Color.orange()))
            return

        if floors < 1 or floors > 10:
            await ctx.send(embed=discord.Embed(description="Please choose between 1 and 10 floors!", color=discord.Color.orange()))
            return

        hunter = hunters_data[user_id]
        hunter_level = hunter.get('level', 1)

        # Initialize dungeon
        dungeon = {
            'floors': floors,
            'current_floor': 1,
            'hp': hunter.get('hp', 100),
            'mp': hunter.get('mp', 50),
            'start_time': datetime.now(),
            'monsters_defeated': 0,
            'total_exp': 0,
            'total_gold': 0
        }
        self.active_raids[user_id] = dungeon

        embed = discord.Embed(
            title="🏰 Dungeon Raid Started!",
            description=f"Entering a {floors}-floor dungeon...",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

        # Start the first floor
        await self.handle_floor(ctx, user_id)

    async def handle_floor(self, ctx, user_id):
        """Handle a dungeon floor"""
        hunters_data = self.load_hunters_data()
        hunter = hunters_data[user_id]
        dungeon = self.active_raids[user_id]

        # Generate monsters for this floor
        floor_monsters = self.get_dungeon_monsters(dungeon['current_floor'], hunter.get('level', 1))

        embed = discord.Embed(
            title=f"Floor {dungeon['current_floor']}",
            description=f"Monsters encountered: {', '.join(m['name'] for m in floor_monsters)}",
            color=discord.Color.purple()
        )
        floor_msg = await ctx.send(embed=embed)

        # Battle each monster
        for monster in floor_monsters:
            battle_result = await self.handle_battle(ctx, user_id, monster)
            if not battle_result:  # Hunter died or fled
                del self.active_raids[user_id]
                return

            dungeon['monsters_defeated'] += 1
            dungeon['total_exp'] += monster['exp_reward']
            dungeon['total_gold'] += monster['gold_reward']

        # Floor cleared
        if dungeon['current_floor'] == dungeon['floors']:
            # Dungeon completed
            await self.complete_dungeon(ctx, user_id)
        else:
            # Proceed to next floor
            dungeon['current_floor'] += 1
            await ctx.send(embed=discord.Embed(description=f"Floor {dungeon['current_floor']-1} cleared! Proceeding to next floor...", color=discord.Color.blurple()))
            await self.handle_floor(ctx, user_id)

    async def handle_battle(self, ctx, user_id, monster):
        """Handle a single monster battle"""
        hunters_data = self.load_hunters_data()
        hunter = hunters_data[user_id]
        dungeon = self.active_raids[user_id]

        monster_hp = monster['hp']
        battle_msg = None

        while monster_hp > 0 and dungeon['hp'] > 0:
            # Update battle display
            embed = discord.Embed(title=f"⚔️ Battle vs {monster['name']}", color=discord.Color.red())
            embed.add_field(name="Your HP", value=f"{dungeon['hp']}/100", inline=True)
            embed.add_field(name=f"{monster['name']}'s HP", value=f"{monster_hp}/{monster['hp']}", inline=True)

            if battle_msg:
                await battle_msg.edit(embed=embed)
            else:
                battle_msg = await ctx.send(embed=embed)

            # Player's turn (modern UI: buttons)
            class BattleActionView(discord.ui.View):
                def __init__(self, parent, ctx, user_id, hunter, monster, dungeon):
                    super().__init__(timeout=30)
                    self.parent = parent
                    self.ctx = ctx
                    self.user_id = user_id
                    self.hunter = hunter
                    self.monster = monster
                    self.dungeon = dungeon
                    self.value = None
                @discord.ui.button(label="Attack", style=discord.ButtonStyle.primary, emoji="⚔️")
                async def attack(self, interaction: discord.Interaction, button: Button):
                    if interaction.user.id != int(self.user_id):
                        await interaction.response.send_message("It's not your turn!", ephemeral=True)
                        return
                    self.value = 'attack'
                    await interaction.response.defer()
                    self.stop()
                @discord.ui.button(label="Use Shadow", style=discord.ButtonStyle.secondary, emoji="👻")
                async def shadow(self, interaction: discord.Interaction, button: Button):
                    if interaction.user.id != int(self.user_id):
                        await interaction.response.send_message("It's not your turn!", ephemeral=True)
                        return
                    self.value = 'shadow'
                    await interaction.response.defer()
                    self.stop()
                @discord.ui.button(label="Use Potion", style=discord.ButtonStyle.success, emoji="🧪")
                async def potion(self, interaction: discord.Interaction, button: Button):
                    if interaction.user.id != int(self.user_id):
                        await interaction.response.send_message("It's not your turn!", ephemeral=True)
                        return
                    self.value = 'potion'
                    await interaction.response.defer()
                    self.stop()
                @discord.ui.button(label="Flee", style=discord.ButtonStyle.danger, emoji="🏃")
                async def flee(self, interaction: discord.Interaction, button: Button):
                    if interaction.user.id != int(self.user_id):
                        await interaction.response.send_message("It's not your turn!", ephemeral=True)
                        return
                    self.value = 'flee'
                    await interaction.response.defer()
                    self.stop()
            action_view = BattleActionView(self, ctx, user_id, hunter, monster, dungeon)
            action_msg = await ctx.send("Choose your action:", view=action_view)
            await action_view.wait()
            action = action_view.value
            if not action:
                await ctx.send(embed=discord.Embed(description="You took too long! The monster attacks!", color=discord.Color.orange()))
            else:
                if action == 'attack':
                    damage = max(1, hunter.get('strength', 10) - monster['defense']//2)
                    monster_hp -= damage
                    await ctx.send(f"You dealt {damage} damage!")
                elif action == 'shadow':
                    if not hunter.get('shadows'):
                        await ctx.send(embed=discord.Embed(description="You don't have any shadows!", color=discord.Color.orange()))
                    else:
                        shadow = hunter['shadows'][0]  # Use first shadow
                        damage = max(1, shadow['stats']['attack'] - monster['defense']//2)
                        monster_hp -= damage
                        await ctx.send(f"Your {shadow['name']} dealt {damage} damage!")
                elif action == 'potion':
                    if 'health_potion' in hunter.get('inventory', []):
                        dungeon['hp'] = min(100, dungeon['hp'] + 50)
                        hunter['inventory'].remove('health_potion')
                        await ctx.send(embed=discord.Embed(description="Used a health potion! Restored 50 HP!", color=discord.Color.green()))
                    else:
                        await ctx.send(embed=discord.Embed(description="No health potions available!", color=discord.Color.orange()))
                elif action == 'flee':
                    if random.random() < 0.5:
                        await ctx.send(embed=discord.Embed(description="You successfully fled from the battle!", color=discord.Color.green()))
                        return False
                    else:
                        await ctx.send(embed=discord.Embed(description="Failed to flee!", color=discord.Color.red()))
            # Monster's turn
            if monster_hp > 0:
                damage = max(1, monster['attack'] - hunter.get('defense_bonus', 0))
                dungeon['hp'] -= damage
                await ctx.send(f"{monster['name']} dealt {damage} damage to you!")
        if dungeon['hp'] <= 0:
            await ctx.send(embed=discord.Embed(description="You were defeated!", color=discord.Color.red()))
            return False
        else:
            await ctx.send(embed=discord.Embed(description=f"Victory! Defeated {monster['name']}!", color=discord.Color.green()))
            return True

    async def complete_dungeon(self, ctx, user_id):
        """Handle dungeon completion and rewards"""
        hunters_data = self.load_hunters_data()
        hunter = hunters_data[user_id]
        dungeon = self.active_raids[user_id]

        # Calculate completion time
        time_taken = datetime.now() - dungeon['start_time']

        # Award rewards
        hunter['exp'] += dungeon['total_exp']
        hunter['gold'] = hunter.get('gold', 0) + dungeon['total_gold']

        # Check for level up
        while hunter['exp'] >= hunter['level'] * 100:
            hunter['exp'] -= hunter['level'] * 100
            hunter['level'] += 1
            await ctx.send(f"🎉 Level Up! You are now level {hunter['level']}!")

        # Create completion embed
        embed = discord.Embed(
            title="🎉 Dungeon Completed!",
            description=f"Completed a {dungeon['floors']}-floor dungeon!",
            color=0x00ff00
        )
        embed.add_field(name="Time Taken", value=str(time_taken).split('.')[0])
        embed.add_field(name="Monsters Defeated", value=str(dungeon['monsters_defeated']))
        embed.add_field(name="EXP Gained", value=str(dungeon['total_exp']))
        embed.add_field(name="Gold Earned", value=str(dungeon['total_gold']))

        await ctx.send(embed=embed)

        # Update hunter data and clean up
        self.save_hunters_data(hunters_data)
        del self.active_raids[user_id]

async def setup(bot):
    await bot.add_cog(DungeonRaids(bot))
