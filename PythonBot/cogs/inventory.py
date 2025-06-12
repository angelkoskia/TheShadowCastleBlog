import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import json
import asyncio

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.items_data = self.load_items_data()
    
    def load_items_data(self):
        """Load items configuration from JSON file"""
        try:
            with open('data/items.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self.get_default_items()
    
    def get_default_items(self):
        """Default items configuration - should match data/items.json structure"""
        return {
            "weapons": {
                "Rusty Dagger": {"type": "weapon", "strength": 3, "value": 50, "rarity": "Common"},
                "Iron Sword": {"type": "weapon", "strength": 5, "value": 100, "rarity": "Common"},
                "Steel Blade": {"type": "weapon", "strength": 12, "value": 300, "rarity": "Uncommon"},
                "Demon Slayer": {"type": "weapon", "strength": 25, "value": 800, "rarity": "Rare"},
                "Dragon Fang": {"type": "weapon", "strength": 40, "value": 2000, "rarity": "Epic"},
                "Shadow Reaper": {"type": "weapon", "strength": 60, "value": 5000, "rarity": "Legendary"},
                "Monarch's Edge": {"type": "weapon", "strength": 100, "value": 15000, "rarity": "Mythic"}
            },
            "armor": {
                "Cloth Robe": {"type": "armor", "defense": 2, "value": 40, "rarity": "Common"},
                "Leather Vest": {"type": "armor", "defense": 5, "value": 80, "rarity": "Common"},
                "Chain Mail": {"type": "armor", "defense": 10, "value": 250, "rarity": "Uncommon"},
                "Knight's Plate": {"type": "armor", "defense": 20, "value": 600, "rarity": "Rare"},
                "Shadow Cloak": {"type": "armor", "defense": 35, "value": 1500, "rarity": "Epic"},
                "Dragon Scale Mail": {"type": "armor", "defense": 55, "value": 4000, "rarity": "Legendary"},
                "Monarch's Regalia": {"type": "armor", "defense": 80, "value": 12000, "rarity": "Mythic"}
            },
            "accessories": {
                "Hunter's Ring": {"type": "accessory", "agility": 5, "value": 150, "rarity": "Common"},
                "Mage's Amulet": {"type": "accessory", "intelligence": 10, "value": 400, "rarity": "Uncommon"},
                "Berserker's Band": {"type": "accessory", "strength": 15, "value": 700, "rarity": "Rare"},
                "Shadow Lord's Sigil": {"type": "accessory", "strength": 20, "agility": 15, "intelligence": 10, "value": 2500, "rarity": "Epic"},
                "Crown of Kings": {"type": "accessory", "strength": 30, "agility": 25, "intelligence": 20, "value": 8000, "rarity": "Legendary"}
            },
            "shields": {
                "Basic Shield": {"type": "shield", "defense": 5, "value": 75, "rarity": "Common"},
                "Iron Shield": {"type": "shield", "defense": 8, "value": 150, "rarity": "Common"},
                "Guardian Shield": {"type": "shield", "defense": 15, "value": 400, "rarity": "Rare"},
                "Knight's Shield": {"type": "shield", "defense": 20, "value": 600, "rarity": "Rare"},
                "Dragon Scale Shield": {"type": "shield", "defense": 30, "value": 1500, "rarity": "Epic"},
                "Aegis of the Ancients": {"type": "shield", "defense": 50, "strength": 15, "value": 5000, "rarity": "Legendary"}
            },
            "consumables": {
                "Health Potion": {"type": "consumable", "effect": "heal", "heal_amount": 50, "value": 50, "rarity": "Common"},
                "Mana Potion": {"type": "consumable", "effect": "mana", "mana_amount": 30, "value": 30, "rarity": "Common"},
                "Greater Health Potion": {"type": "consumable", "effect": "heal", "heal_amount": 150, "value": 200, "rarity": "Uncommon"},
                "Greater Mana Potion": {"type": "consumable", "effect": "mana", "mana_amount": 100, "value": 150, "rarity": "Uncommon"},
                "Experience Boost": {"type": "consumable", "effect": "exp_boost", "exp_amount": 200, "value": 300, "rarity": "Rare"}
            },
            "crafting_materials": {
                "Iron Ore": {"type": "material", "value": 20, "rarity": "Common"},
                "Steel Ingot": {"type": "material", "value": 80, "rarity": "Uncommon"},
                "Demon Horn": {"type": "material", "value": 300, "rarity": "Rare"},
                "Dragon Scale": {"type": "material", "value": 1000, "rarity": "Epic"},
                "Shadow Essence": {"type": "material", "value": 2000, "rarity": "Legendary"},
                "Monarch Fragment": {"type": "material", "value": 5000, "rarity": "Mythic"}
            }
        }
    
    def load_hunters_data(self):
        """Load hunter data from JSON file"""
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_hunters_data(self, data):
        """Save hunter data to JSON file"""
        with open('hunters_data.json', 'w') as f:
            json.dump(data, f, indent=4)
    
    def get_item_info(self, item_name):
        """Get item information from all categories"""
        for category in self.items_data.values():
            if item_name in category:
                return category[item_name]
        return None
    
    def update_hunter_stats(self, hunter):
        """Update hunter's total stats including equipment bonuses"""
        # Store base stats (without equipment)
        if 'base_strength' not in hunter:
            hunter['base_strength'] = hunter.get('strength', 10)
            hunter['base_agility'] = hunter.get('agility', 10)
            hunter['base_intelligence'] = hunter.get('intelligence', 10)
        
        # Reset to base stats
        hunter['strength'] = hunter['base_strength']
        hunter['agility'] = hunter['base_agility'] 
        hunter['intelligence'] = hunter['base_intelligence']
        
        # Add equipment bonuses
        equipment = hunter.get('equipment', {})
        for item_name in equipment.values():
            if item_name:
                item_info = self.get_item_info(item_name)
                if item_info:
                    hunter['strength'] += item_info.get('strength', 0)
                    hunter['agility'] += item_info.get('agility', 0)
                    hunter['intelligence'] += item_info.get('intelligence', 0)
                    hunter['defense'] = hunter.get('defense', 0) + item_info.get('defense', 0)
    
    def get_rarity_color(self, rarity):
        """Get Discord color based on item rarity"""
        colors = {
            "Common": discord.Color.light_grey(),
            "Uncommon": discord.Color.green(),
            "Rare": discord.Color.blue(),
            "Epic": discord.Color.purple(),
            "Legendary": discord.Color.gold(),
            "Mythic": discord.Color.from_rgb(255, 20, 147)  # Deep pink for mythic
        }
        return colors.get(rarity, discord.Color.default())
    
    @commands.command(name='inventory', aliases=['inv'])
    async def show_inventory(self, ctx):
        """Display hunter's inventory"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        
        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use `.start`")
            return
        
        hunter = hunters_data[user_id]
        inventory = hunter.get('inventory', {})
        equipment = hunter.get('equipment', {})
        
        # Handle both old list format and new dict format
        if isinstance(inventory, list):
            # Convert old list format to new dict format
            old_items = inventory
            inventory = {}
            for item in old_items:
                inventory[item] = inventory.get(item, 0) + 1
            hunter['inventory'] = inventory
            self.save_hunters_data(hunters_data)
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        embed = discord.Embed(
            title="🎒 Inventory",
            description="Your items and equipment",
            color=discord.Color(colors['accent'])
        )
        
        # Show equipped items with proper icons
        equipped_text = ""
        slot_icons = {
            'weapon': '⚔️',
            'armor': '🛡️', 
            'accessory': '💍',
            'shield': '🔰'
        }
        
        # Display in specific order
        equipment_order = ['weapon', 'armor', 'shield', 'accessory']
        for slot in equipment_order:
            item = equipment.get(slot)
            icon = slot_icons.get(slot, '📭')
            if item:
                item_info = self.get_item_info(item)
                rarity = item_info.get('rarity', 'Common') if item_info else 'Common'
                slot_name = "Offhand" if slot == 'shield' else slot.title()
                equipped_text += f"{icon} {slot_name}: **{item}** ({rarity})\n"
            else:
                slot_name = "Offhand" if slot == 'shield' else slot.title()
                equipped_text += f"📭 {slot_name}: *None*\n"
        
        embed.add_field(name="⚔️ Equipped", value=equipped_text or "Nothing equipped", inline=False)
        
        # Show inventory items
        if inventory:
            inventory_text = ""
            for item, count in inventory.items():
                # Ensure count is an integer
                try:
                    count = int(count) if count is not None else 0
                except (ValueError, TypeError):
                    count = 0
                
                if count > 0:
                    item_info = self.get_item_info(item)
                    rarity = item_info.get('rarity', 'Common') if item_info else 'Common'
                    count_text = f" x{count}" if count > 1 else ""
                    inventory_text += f"• **{item}** ({rarity}){count_text}\n"
            
            embed.add_field(name="📦 Items", value=inventory_text[:1024] if inventory_text else "Your inventory is empty", inline=False)
        else:
            embed.add_field(name="📦 Items", value="Your inventory is empty", inline=False)
        
        embed.add_field(
            name="💰 Gold",
            value=f"{hunter.get('gold', 0)} coins",
            inline=True
        )
        
        embed.set_footer(text="Use buttons below to interact with items • Select an item first")
        
        # Create interactive inventory view
        view = InteractiveInventoryView(ctx, hunter, self)
        message = await ctx.send(embed=embed, view=view)
        view.message = message
    
    @commands.command(name='equip')
    async def equip_item(self, ctx, *, item_name):
        """Equip an item from inventory"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        
        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use `.start`")
            return
        
        hunter = hunters_data[user_id]
        inventory = hunter.get('inventory', {})
        
        # Handle both old list format and new dict format
        if isinstance(inventory, list):
            # Convert old list format to new dict format
            old_items = inventory
            inventory = {}
            for item in old_items:
                inventory[item] = inventory.get(item, 0) + 1
            hunter['inventory'] = inventory
        
        # Find item in inventory
        item_found = None
        for item_name_key, quantity in inventory.items():
            # Ensure quantity is an integer
            try:
                quantity = int(quantity) if quantity is not None else 0
            except (ValueError, TypeError):
                quantity = 0
            
            if item_name_key.lower() == item_name.lower() and quantity > 0:
                item_found = item_name_key
                break
        
        if not item_found:
            await ctx.send(f"You don't have '{item_name}' in your inventory!")
            return
        
        # Get item info
        item_info = self.get_item_info(item_found)
        if not item_info:
            await ctx.send("Item information not found!")
            return
        
        item_type = item_info['type']
        if item_type not in ['weapon', 'armor', 'accessory', 'shield']:
            await ctx.send("This item cannot be equipped!")
            return
        
        # Equip the item
        equipment = hunter.get('equipment', {})
        old_item = equipment.get(item_type)
        
        # Remove from inventory (dict format)
        inventory[item_found] -= 1
        if inventory[item_found] <= 0:
            del inventory[item_found]
        
        # Add old item back to inventory if exists
        if old_item:
            inventory[old_item] = inventory.get(old_item, 0) + 1
        
        # Update quest progress for equipping items
        try:
            from daily_quest_system import update_quest_progress
            update_quest_progress(hunter, "equip_items", 1)
        except:
            pass
        
        # Equip new item
        equipment[item_type] = item_found
        hunter['equipment'] = equipment
        
        # Update total stats with equipment bonuses
        from main import update_hunter_equipment_stats
        update_hunter_equipment_stats(hunter)
        
        self.save_hunters_data(hunters_data)
        
        embed = discord.Embed(
            title="⚔️ Equipment Updated!",
            description=f"Successfully equipped **{item_found}**",
            color=self.get_rarity_color(item_info.get('rarity', 'Common'))
        )
        
        if old_item:
            embed.add_field(name="Previous Item", value=f"Unequipped: {old_item}", inline=False)
        
        # Show item stats
        stats_text = ""
        for stat, value in item_info.items():
            if stat not in ['type', 'value', 'rarity']:
                stats_text += f"{stat.title()}: +{value}\n"
        
        if stats_text:
            embed.add_field(name="Item Stats", value=stats_text, inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='use')
    async def use_item(self, ctx, *, item_name):
        """Use a consumable item or special key"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        
        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use `.start`")
            return
        
        hunter = hunters_data[user_id]
        inventory = hunter.get('inventory', {})
        
        # Handle both old list format and new dict format
        if isinstance(inventory, list):
            old_items = inventory
            inventory = {}
            for item in old_items:
                inventory[item] = inventory.get(item, 0) + 1
            hunter['inventory'] = inventory
        
        # Find item in inventory (case insensitive)
        item_found = None
        for item in inventory.keys():
            if item.lower() == item_name.lower():
                item_found = item
                break
        
        if not item_found or inventory.get(item_found, 0) <= 0:
            await ctx.send(f"You don't have '{item_name}' in your inventory!")
            return
        
        # Get item info
        item_info = self.get_item_info(item_found)
        if not item_info:
            await ctx.send("Item information not found!")
            return
        
        item_type = item_info.get('type')
        
        # Handle special keys
        if item_type in ['red_key', 'special_key']:
            await self.use_special_key(ctx, hunter, item_found, item_info, inventory)
            return
        
        # Handle consumables
        if item_type != 'consumable':
            await ctx.send("This item cannot be used!")
            return
        
        # Use the item
        effect = item_info.get('effect')
        result_text = ""
        
        if effect == 'heal':
            heal_amount = item_info.get('heal_amount', 50)
            old_hp = hunter['hp']
            max_hp = hunter.get('max_hp', 100)
            hunter['hp'] = min(max_hp, hunter['hp'] + heal_amount)
            actual_heal = hunter['hp'] - old_hp
            result_text = f"Restored {actual_heal} HP! Current HP: {hunter['hp']}/{max_hp}"
        
        elif effect == 'mana':
            mana_amount = item_info.get('mana_amount', 30)
            old_mp = hunter['mp']
            hunter['mp'] = min(hunter['max_mp'], hunter['mp'] + mana_amount)
            actual_mana = hunter['mp'] - old_mp
            result_text = f"Restored {actual_mana} MP! Current MP: {hunter['mp']}/{hunter['max_mp']}"
        
        elif effect == 'revive':
            # Check if player has death timer
            import time
            if 'death_timer' not in hunter or time.time() >= hunter['death_timer']:
                await ctx.send("You are not under a death penalty! The revive potion has no effect.")
                return
            
            # Remove death timer
            del hunter['death_timer']
            result_text = "Death penalty timer removed! All activities are now available."
        
        elif effect == 'exp_boost':
            exp_boost = item_info.get('exp_amount', 100)
            hunter['exp'] += exp_boost
            result_text = f"Gained {exp_boost} bonus EXP!"
        
        # Remove one item from inventory (dict format)
        inventory[item_found] -= 1
        if inventory[item_found] <= 0:
            del inventory[item_found]
        
        self.save_hunters_data(hunters_data)
        
        embed = discord.Embed(
            title="✨ Item Used!",
            description=f"Used **{item_found}**",
            color=discord.Color.green()
        )
        embed.add_field(name="Effect", value=result_text, inline=False)
        embed.add_field(name="Remaining", value=f"Items in inventory: {len(hunter.get('inventory', []))}", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='debug_inventory')
    async def debug_inventory(self, ctx):
        """Debug command to check inventory issues"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        
        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use `.start`")
            return
        
        hunter = hunters_data[user_id]
        inventory = hunter.get('inventory', [])
        
        embed = discord.Embed(
            title="🔍 Inventory Debug Info",
            description=f"Debugging inventory for {ctx.author.name}",
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="Raw Inventory",
            value=f"Items: {inventory}\nCount: {len(inventory)}",
            inline=False
        )
        
        # Check each item
        valid_items = []
        invalid_items = []
        
        for item in inventory:
            item_info = self.get_item_info(item)
            if item_info:
                valid_items.append(f"{item} ({item_info['type']})")
            else:
                invalid_items.append(item)
        
        if valid_items:
            embed.add_field(name="Valid Items", value="\n".join(valid_items[:10]), inline=False)
        
        if invalid_items:
            embed.add_field(name="Invalid Items", value="\n".join(invalid_items[:10]), inline=False)
        
        await ctx.send(embed=embed)
    
    async def use_special_key(self, ctx, hunter, item_name, item_info, inventory):
        """Handle using special keys for gates and dungeons"""
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        key_type = item_info.get('type')
        
        if key_type == 'red_key':
            # Red Gate Key usage
            embed = discord.Embed(
                title="🔴 Red Gate Access Granted!",
                description=f"You used the **{item_name}** to unlock access to a dangerous Red Gate!",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="🚨 Warning",
                value="Red Gates are extremely dangerous dimensional rifts that can appear randomly.\nOnly the strongest hunters should attempt these!",
                inline=False
            )
            
            embed.add_field(
                name="🎯 Access Unlocked",
                value="You can now enter Red Gates when they appear.\nUse `.enter_gate Red Gate` when one becomes available.",
                inline=False
            )
            
            # Add red gate access to hunter profile
            if 'special_access' not in hunter:
                hunter['special_access'] = {}
            hunter['special_access']['red_gates'] = True
            
        elif key_type == 'special_key':
            # Special Dungeon Key usage
            key_color = "Red" if "Red" in item_name else "Blue" if "Blue" in item_name else "Gold"
            
            embed = discord.Embed(
                title=f"🔑 {key_color} Dungeon Access!",
                description=f"You used the **{item_name}** to unlock special dungeon access!",
                color=discord.Color.gold() if key_color == "Gold" else discord.Color.blue() if key_color == "Blue" else discord.Color.red()
            )
            
            embed.add_field(
                name="🏰 Special Dungeons",
                value=f"{key_color} dungeons contain unique monsters and legendary rewards.\nThese dungeons are more challenging than regular ones.",
                inline=False
            )
            
            embed.add_field(
                name="🎯 Access Unlocked", 
                value=f"You can now access {key_color} special dungeons.\nUse `.raid {key_color} Dungeon` to enter.",
                inline=False
            )
            
            # Add special dungeon access
            if 'special_access' not in hunter:
                hunter['special_access'] = {}
            if 'special_dungeons' not in hunter['special_access']:
                hunter['special_access']['special_dungeons'] = []
            
            if key_color not in hunter['special_access']['special_dungeons']:
                hunter['special_access']['special_dungeons'].append(key_color)
        
        # Remove one key from inventory
        inventory[item_name] -= 1
        if inventory[item_name] <= 0:
            del inventory[item_name]
        
        # Save changes
        hunters_data = self.load_hunters_data()
        hunters_data[str(ctx.author.id)] = hunter
        self.save_hunters_data(hunters_data)
        
        embed.set_footer(text="Special access has been permanently unlocked for your hunter!")
        await ctx.send(embed=embed)

class InteractiveInventoryView(View):
    """Interactive inventory with dropdown selection and action buttons"""
    
    def __init__(self, ctx, hunter, inventory_cog):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.hunter = hunter
        self.inventory_cog = inventory_cog
        self.selected_item = None
        self.message = None
        
        # Add item selection dropdown
        self.add_item(ItemSelectDropdown(self))
        
        # Add action buttons (initially disabled)
        self.equip_button = Button(label="Equip/Unequip", style=discord.ButtonStyle.primary, disabled=True)
        self.equip_button.callback = self.equip_callback
        self.add_item(self.equip_button)
        
        self.use_button = Button(label="Use Item", style=discord.ButtonStyle.green, disabled=True)
        self.use_button.callback = self.use_callback
        self.add_item(self.use_button)
        
        self.sell_button = Button(label="Sell Item", style=discord.ButtonStyle.red, disabled=True)
        self.sell_button.callback = self.sell_callback
        self.add_item(self.sell_button)
        
        self.refresh_button = Button(label="🔄 Refresh", style=discord.ButtonStyle.grey)
        self.refresh_button.callback = self.refresh_callback
        self.add_item(self.refresh_button)
    
    async def on_timeout(self):
        """Handle view timeout"""
        for item in self.children:
            item.disabled = True
        
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass
    
    def update_buttons(self):
        """Update button states based on selected item"""
        if not self.selected_item:
            self.equip_button.disabled = True
            self.use_button.disabled = True
            self.sell_button.disabled = True
            return
        
        item_info = self.inventory_cog.get_item_info(self.selected_item)
        if not item_info:
            self.equip_button.disabled = True
            self.use_button.disabled = True
            self.sell_button.disabled = True
            return
        
        item_type = item_info.get('type', '')
        
        # Enable/disable buttons based on item type
        self.equip_button.disabled = item_type not in ['weapon', 'armor', 'accessory', 'shield']
        self.use_button.disabled = item_type != 'consumable'
        self.sell_button.disabled = False  # Can always sell items
    
    async def equip_callback(self, interaction):
        """Handle equip/unequip button press"""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the command user can interact with this inventory!", ephemeral=True)
            return
        
        if not self.selected_item:
            await interaction.response.send_message("Please select an item first!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Load fresh data
        hunters_data = self.inventory_cog.load_hunters_data()
        user_id = str(self.ctx.author.id)
        hunter = hunters_data.get(user_id, {})
        
        item_info = self.inventory_cog.get_item_info(self.selected_item)
        if not item_info:
            await interaction.followup.send("Item information not found!", ephemeral=True)
            return
        
        item_type = item_info['type']
        equipment = hunter.get('equipment', {})
        inventory = hunter.get('inventory', {})
        
        # Check if item is currently equipped
        currently_equipped = equipment.get(item_type) == self.selected_item
        
        if currently_equipped:
            # Unequip the item
            equipment[item_type] = None
            inventory[self.selected_item] = inventory.get(self.selected_item, 0) + 1
            action = "unequipped"
        else:
            # Equip the item
            if inventory.get(self.selected_item, 0) <= 0:
                await interaction.followup.send("You don't have this item in your inventory!", ephemeral=True)
                return
            
            # Remove from inventory
            inventory[self.selected_item] -= 1
            if inventory[self.selected_item] <= 0:
                del inventory[self.selected_item]
            
            # Add old item back to inventory if exists
            old_item = equipment.get(item_type)
            if old_item:
                inventory[old_item] = inventory.get(old_item, 0) + 1
            
            # Equip new item
            equipment[item_type] = self.selected_item
            action = "equipped"
        
        # Update hunter data
        hunter['equipment'] = equipment
        hunter['inventory'] = inventory
        hunters_data[user_id] = hunter
        
        # Update stats
        self.inventory_cog.update_hunter_stats(hunter)
        self.inventory_cog.save_hunters_data(hunters_data)
        
        await interaction.followup.send(f"Successfully {action} **{self.selected_item}**!", ephemeral=True)
        
        # Refresh the inventory display
        await self.refresh_inventory()
    
    async def use_callback(self, interaction):
        """Handle use item button press"""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the command user can interact with this inventory!", ephemeral=True)
            return
        
        if not self.selected_item:
            await interaction.response.send_message("Please select an item first!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Load fresh data
        hunters_data = self.inventory_cog.load_hunters_data()
        user_id = str(self.ctx.author.id)
        hunter = hunters_data.get(user_id, {})
        inventory = hunter.get('inventory', {})
        
        if inventory.get(self.selected_item, 0) <= 0:
            await interaction.followup.send("You don't have this item in your inventory!", ephemeral=True)
            return
        
        item_info = self.inventory_cog.get_item_info(self.selected_item)
        if not item_info or item_info.get('type') != 'consumable':
            await interaction.followup.send("This item cannot be used!", ephemeral=True)
            return
        
        # Use the item
        inventory[self.selected_item] -= 1
        if inventory[self.selected_item] <= 0:
            del inventory[self.selected_item]
        
        # Apply item effects
        effect = item_info.get('effect', '')
        result_msg = f"Used **{self.selected_item}**"
        
        if effect == 'heal':
            heal_amount = item_info.get('heal_amount', 50)
            old_hp = hunter.get('hp', 0)
            max_hp = hunter.get('max_hp', 100)
            hunter['hp'] = min(max_hp, old_hp + heal_amount)
            actual_heal = hunter['hp'] - old_hp
            result_msg += f" and restored {actual_heal} HP!"
        
        elif effect == 'mana':
            mana_amount = item_info.get('mana_amount', 30)
            old_mp = hunter.get('mp', 0)
            max_mp = hunter.get('max_mp', 50)
            hunter['mp'] = min(max_mp, old_mp + mana_amount)
            actual_mana = hunter['mp'] - old_mp
            result_msg += f" and restored {actual_mana} MP!"
        
        elif effect == 'exp_boost':
            exp_amount = item_info.get('exp_amount', 200)
            from main import award_exp
            level_data = await award_exp(user_id, exp_amount, self.inventory_cog.bot)
            result_msg += f" and gained {exp_amount} EXP!"
            
            if level_data.get('levels_gained', 0) > 0:
                result_msg += f"\nLevel up! {level_data['old_level']} → {level_data['new_level']}"
        
        # Save data
        hunter['inventory'] = inventory
        hunters_data[user_id] = hunter
        self.inventory_cog.save_hunters_data(hunters_data)
        
        await interaction.followup.send(result_msg, ephemeral=True)
        
        # Refresh the inventory display
        await self.refresh_inventory()
    
    async def sell_callback(self, interaction):
        """Handle sell item button press"""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the command user can interact with this inventory!", ephemeral=True)
            return
        
        if not self.selected_item:
            await interaction.response.send_message("Please select an item first!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Load fresh data
        hunters_data = self.inventory_cog.load_hunters_data()
        user_id = str(self.ctx.author.id)
        hunter = hunters_data.get(user_id, {})
        inventory = hunter.get('inventory', {})
        
        if inventory.get(self.selected_item, 0) <= 0:
            await interaction.followup.send("You don't have this item in your inventory!", ephemeral=True)
            return
        
        item_info = self.inventory_cog.get_item_info(self.selected_item)
        if not item_info:
            await interaction.followup.send("Item information not found!", ephemeral=True)
            return
        
        # Calculate sell price (50% of original value)
        original_price = item_info.get('value', 10)
        sell_price = max(1, original_price // 2)
        
        # Remove item and add gold
        inventory[self.selected_item] -= 1
        if inventory[self.selected_item] <= 0:
            del inventory[self.selected_item]
        
        hunter['gold'] = hunter.get('gold', 0) + sell_price
        
        # Save data
        hunter['inventory'] = inventory
        hunters_data[user_id] = hunter
        self.inventory_cog.save_hunters_data(hunters_data)
        
        await interaction.followup.send(f"Sold **{self.selected_item}** for {sell_price} gold!\nTotal gold: {hunter['gold']}", ephemeral=True)
        
        # Refresh the inventory display
        await self.refresh_inventory()
    
    async def refresh_callback(self, interaction):
        """Handle refresh button press"""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the command user can interact with this inventory!", ephemeral=True)
            return
        
        await interaction.response.defer()
        await self.refresh_inventory()
        await interaction.followup.send("Inventory refreshed!", ephemeral=True)
    
    async def refresh_inventory(self):
        """Refresh the inventory display"""
        # Load fresh data
        hunters_data = self.inventory_cog.load_hunters_data()
        user_id = str(self.ctx.author.id)
        self.hunter = hunters_data.get(user_id, {})
        
        # Clear selection
        self.selected_item = None
        self.update_buttons()
        
        # Update dropdown
        for item in self.children:
            if isinstance(item, ItemSelectDropdown):
                item.options = item.create_options(self.hunter)
                break
        
        # Create new embed
        embed = self.create_inventory_embed()
        
        try:
            await self.message.edit(embed=embed, view=self)
        except:
            pass
    
    def create_inventory_embed(self):
        """Create the inventory embed"""
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(self.ctx.author.id)
        
        embed = discord.Embed(
            title="🎒 Interactive Inventory",
            description="Select an item from the dropdown below to interact with it",
            color=discord.Color(colors['accent'])
        )
        
        # Show equipped items
        equipment = self.hunter.get('equipment', {})
        equipped_text = ""
        slot_icons = {
            'weapon': '⚔️',
            'armor': '🛡️', 
            'accessory': '💍',
            'shield': '🔰'
        }
        
        for slot in ['weapon', 'armor', 'shield', 'accessory']:
            item = equipment.get(slot)
            icon = slot_icons.get(slot, '📭')
            if item:
                item_info = self.inventory_cog.get_item_info(item)
                rarity = item_info.get('rarity', 'Common') if item_info else 'Common'
                slot_name = "Offhand" if slot == 'shield' else slot.title()
                equipped_text += f"{icon} {slot_name}: **{item}** ({rarity})\n"
            else:
                slot_name = "Offhand" if slot == 'shield' else slot.title()
                equipped_text += f"📭 {slot_name}: *None*\n"
        
        embed.add_field(name="⚔️ Equipped", value=equipped_text or "Nothing equipped", inline=False)
        
        # Show inventory count
        inventory = self.hunter.get('inventory', {})
        total_items = sum(count for count in inventory.values() if isinstance(count, int) and count > 0)
        
        embed.add_field(
            name="📦 Inventory",
            value=f"Total items: {total_items}",
            inline=True
        )
        
        embed.add_field(
            name="💰 Gold",
            value=f"{self.hunter.get('gold', 0):,} coins",
            inline=True
        )
        
        if self.selected_item:
            item_info = self.inventory_cog.get_item_info(self.selected_item)
            if item_info:
                embed.add_field(
                    name=f"🔍 Selected: {self.selected_item}",
                    value=f"Type: {item_info.get('type', 'Unknown').title()}\nRarity: {item_info.get('rarity', 'Common')}",
                    inline=False
                )
        
        embed.set_footer(text="Select an item from the dropdown to use action buttons")
        return embed

class ItemSelectDropdown(Select):
    """Dropdown for selecting inventory items"""
    
    def __init__(self, parent_view):
        self.parent_view = parent_view
        options = self.create_options(parent_view.hunter)
        super().__init__(placeholder="Select an item to interact with...", options=options, min_values=0, max_values=1)
    
    def create_options(self, hunter):
        """Create dropdown options from inventory"""
        inventory = hunter.get('inventory', {})
        options = []
        
        # Add inventory items
        for item_name, count in inventory.items():
            if isinstance(count, int) and count > 0:
                item_info = self.parent_view.inventory_cog.get_item_info(item_name)
                rarity = item_info.get('rarity', 'Common') if item_info else 'Common'
                item_type = item_info.get('type', 'Unknown').title() if item_info else 'Unknown'
                
                emoji = "⚔️" if item_type == "Weapon" else "🛡️" if item_type == "Armor" else "💍" if item_type == "Accessory" else "🔰" if item_type == "Shield" else "🧪" if item_type == "Consumable" else "📦"
                
                description = f"{item_type} • {rarity}"
                if count > 1:
                    description += f" • x{count}"
                
                options.append(discord.SelectOption(
                    label=item_name[:25],  # Discord limit
                    description=description[:50],  # Discord limit
                    emoji=emoji,
                    value=item_name
                ))
        
        # Add equipment items (for unequipping)
        equipment = hunter.get('equipment', {})
        for slot, item_name in equipment.items():
            if item_name:
                item_info = self.parent_view.inventory_cog.get_item_info(item_name)
                rarity = item_info.get('rarity', 'Common') if item_info else 'Common'
                
                emoji = "⚔️" if slot == "weapon" else "🛡️" if slot == "armor" else "💍" if slot == "accessory" else "🔰"
                
                options.append(discord.SelectOption(
                    label=f"{item_name} (Equipped)"[:25],
                    description=f"Equipped {slot.title()} • {rarity}"[:50],
                    emoji=emoji,
                    value=item_name
                ))
        
        if not options:
            options.append(discord.SelectOption(
                label="No items available",
                description="Your inventory is empty",
                emoji="📭",
                value="empty"
            ))
        
        return options[:25]  # Discord limit
    
    async def callback(self, interaction):
        """Handle item selection"""
        if interaction.user.id != self.parent_view.ctx.author.id:
            await interaction.response.send_message("Only the command user can interact with this inventory!", ephemeral=True)
            return
        
        if self.values[0] == "empty":
            await interaction.response.send_message("No items to select!", ephemeral=True)
            return
        
        self.parent_view.selected_item = self.values[0]
        self.parent_view.update_buttons()
        
        # Update embed to show selected item
        embed = self.parent_view.create_inventory_embed()
        
        await interaction.response.edit_message(embed=embed, view=self.parent_view)

async def setup(bot):
    await bot.add_cog(Inventory(bot))
