import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import json
import asyncio

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('data/items.json', 'r') as f:
            self.shop_items = json.load(f)

    def load_hunters_data(self):
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_hunters_data(self, data):
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    class ShopView(View):
        def __init__(self, cog, category="all"):
            super().__init__(timeout=60)
            self.cog = cog
            self.category = category
            self.add_item(self.CategorySelect(cog))

        class CategorySelect(Select):
            def __init__(self, cog):
                options = [
                    discord.SelectOption(label="All Items", value="all", emoji="🏪"),
                    discord.SelectOption(label="Weapons", value="weapons", emoji="⚔️"),
                    discord.SelectOption(label="Armor", value="armor", emoji="🛡️"),
                    discord.SelectOption(label="Consumables", value="consumables", emoji="🧪"),
                    discord.SelectOption(label="Accessories", value="accessories", emoji="💍")
                ]
                super().__init__(placeholder="Select category...", options=options)
                self.cog = cog

            async def callback(self, interaction: discord.Interaction):
                await self.cog.show_shop_items(interaction, self.values[0])

    @commands.command(name='shop')
    async def shop(self, ctx):
        """Visit the hunter shop"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use #start")
            return

        embed = discord.Embed(
            title="🏪 Hunter Shop",
            description="Welcome to the shop! Select a category to view items.",
            color=discord.Color.gold()
        )

        # Show player's gold
        hunter = hunters_data[user_id]
        embed.add_field(
            name="Your Gold",
            value=f"🪙 {hunter.get('gold', 0)}",
            inline=False
        )

        await ctx.send(embed=embed, view=self.ShopView(self))

    async def show_shop_items(self, interaction, category="all"):
        """Display shop items for a specific category"""
        user_id = str(interaction.user.id)
        hunters_data = self.load_hunters_data()

        if user_id not in hunters_data:
            await interaction.response.send_message("You need to start your journey first! Use #start", ephemeral=True)
            return

        hunter = hunters_data[user_id]
        items = []

        # Filter items by category
        if category == "all":
            for cat in self.shop_items.values():
                items.extend(cat.values())
        else:
            items = list(self.shop_items.get(category, {}).values())

        embed = discord.Embed(
            title=f"🏪 Shop - {category.title()}",
            color=discord.Color.gold()
        )
        embed.add_field(name="Your Gold", value=f"🪙 {hunter.get('gold', 0)}", inline=False)

        # Create item selection menu
        options = []
        for item in items[:25]:  # Discord limit of 25 options
            options.append(
                discord.SelectOption(
                    label=f"{item['name']} - {item['price']} gold",
                    value=item['id'],
                    description=item['description'],
                    emoji=self.get_item_emoji(item['type'])
                )
            )

        # Create purchase UI
        class PurchaseView(View):
            def __init__(self):
                super().__init__(timeout=60)

            @discord.ui.select(placeholder="Select an item to purchase...", options=options)
            async def select_item(self, interaction: discord.Interaction, select: Select):
                await self.purchase_item(interaction, select.values[0])

            async def purchase_item(self, interaction, item_id):
                # Find the item
                item = None
                for category in self.shop_items.values():
                    if item_id in category:
                        item = category[item_id]
                        break

                if not item:
                    await interaction.response.send_message("Item not found!", ephemeral=True)
                    return

                # Check if player can afford it
                if hunter.get('gold', 0) < item['price']:
                    await interaction.response.send_message("You don't have enough gold!", ephemeral=True)
                    return

                # Create confirmation button
                class ConfirmView(View):
                    def __init__(self):
                        super().__init__(timeout=30)

                    @discord.ui.button(label="Confirm Purchase", style=discord.ButtonStyle.success)
                    async def confirm(self, interaction: discord.Interaction, button: Button):
                        # Process purchase
                        hunter['gold'] -= item['price']
                        if 'inventory' not in hunter:
                            hunter['inventory'] = []
                        hunter['inventory'].append(item)
                        self.save_hunters_data(hunters_data)

                        embed = discord.Embed(
                            title="✅ Purchase Successful!",
                            description=f"You bought {item['name']} for 🪙 {item['price']}",
                            color=discord.Color.green()
                        )
                        embed.add_field(name="Remaining Gold", value=f"🪙 {hunter['gold']}")
                        await interaction.response.send_message(embed=embed)

                    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
                    async def cancel(self, interaction: discord.Interaction, button: Button):
                        await interaction.response.send_message("Purchase cancelled.", ephemeral=True)

                confirm_embed = discord.Embed(
                    title="🛒 Confirm Purchase",
                    description=f"Buy {item['name']} for 🪙 {item['price']}?",
                    color=discord.Color.blue()
                )
                confirm_embed.add_field(name="Item Details", value=item['description'])
                await interaction.response.send_message(embed=confirm_embed, view=ConfirmView(), ephemeral=True)

        await interaction.response.send_message(embed=embed, view=PurchaseView())

    def get_item_emoji(self, item_type):
        """Get the appropriate emoji for item type"""
        emoji_map = {
            'weapon': '⚔️',
            'armor': '🛡️',
            'consumable': '🧪',
            'accessory': '💍'
        }
        return emoji_map.get(item_type, '📦')

    @commands.command(name='sell')
    async def sell(self, ctx, *, item_name: str = None):
        """Sell an item from your inventory"""
        if not item_name:
            await ctx.send("Please specify an item to sell! Use #inventory to see your items.")
            return

        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use #start")
            return

        hunter = hunters_data[user_id]
        inventory = hunter.get('inventory', [])

        # Find the item
        item_to_sell = None
        item_index = -1
        for i, item in enumerate(inventory):
            if item['name'].lower() == item_name.lower():
                item_to_sell = item
                item_index = i
                break

        if not item_to_sell:
            await ctx.send("Item not found in your inventory!")
            return

        # Calculate sell price (50% of buy price)
        sell_price = item_to_sell['price'] // 2

        # Create confirmation UI
        class SellView(View):
            def __init__(self):
                super().__init__(timeout=30)

            @discord.ui.button(label="Confirm Sale", style=discord.ButtonStyle.success)
            async def confirm(self, interaction: discord.Interaction, button: Button):
                # Process sale
                hunter['gold'] = hunter.get('gold', 0) + sell_price
                del inventory[item_index]
                self.save_hunters_data(hunters_data)

                embed = discord.Embed(
                    title="✅ Item Sold!",
                    description=f"You sold {item_to_sell['name']} for 🪙 {sell_price}",
                    color=discord.Color.green()
                )
                embed.add_field(name="New Balance", value=f"🪙 {hunter['gold']}")
                await interaction.response.send_message(embed=embed)

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, interaction: discord.Interaction, button: Button):
                await interaction.response.send_message("Sale cancelled.", ephemeral=True)

        embed = discord.Embed(
            title="💰 Confirm Sale",
            description=f"Sell {item_to_sell['name']} for 🪙 {sell_price}?",
            color=discord.Color.blue()
        )
        embed.add_field(name="Original Price", value=f"🪙 {item_to_sell['price']}")
        await ctx.send(embed=embed, view=SellView())

async def setup(bot):
    await bot.add_cog(Shop(bot))
