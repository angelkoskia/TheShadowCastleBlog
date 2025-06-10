import discord
from discord.ext import commands
import json
import os
from discord.ui import View, Button

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
            await ctx.send(embed=discord.Embed(description="You haven't started your journey yet! Use #start first.", color=discord.Color.red()))
            return

        hunter = hunters_data[user_id]
        inventory = hunter.get('inventory', [])
        equipment = hunter.get('equipment', {})

        embed = discord.Embed(title=f"{ctx.author.name}'s Inventory", color=discord.Color.gold())

        # Show equipped items
        equipped = (
            f"🗡️ Weapon: {equipment.get('weapon', 'None')}\n"
            f"🛡️ Armor: {equipment.get('armor', 'None')}\n"
            f"💍 Accessory: {equipment.get('accessory', 'None')}"
        )
        embed.add_field(name="Equipped Items", value=equipped, inline=False)

        # Show inventory items
        if inventory:
            item_count = {}
            for item in inventory:
                if item in item_count:
                    item_count[item] += 1
                else:
                    item_count[item] = 1
            inv_text = ""
            for item, count in item_count.items():
                inv_text += f"{item} x{count}\n"
        else:
            inv_text = "Your inventory is empty!"
        embed.add_field(name="Inventory", value=inv_text, inline=False)

        # Show gold
        embed.add_field(name="🪙 Gold", value=str(hunter.get('gold', 0)), inline=True)
        embed.set_footer(text="Use #equip <item> or #unequip <type> to manage equipment.")

        # Modern UI: Add equip/unequip buttons for equipped slots
        class InventoryView(View):
            def __init__(self, parent, ctx, hunter, equipment):
                super().__init__(timeout=60)
                self.parent = parent
                self.ctx = ctx
                self.hunter = hunter
                self.equipment = equipment
                for slot in ['weapon', 'armor', 'accessory']:
                    if equipment.get(slot):
                        self.add_item(Button(label=f"Unequip {slot.title()}", style=discord.ButtonStyle.secondary, custom_id=f"unequip_{slot}"))

            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                return interaction.user.id == ctx.author.id

            @discord.ui.button(label="Refresh", style=discord.ButtonStyle.primary, emoji="🔄", custom_id="refresh")
            async def refresh_button(self, interaction: discord.Interaction, button: Button):
                await interaction.response.defer()
                await self.parent.show_inventory(self.ctx)

            async def on_error(self, error, item, interaction):
                await interaction.response.send_message("An error occurred.", ephemeral=True)

            async def on_timeout(self):
                pass

            async def interaction(self, interaction: discord.Interaction):
                # Handle unequip actions
                if interaction.data['custom_id'].startswith('unequip_'):
                    slot = interaction.data['custom_id'].split('_')[1]
                    await self.parent.unequip_item_button(self.ctx, slot, interaction)

        await ctx.send(embed=embed, view=InventoryView(self, ctx, hunter, equipment))

    async def unequip_item_button(self, ctx, item_type, interaction):
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        hunter = hunters_data[user_id]
        if item_type not in hunter['equipment'] or not hunter['equipment'][item_type]:
            await interaction.response.send_message(f"You don't have anything equipped in the {item_type} slot!", ephemeral=True)
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
        await interaction.response.send_message(f"Successfully unequipped {item_name}!", ephemeral=True)
        await self.show_inventory(ctx)

    @commands.command(name='equip')
    async def equip_item(self, ctx, *, item_name: str):
        """Equip an item from your inventory"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send(embed=discord.Embed(description="You haven't started your journey yet! Use #start first.", color=discord.Color.red()))
            return

        hunter = hunters_data[user_id]
        inventory = hunter.get('inventory', [])

        if item_name not in inventory:
            await ctx.send(embed=discord.Embed(description=f"You don't have {item_name} in your inventory!", color=discord.Color.orange()))
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
            await ctx.send(embed=discord.Embed(description="This item cannot be equipped!", color=discord.Color.red()))
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
        await ctx.send(embed=discord.Embed(description=f"Successfully equipped {item_name}!", color=discord.Color.green()))

    @commands.command(name='unequip')
    async def unequip_item(self, ctx, item_type: str):
        """Unequip an item (weapon/armor/accessory)"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send(embed=discord.Embed(description="You haven't started your journey yet! Use #start first.", color=discord.Color.red()))
            return

        hunter = hunters_data[user_id]
        if item_type not in hunter['equipment'] or not hunter['equipment'][item_type]:
            await ctx.send(embed=discord.Embed(description=f"You don't have anything equipped in the {item_type} slot!", color=discord.Color.orange()))
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
        await ctx.send(embed=discord.Embed(description=f"Successfully unequipped {item_name}!", color=discord.Color.green()))

    @commands.command(name='use')
    async def use_item(self, ctx, *, item_name: str):
        """Use a consumable item"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)

        if user_id not in hunters_data:
            await ctx.send(embed=discord.Embed(description="You haven't started your journey yet! Use #start first.", color=discord.Color.red()))
            return

        hunter = hunters_data[user_id]
        inventory = hunter.get('inventory', [])

        if item_name not in inventory:
            await ctx.send(embed=discord.Embed(description=f"You don't have {item_name} in your inventory!", color=discord.Color.orange()))
            return

        # Check if item is usable
        item_data = None
        for category in self.items_data:
            if item_name in self.items_data[category]:
                item_data = self.items_data[category][item_name]
                break

        if not item_data or item_data['type'] not in ['consumable', 'buff']:
            await ctx.send(embed=discord.Embed(description="This item cannot be used!", color=discord.Color.red()))
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

    @commands.command(name='status')
    async def show_status(self, ctx):
        """View your hunter profile and stats"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        if user_id not in hunters_data:
            await ctx.send(embed=discord.Embed(description="You haven't started your journey yet! Use #awaken first.", color=discord.Color.red()))
            return
        hunter = hunters_data[user_id]
        embed = discord.Embed(title=f"{ctx.author.name}'s Hunter Profile", color=discord.Color.blue())
        embed.add_field(name="Level", value=str(hunter.get('level', 1)), inline=True)
        embed.add_field(name="EXP", value=f"{hunter.get('exp', 0)}/{hunter.get('level', 1)*100}", inline=True)
        embed.add_field(name="Gold", value=str(hunter.get('gold', 0)), inline=True)
        embed.add_field(name="HP", value=f"{hunter.get('hp', 100)}/100", inline=True)
        embed.add_field(name="MP", value=f"{hunter.get('mp', 50)}/50", inline=True)
        embed.add_field(name="Strength", value=str(hunter.get('strength', 10)), inline=True)
        embed.add_field(name="Agility", value=str(hunter.get('agility', 10)), inline=True)
        # Abilities
        abilities = hunter.get('abilities', {})
        if abilities:
            abilities_str = '\n'.join([f"{name.title()}: {data['type'].title()} ({data['power']})" for name, data in abilities.items()])
        else:
            abilities_str = 'None'
        embed.add_field(name="Abilities", value=abilities_str, inline=False)
        # Equipment
        equipment = hunter.get('equipment', {})
        equipped = (
            f"🗡️ Weapon: {equipment.get('weapon', 'None')}\n"
            f"🛡️ Armor: {equipment.get('armor', 'None')}\n"
            f"💍 Accessory: {equipment.get('accessory', 'None')}"
        )
        embed.add_field(name="Equipped Items", value=equipped, inline=False)
        # Achievements
        achievements = (
            f"🏆 PvP Wins: {hunter.get('pvp_wins', 0)}\n"
            f"❌ PvP Losses: {hunter.get('pvp_losses', 0)}\n"
            f"👹 Monster Kills: {hunter.get('monster_kills', 0)}\n"
            f"💀 Deaths: {hunter.get('deaths', 0)}\n"
            f"🎯 Successful Raids: {hunter.get('successful_raids', 0)}\n"
            f"⚠️ Failed Raids: {hunter.get('failed_raids', 0)}"
        )
        embed.add_field(name="Achievements", value=achievements, inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Inventory(bot))
