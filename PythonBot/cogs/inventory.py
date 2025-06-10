import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import json

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_hunters_data(self):
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_hunters_data(self, data):
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    class InventoryView(View):
        def __init__(self, cog, user_id, page=0):
            super().__init__(timeout=60)
            self.cog = cog
            self.user_id = user_id
            self.page = page
            self.items_per_page = 5

        @discord.ui.button(label="Use", style=discord.ButtonStyle.primary, emoji="🔨")
        async def use_item(self, interaction: discord.Interaction, button: Button):
            hunters_data = self.cog.load_hunters_data()
            inventory = hunters_data[self.user_id].get('inventory', [])

            if not inventory:
                await interaction.response.send_message("Your inventory is empty!", ephemeral=True)
                return

            # Create item selection menu
            options = []
            for item in inventory:
                if item.get('type') == 'consumable':
                    options.append(discord.SelectOption(
                        label=item['name'],
                        description=f"Effect: {item.get('effect', 'Unknown')}",
                        value=item['id']
                    ))

            if not options:
                await interaction.response.send_message("No usable items found!", ephemeral=True)
                return

            select = Select(
                placeholder="Choose an item to use...",
                options=options[:25]  # Discord limits to 25 options
            )

            async def select_callback(interaction):
                await self.cog.use_item(interaction, select.values[0])

            select.callback = select_callback
            view = View()
            view.add_item(select)
            await interaction.response.send_message("Select an item to use:", view=view, ephemeral=True)

        @discord.ui.button(label="Equip", style=discord.ButtonStyle.success, emoji="⚔️")
        async def equip_item(self, interaction: discord.Interaction, button: Button):
            hunters_data = self.cog.load_hunters_data()
            inventory = hunters_data[self.user_id].get('inventory', [])

            if not inventory:
                await interaction.response.send_message("Your inventory is empty!", ephemeral=True)
                return

            # Create equipment selection menu
            options = []
            for item in inventory:
                if item.get('type') in ['weapon', 'armor', 'accessory']:
                    options.append(discord.SelectOption(
                        label=item['name'],
                        description=f"Type: {item['type'].title()}",
                        value=item['id']
                    ))

            if not options:
                await interaction.response.send_message("No equipment found!", ephemeral=True)
                return

            select = Select(
                placeholder="Choose equipment to equip...",
                options=options[:25]
            )

            async def select_callback(interaction):
                await self.cog.equip_item(interaction, select.values[0])

            select.callback = select_callback
            view = View()
            view.add_item(select)
            await interaction.response.send_message("Select equipment to equip:", view=view, ephemeral=True)

        @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, emoji="➡️")
        async def next_page(self, interaction: discord.Interaction, button: Button):
            hunters_data = self.cog.load_hunters_data()
            inventory = hunters_data[self.user_id].get('inventory', [])

            if (self.page + 1) * self.items_per_page < len(inventory):
                self.page += 1
                await self.cog.show_inventory(interaction, self.user_id, self.page)
            else:
                await interaction.response.send_message("No more items!", ephemeral=True)

    @commands.command(name='inventory')
    async def inventory(self, ctx):
        """View and manage your inventory"""
        user_id = str(ctx.author.id)
        hunters_data = self.load_hunters_data()

        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use #start")
            return

        await self.show_inventory(ctx, user_id)

    async def show_inventory(self, ctx, user_id, page=0):
        """Display inventory with pagination"""
        hunters_data = self.load_hunters_data()
        inventory = hunters_data[user_id].get('inventory', [])
        equipment = hunters_data[user_id].get('equipment', {})

        if not inventory:
            embed = discord.Embed(
                title="🎒 Inventory",
                description="Your inventory is empty!",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return

        items_per_page = 5
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(inventory))

        embed = discord.Embed(
            title="🎒 Inventory",
            color=discord.Color.blue()
        )

        # Show equipped items
        equipped = "```\n"
        equipped += f"Weapon: {equipment.get('weapon', 'None')}\n"
        equipped += f"Armor: {equipment.get('armor', 'None')}\n"
        equipped += f"Accessory: {equipment.get('accessory', 'None')}\n"
        equipped += "```"
        embed.add_field(name="📦 Equipped Items", value=equipped, inline=False)

        # Show inventory items
        for item in inventory[start_idx:end_idx]:
            embed.add_field(
                name=f"{item['name']}",
                value=f"Type: {item['type']}\n{item.get('description', 'No description')}",
                inline=False
            )

        embed.set_footer(text=f"Page {page + 1}/{(len(inventory) - 1) // items_per_page + 1}")

        await ctx.send(embed=embed, view=self.InventoryView(self, user_id, page))

    async def use_item(self, interaction, item_id):
        """Use a consumable item"""
        user_id = str(interaction.user.id)
        hunters_data = self.load_hunters_data()
        inventory = hunters_data[user_id].get('inventory', [])

        item = next((item for item in inventory if item['id'] == item_id), None)
        if not item:
            await interaction.response.send_message("Item not found!", ephemeral=True)
            return

        if item['type'] != 'consumable':
            await interaction.response.send_message("This item cannot be used!", ephemeral=True)
            return

        # Apply item effects
        if 'heal' in item.get('effects', {}):
            hunters_data[user_id]['hp'] = min(
                hunters_data[user_id]['hp'] + item['effects']['heal'],
                hunters_data[user_id]['max_hp']
            )

        # Remove item from inventory
        hunters_data[user_id]['inventory'] = [i for i in inventory if i['id'] != item_id]
        self.save_hunters_data(hunters_data)

        embed = discord.Embed(
            title="✨ Item Used",
            description=f"Used {item['name']}\n{item.get('use_message', 'The item was consumed.')}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    async def equip_item(self, interaction, item_id):
        """Equip a piece of equipment"""
        user_id = str(interaction.user.id)
        hunters_data = self.load_hunters_data()
        inventory = hunters_data[user_id].get('inventory', [])

        item = next((item for item in inventory if item['id'] == item_id), None)
        if not item:
            await interaction.response.send_message("Item not found!", ephemeral=True)
            return

        if item['type'] not in ['weapon', 'armor', 'accessory']:
            await interaction.response.send_message("This item cannot be equipped!", ephemeral=True)
            return

        # Unequip current item if any
        current_equipped = hunters_data[user_id]['equipment'].get(item['type'])
        if current_equipped:
            # Add current equipment back to inventory
            hunters_data[user_id]['inventory'].append(current_equipped)

        # Equip new item
        hunters_data[user_id]['equipment'][item['type']] = item
        # Remove from inventory
        hunters_data[user_id]['inventory'] = [i for i in inventory if i['id'] != item_id]

        # Update stats
        self.update_equipment_stats(hunters_data[user_id])

        self.save_hunters_data(hunters_data)

        embed = discord.Embed(
            title="⚔️ Equipment Changed",
            description=f"Equipped {item['name']}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    def update_equipment_stats(self, hunter):
        """Update hunter's stats based on equipped items"""
        # Reset bonus stats
        hunter['attack_bonus'] = 0
        hunter['defense_bonus'] = 0

        for slot, item in hunter['equipment'].items():
            if not item:
                continue
            # Add equipment bonuses
            hunter['attack_bonus'] += item.get('attack_bonus', 0)
            hunter['defense_bonus'] += item.get('defense_bonus', 0)

async def setup(bot):
    await bot.add_cog(Inventory(bot))
