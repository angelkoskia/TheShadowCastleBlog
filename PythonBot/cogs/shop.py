import discord
from discord.ext import commands
import json
import os

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('data/items.json', 'r') as f:
            self.items_data = json.load(f)

    def load_hunters_data(self):
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_hunters_data(self, data):
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    @commands.command(name='shop')
    async def show_shop(self, ctx, category: str = None):
        """Browse the hunter's shop. Categories: weapons, armor, potions"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You haven't started your journey yet! Use !start first.")
            return

        hunter = hunters_data[user_id]
        hunter_rank = hunter.get('rank', 'E')

        if category and category.lower() not in ['weapons', 'armor', 'potions']:
            await ctx.send("Invalid category! Choose from: weapons, armor, potions")
            return

        embed = discord.Embed(
            title="🏪 Hunter's Shop",
            description="Welcome to the shop! Use `!buy <item_name>` to purchase items.",
            color=0xffd700  # Gold color
        )

        categories = [category.lower()] if category else ['weapons', 'armor', 'potions']
        category_icons = {
            'weapons': '⚔️',
            'armor': '🛡️',
            'potions': '🧪'
        }

        for cat in categories:
            items_list = ""
            for item_id, item_data in self.items_data[cat].items():
                # Check if player rank is sufficient
                if 'rank' in item_data and self.rank_to_number(item_data['rank']) > self.rank_to_number(hunter_rank):
                    continue

                # Create a formatted item entry with stats and requirements
                item_entry = f"**{item_data['name']}**\n"
                item_entry += f"└ 🪙 Price: {item_data['price']} gold\n"

                if 'attack' in item_data:
                    item_entry += f"└ ⚔️ Attack: +{item_data['attack']}\n"
                if 'defense' in item_data:
                    item_entry += f"└ 🛡️ Defense: +{item_data['defense']}\n"
                if 'effect' in item_data:
                    effect = item_data['effect']
                    effect_type = effect['type'].replace('_', ' ').title()
                    item_entry += f"└ ✨ Effect: {effect_type} (+{effect['value']})\n"
                if 'rank' in item_data:
                    item_entry += f"└ 📊 Required Rank: {item_data['rank']}\n"

                items_list += f"{item_entry}\n"

            if items_list:
                embed.add_field(
                    name=f"{category_icons[cat]} {cat.title()}",
                    value=items_list,
                    inline=False
                )

        # Show player's gold at the bottom
        embed.set_footer(text=f"Your Gold: 🪙 {hunter.get('gold', 0)}")
        await ctx.send(embed=embed)

    def rank_to_number(self, rank):
        ranks = {'E': 1, 'D': 2, 'C': 3, 'B': 4, 'A': 5, 'S': 6}
        return ranks.get(rank, 0)

    @commands.command(name='buy')
    async def buy_item(self, ctx, *, item_name: str):
        """Buy an item from the shop"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You haven't started your journey yet! Use !start first.")
            return

        hunter = hunters_data[user_id]

        # Find item in shop
        item_found = False
        item_category = None
        item_data = None
        item_id = None

        for category, items in self.items_data.items():
            for id, data in items.items():
                if data['name'].lower() == item_name.lower():
                    item_found = True
                    item_category = category
                    item_data = data
                    item_id = id
                    break
            if item_found:
                break

        if not item_found:
            await ctx.send("This item doesn't exist in the shop!")
            return

        # Check if player has enough gold
        if hunter.get('gold', 0) < item_data['price']:
            await ctx.send("You don't have enough gold to buy this item!")
            return

        # Check if player meets rank requirement
        if 'rank' in item_data:
            if self.rank_to_number(item_data['rank']) > self.rank_to_number(hunter.get('rank', 'E')):
                await ctx.send(f"You need to be rank {item_data['rank']} or higher to buy this item!")
                return

        # Process purchase
        hunter['gold'] -= item_data['price']
        if 'inventory' not in hunter:
            hunter['inventory'] = []
        hunter['inventory'].append(item_id)

        self.save_hunters_data(hunters_data)
        await ctx.send(f"Successfully purchased {item_data['name']} for {item_data['price']} gold!")

    @commands.command(name='sell')
    async def sell_item(self, ctx, *, item_name: str):
        """Sell an item from your inventory"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You haven't started your journey yet! Use !start first.")
            return

        hunter = hunters_data[user_id]
        if 'inventory' not in hunter or item_name not in hunter['inventory']:
            await ctx.send("You don't have this item in your inventory!")
            return

        # Find item data to determine sell price
        item_data = None
        for category in self.items_data:
            if item_name in self.items_data[category]:
                item_data = self.items_data[category][item_name]
                break

        if not item_data:
            await ctx.send("Error: Item data not found!")
            return

        sell_price = item_data['price'] // 2  # Sell for half the purchase price
        hunter['inventory'].remove(item_name)
        hunter['gold'] = hunter.get('gold', 0) + sell_price

        self.save_hunters_data(hunters_data)
        await ctx.send(f"Successfully sold {item_data['name']} for {sell_price} gold!")

async def setup(bot):
    await bot.add_cog(Shop(bot))
