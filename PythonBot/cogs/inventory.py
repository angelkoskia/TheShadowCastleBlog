import discord
from discord.ext import commands
import json
import os

class Inventory(commands.Cog):
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

    @commands.command(name='inventory', aliases=['inv'])
    async def show_inventory(self, ctx):
        """Display your inventory and equipped items"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You haven't started your journey yet! Use !start first.")
            return

        hunter = hunters_data[user_id]
        inventory = hunter.get('inventory', [])
        equipment = hunter.get('equipment', {})

        embed = discord.Embed(title=f"{ctx.author.name}'s Inventory", color=0x00ff00)

        # Show equipped items
        equipped = "```\n"
        equipped += f"Weapon: {equipment.get('weapon', 'None')}\n"
        equipped += f"Armor: {equipment.get('armor', 'None')}\n"
        equipped += f"Accessory: {equipment.get('accessory', 'None')}\n"
        equipped += "```"
        embed.add_field(name="Equipped Items", value=equipped, inline=False)

        # Show inventory items
        if inventory:
            inv_text = "```\n"
            item_count = {}
            for item in inventory:
                if item in item_count:
                    item_count[item] += 1
                else:
                    item_count[item] = 1

            for item, count in item_count.items():
                inv_text += f"{item} x{count}\n"
            inv_text += "```"
        else:
            inv_text = "Your inventory is empty!"

        embed.add_field(name="Inventory", value=inv_text, inline=False)

        # Show gold
        embed.add_field(name="Gold", value=str(hunter.get('gold', 0)), inline=True)

        await ctx.send(embed=embed)

    @commands.command(name='equip')
    async def equip_item(self, ctx, *, item_name: str):
        """Equip an item from your inventory"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You haven't started your journey yet! Use !start first.")
            return

        hunter = hunters_data[user_id]
        inventory = hunter.get('inventory', [])

        if item_name not in inventory:
            await ctx.send(f"You don't have {item_name} in your inventory!")
            return

        # Find item type
        item_type = None
        item_data = None
        for category in self.items_data:
            if item_name in self.items_data[category]:
                item_data = self.items_data[category][item_name]
                item_type = item_data['type']
                break

        if not item_type:
            await ctx.send("This item cannot be equipped!")
            return

        # Unequip current item if exists
        current_equipped = hunter['equipment'].get(item_type)
        if current_equipped:
            inventory.append(current_equipped)

        # Equip new item
        hunter['equipment'][item_type] = item_name
        inventory.remove(item_name)

        # Update stats based on equipment
        if 'attack' in item_data:
            hunter['attack_bonus'] = item_data['attack']
        if 'defense' in item_data:
            hunter['defense_bonus'] = item_data['defense']

        self.save_hunters_data(hunters_data)
        await ctx.send(f"Successfully equipped {item_name}!")

    @commands.command(name='unequip')
    async def unequip_item(self, ctx, item_type: str):
        """Unequip an item (weapon/armor/accessory)"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You haven't started your journey yet! Use !start first.")
            return

        hunter = hunters_data[user_id]
        if item_type not in hunter['equipment'] or not hunter['equipment'][item_type]:
            await ctx.send(f"You don't have anything equipped in the {item_type} slot!")
            return

        item_name = hunter['equipment'][item_type]
        hunter['inventory'].append(item_name)
        hunter['equipment'][item_type] = None

        # Remove stat bonuses
        if item_type == 'weapon':
            hunter['attack_bonus'] = 0
        elif item_type == 'armor':
            hunter['defense_bonus'] = 0

        self.save_hunters_data(hunters_data)
        await ctx.send(f"Successfully unequipped {item_name}!")

    @commands.command(name='use')
    async def use_item(self, ctx, *, item_name: str):
        """Use a consumable item"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send("You haven't started your journey yet! Use !start first.")
            return

        hunter = hunters_data[user_id]
        inventory = hunter.get('inventory', [])

        if item_name not in inventory:
            await ctx.send(f"You don't have {item_name} in your inventory!")
            return

        # Check if item is usable
        item_data = None
        for category in self.items_data:
            if item_name in self.items_data[category]:
                item_data = self.items_data[category][item_name]
                break

        if not item_data or item_data['type'] not in ['consumable', 'buff']:
            await ctx.send("This item cannot be used!")
            return

        # Apply item effects
        effect = item_data['effect']
        if effect['type'] == 'heal':
            hunter['hp'] = min(100, hunter['hp'] + effect['value'])
            message = f"Restored {effect['value']} HP!"
        elif effect['type'] == 'restore_mp':
            hunter['mp'] = min(100, hunter['mp'] + effect['value'])
            message = f"Restored {effect['value']} MP!"
        elif effect['type'] == 'strength':
            hunter['temp_strength_bonus'] = effect['value']
            hunter['buff_duration'] = effect['duration']
            message = f"Increased strength by {effect['value']} for {effect['duration']} seconds!"

        # Remove item from inventory
        inventory.remove(item_name)
        self.save_hunters_data(hunters_data)

        await ctx.send(f"Used {item_name}! {message}")

async def setup(bot):
    await bot.add_cog(Inventory(bot))
