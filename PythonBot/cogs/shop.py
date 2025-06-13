import discord
from discord.ext import commands
import json
import random
from discord.ui import View, Select, Button

class ShopView(View):
    """Interactive shop view with category navigation and item purchasing"""
    
    def __init__(self, bot, user_id, hunter_level, hunter_gold, items_data):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.hunter_level = hunter_level
        self.hunter_gold = hunter_gold
        self.items_data = items_data
        self.current_category = "basic_items"
        self.message = None
        
        # Add category selection dropdown
        self.add_item(CategorySelect(self))
    
    async def on_timeout(self):
        """Handle view timeout"""
        if self.message:
            try:
                embed = discord.Embed(
                    title="🏪 Shop Closed",
                    description="Shop session timed out. Use `.shop` to browse again.",
                    color=discord.Color.grey()
                )
                await self.message.edit(embed=embed, view=None)
            except:
                pass
    
    def get_shop_embed(self, colors):
        """Generate shop embed for current category"""
        embed = discord.Embed(
            title="🏪 Solo Leveling Hunter Shop",
            description=f"💰 Your Gold: **{self.hunter_gold:,}** | 👤 Level: **{self.hunter_level}**",
            color=discord.Color(colors['primary'])
        )
        
        category_titles = {
            "basic_items": "⚔️ Basic Equipment",
            "consumables": "🧪 Consumables & Potions", 
            "materials": "🔨 Crafting Materials",
            "weapons": "🗡️ Solo Leveling Legendary Weapons",
            "armor": "🛡️ Solo Leveling Armor",
            "accessories": "💍 Solo Leveling Accessories"
        }
        
        current_items = self.items_data.get(self.current_category, {})
        embed.add_field(
            name=category_titles.get(self.current_category, "Items"),
            value="_ _",
            inline=False
        )
        
        # Group items by tier
        tier_groups = {"UR": [], "SR": [], "Rare": [], "Common": []}
        
        for item_name, item_data in current_items.items():
            tier = item_data.get('tier', 'Common')
            level_req = item_data.get('level_req', 1)
            
            # Check level requirement
            if self.hunter_level >= level_req:
                tier_groups[tier].append((item_name, item_data))
        
        # Display items by tier
        tier_emojis = {"UR": "🟡", "SR": "🟣", "Rare": "🔵", "Common": "⚪"}
        
        for tier in ["UR", "SR", "Rare", "Common"]:
            items = tier_groups[tier]
            if items:
                items_text = ""
                for item_name, item_data in items[:5]:  # Limit to 5 items per tier
                    price = item_data.get('value', 0)
                    can_afford = "✅" if self.hunter_gold >= price else "❌"
                    
                    # Build stats display
                    stats = []
                    if 'attack' in item_data:
                        stats.append(f"ATK: {item_data['attack']}")
                    if 'defense' in item_data:
                        stats.append(f"DEF: {item_data['defense']}")
                    if 'heal_amount' in item_data:
                        stats.append(f"Heal: {item_data['heal_amount']}")
                    
                    stats_text = f" | {' • '.join(stats)}" if stats else ""
                    items_text += f"{can_afford} **{item_name}** - {price:,} gold{stats_text}\n"
                
                if items_text:
                    embed.add_field(
                        name=f"{tier_emojis[tier]} {tier} Tier",
                        value=items_text[:1024],
                        inline=False
                    )
        
        # Add item selection dropdown if items exist
        if any(tier_groups.values()):
            self.clear_items()
            self.add_item(CategorySelect(self))
            self.add_item(ItemSelect(self, tier_groups))
        
        embed.set_footer(text="Select a category above, then choose an item to purchase")
        return embed

class CategorySelect(Select):
    """Dropdown for selecting shop categories"""
    
    def __init__(self, shop_view):
        self.shop_view = shop_view
        
        options = [
            discord.SelectOption(label="Basic Equipment", value="basic_items", emoji="⚔️"),
            discord.SelectOption(label="Consumables", value="consumables", emoji="🧪"),
            discord.SelectOption(label="Materials", value="materials", emoji="🔨"),
            discord.SelectOption(label="Legendary Weapons", value="weapons", emoji="🗡️"),
            discord.SelectOption(label="Legendary Armor", value="armor", emoji="🛡️"),
            discord.SelectOption(label="Accessories", value="accessories", emoji="💍")
        ]
        
        super().__init__(placeholder="Select a category...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.shop_view.user_id):
            await interaction.response.send_message("You can't use this shop!", ephemeral=True)
            return
        
        self.shop_view.current_category = self.values[0]
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(interaction.user.id)
        
        embed = self.shop_view.get_shop_embed(colors)
        await interaction.response.edit_message(embed=embed, view=self.shop_view)

class ItemSelect(Select):
    """Dropdown for selecting items to purchase"""
    
    def __init__(self, shop_view, tier_groups):
        self.shop_view = shop_view
        
        options = []
        for tier in ["UR", "SR", "Rare", "Common"]:
            items = tier_groups[tier]
            for item_name, item_data in items[:10]:  # Limit options
                price = item_data.get('value', 0)
                can_afford = "✅" if shop_view.hunter_gold >= price else "❌"
                
                options.append(discord.SelectOption(
                    label=f"{item_name} - {price:,} gold",
                    value=item_name,
                    description=item_data.get('description', 'No description')[:100],
                    emoji=can_afford
                ))
        
        if not options:
            options.append(discord.SelectOption(label="No items available", value="none"))
        
        super().__init__(placeholder="Select an item to purchase...", options=options[:25])
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.shop_view.user_id):
            await interaction.response.send_message("You can't use this shop!", ephemeral=True)
            return
        
        item_name = self.values[0]
        if item_name == "none":
            await interaction.response.send_message("No items available for purchase!", ephemeral=True)
            return
        
        # Process purchase
        await self.process_purchase(interaction, item_name)

    async def process_purchase(self, interaction, item_name):
        """Process item purchase"""
        # Load fresh hunter data
        hunters_data = {}
        try:
            with open('hunters_data.json', 'r') as f:
                hunters_data = json.load(f)
        except FileNotFoundError:
            hunters_data = {}
        
        user_id = str(interaction.user.id)
        if user_id not in hunters_data:
            await interaction.response.send_message("Hunter data not found!", ephemeral=True)
            return
        
        hunter = hunters_data[user_id]
        current_gold = hunter.get('gold', 0)
        
        # Find item in current category
        current_items = self.shop_view.items_data.get(self.shop_view.current_category, {})
        if item_name not in current_items:
            await interaction.response.send_message("Item not found!", ephemeral=True)
            return
        
        item_data = current_items[item_name]
        price = item_data.get('value', 0)
        
        # Check affordability
        if current_gold < price:
            await interaction.response.send_message(
                f"You don't have enough gold! Need {price:,} but have {current_gold:,}",
                ephemeral=True
            )
            return
        
        # Check level requirement
        level_req = item_data.get('level_req', 1)
        if hunter.get('level', 1) < level_req:
            await interaction.response.send_message(
                f"You need to be level {level_req} to buy this item!",
                ephemeral=True
            )
            return
        
        # Process purchase
        hunter['gold'] -= price
        
        # Add to inventory
        if 'inventory' not in hunter:
            hunter['inventory'] = {}
        
        if item_data.get('stackable', False):
            hunter['inventory'][item_name] = hunter['inventory'].get(item_name, 0) + 1
        else:
            # For non-stackable items, create unique keys if needed
            base_name = item_name
            counter = 1
            unique_name = base_name
            while unique_name in hunter['inventory']:
                unique_name = f"{base_name}_{counter}"
                counter += 1
            hunter['inventory'][unique_name] = item_data
        
        # Save data
        try:
            with open('hunters_data.json', 'w') as f:
                json.dump(hunters_data, f, indent=4)
        except Exception as e:
            await interaction.response.send_message(f"Error saving purchase: {e}", ephemeral=True)
            return
        
        # Update shop view
        self.shop_view.hunter_gold = hunter['gold']
        
        # Success message
        tier_emoji = {"UR": "🟡", "SR": "🟣", "Rare": "🔵", "Common": "⚪"}.get(item_data.get('tier', 'Common'), "⚪")
        
        embed = discord.Embed(
            title="✅ Purchase Successful!",
            description=f"You bought **{item_name}** for {price:,} gold",
            color=discord.Color.green()
        )
        embed.add_field(name="Remaining Gold", value=f"{hunter['gold']:,} 💰", inline=True)
        embed.add_field(name="Item Tier", value=f"{tier_emoji} {item_data.get('tier', 'Common')}", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Update main shop display
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(interaction.user.id)
        shop_embed = self.shop_view.get_shop_embed(colors)
        await interaction.edit_original_response(embed=shop_embed, view=self.shop_view)

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.items_data = self.load_items_data()
    
    def load_items_data(self):
        """Load comprehensive items configuration including Solo Leveling and traditional RPG items"""
        return {
            # Traditional RPG Items for early game progression
            "basic_items": {
                "wooden_sword": {
                    "id": "wooden_sword", "name": "Wooden Sword", "type": "weapon", "tier": "Common", "value": 50,
                    "attack": 5, "description": "A basic, sturdy wooden sword. Good for beginners.",
                    "level_req": 1, "stackable": False, "equippable": True
                },
                "rusty_dagger": {
                    "id": "rusty_dagger", "name": "Rusty Dagger", "type": "weapon", "tier": "Common", "value": 30,
                    "attack": 3, "description": "A dull, rusty dagger. Not very effective.",
                    "level_req": 1, "stackable": False, "equippable": True
                },
                "leather_armor": {
                    "id": "leather_armor", "name": "Leather Armor", "type": "armor", "tier": "Common", "value": 75,
                    "defense": 5, "description": "Light leather protection.",
                    "level_req": 1, "stackable": False, "equippable": True
                },
                "bronze_sword": {
                    "id": "bronze_sword", "name": "Bronze Sword", "type": "weapon", "tier": "Common", "value": 150,
                    "attack": 12, "defense": 2, "description": "A well-balanced sword made of bronze.",
                    "level_req": 5, "stackable": False, "equippable": True
                },
                "hunter_bow": {
                    "id": "hunter_bow", "name": "Hunter's Bow", "type": "weapon", "tier": "Common", "value": 120,
                    "attack": 10, "description": "A simple bow for ranged combat.",
                    "level_req": 3, "stackable": False, "equippable": True
                },
                "steel_axe": {
                    "id": "steel_axe", "name": "Steel Axe", "type": "weapon", "tier": "Rare", "value": 200,
                    "attack": 15, "description": "A heavy axe that delivers powerful blows.",
                    "level_req": 8, "stackable": False, "equippable": True
                },
                "iron_plate_armor": {
                    "id": "iron_plate_armor", "name": "Iron Plate Armor", "type": "armor", "tier": "Rare", "value": 300,
                    "defense": 15, "description": "Heavy iron plates for superior defense.",
                    "level_req": 10, "stackable": False, "equippable": True
                },
                "cloth_robe": {
                    "id": "cloth_robe", "name": "Cloth Robe", "type": "armor", "tier": "Common", "value": 40,
                    "defense": 2, "description": "Lightweight robe, offers minimal protection.",
                    "level_req": 1, "stackable": False, "equippable": True
                },
                "wooden_shield": {
                    "id": "wooden_shield", "name": "Wooden Shield", "type": "shield", "tier": "Common", "value": 80,
                    "defense": 7, "description": "A sturdy shield for blocking attacks.",
                    "level_req": 2, "stackable": False, "equippable": True
                }
            },
            "consumables": {
                "healing_potion": {
                    "id": "healing_potion", "name": "Healing Potion", "type": "consumable", "tier": "Common", "value": 20,
                    "heal_amount": 30, "description": "Restores 30 HP.",
                    "level_req": 1, "stackable": True, "equippable": False
                },
                "super_healing_potion": {
                    "id": "super_healing_potion", "name": "Super Healing Potion", "type": "consumable", "tier": "Rare", "value": 60,
                    "heal_amount": 75, "description": "Restores 75 HP.",
                    "level_req": 5, "stackable": True, "equippable": False
                },
                "mana_potion": {
                    "id": "mana_potion", "name": "Mana Potion", "type": "consumable", "tier": "Common", "value": 40,
                    "mana_amount": 50, "description": "Restores 50 Mana.",
                    "level_req": 1, "stackable": True, "equippable": False
                },
                "strength_elixir": {
                    "id": "strength_elixir", "name": "Strength Elixir", "type": "consumable", "tier": "Rare", "value": 100,
                    "boost_type": "attack", "boost_amount": 10, "duration": 3,
                    "description": "Temporarily boosts attack by 10 for 3 turns.",
                    "level_req": 8, "stackable": True, "equippable": False
                }
            },
            "materials": {
                "iron_ore": {
                    "id": "iron_ore", "name": "Iron Ore", "type": "material", "tier": "Common", "value": 15,
                    "description": "Raw ore, can be crafted into weapons and armor.",
                    "level_req": 1, "stackable": True, "equippable": False
                },
                "silver_ore": {
                    "id": "silver_ore", "name": "Silver Ore", "type": "material", "tier": "Rare", "value": 50,
                    "description": "A shiny, valuable ore used in advanced crafting.",
                    "level_req": 5, "stackable": True, "equippable": False
                },
                "monster_fang": {
                    "id": "monster_fang", "name": "Monster Fang", "type": "material", "tier": "Rare", "value": 30,
                    "description": "Sharp fang from a defeated beast. Used in weapon crafting.",
                    "level_req": 3, "stackable": True, "equippable": False
                },
                "mystic_dust": {
                    "id": "mystic_dust", "name": "Mystic Dust", "type": "material", "tier": "SR", "value": 200,
                    "description": "A rare dust with magical properties for enchanting.",
                    "level_req": 15, "stackable": True, "equippable": False
                }
            },
            "weapons": {
                # Ultra Rare (UR) - Legendary Weapons
                "Kamish's Wrath": {
                    "type": "weapon", "element": "Fire", "tier": "UR", "value": 12000,
                    "attack": random.randint(1800, 2000), "critical_rate": 15, "fire_damage": 20,
                    "skill": "Dragon's Flame", "skill_desc": "AoE fire burst dealing massive damage",
                    "description": "Forged from the fang of Kamish, the Western Dragon. Ignites the wielder's blade with fierce flames."
                },
                "Orb of Avarice": {
                    "type": "weapon", "element": "Magic", "tier": "UR", "value": 15000,
                    "magic_power": 50, "mana_regen": 10, "attack": random.randint(1600, 1800),
                    "skill": "Dark Pulse", "skill_desc": "AoE magic damage that drains enemy mana",
                    "description": "A mysterious orb that once belonged to a Demon Ruler. Increases magical power and mana regeneration."
                },
                
                # Super Rare (SR) - Boss Drops
                "Baruka's Dagger": {
                    "type": "weapon", "element": "Wind", "tier": "SR", "value": 6500,
                    "attack": random.randint(1500, 1700), "hp_boost": 2000, "precision": 1500,
                    "skill": "Slayer of Ice Slayers", "skill_desc": "Teleport behind enemy + Wind slash",
                    "description": "A legendary dagger wielded by Baruka, the Ice Elf Lord. Infused with wind magic that grants swift and deadly strikes."
                },
                "Giant's Sword": {
                    "type": "weapon", "element": "Physical", "tier": "SR", "value": 8000,
                    "attack": random.randint(2500, 3000), "defense_penetration": 10,
                    "skill": "Heavy Swing", "skill_desc": "Massive single-target damage",
                    "description": "A colossal sword carried by the Giants of Tokyo's S-Rank Gate. Known for its immense power and durability."
                },
                "Igris's Shadow Sword": {
                    "type": "weapon", "element": "Light", "tier": "SR", "value": 7500,
                    "attack": 2200, "light_damage": 25,
                    "skill": "Holy Slash", "skill_desc": "Single-target light burst that harms undead",
                    "description": "The holy sword wielded by Igris, Jinwoo's shadow knight. Radiates light energy that harms dark forces."
                },
                "Iron's Mace": {
                    "type": "weapon", "element": "Physical", "tier": "SR", "value": 7000,
                    "attack": 2000, "stun_chance": 20, "defense": 15,
                    "skill": "Crushing Blow", "skill_desc": "Heavy attack with high stun chance",
                    "description": "The massive mace wielded by Iron, one of Jinwoo's shadow soldiers. Crushing blows that stun enemies."
                },
                "Blood Sword": {
                    "type": "weapon", "element": "Dark", "tier": "SR", "value": 6000,
                    "attack": 1900, "life_steal": 15, "poison_damage": 10,
                    "skill": "Venom Strike", "skill_desc": "Poison damage over time + life steal",
                    "description": "A cursed sword dripping with poison. Drains life from enemies and weakens their defenses."
                },
                "Earthbreaker Hammer": {
                    "type": "weapon", "element": "Earth", "tier": "SR", "value": 8500,
                    "attack": 2700, "stun_chance": 25,
                    "skill": "Earthquake", "skill_desc": "AoE stun and damage",
                    "description": "A heavy hammer that shakes the earth on impact. Slow but devastating."
                },
                "Shadow Bow": {
                    "type": "weapon", "element": "Shadow", "tier": "SR", "value": 7000,
                    "attack": 1600, "piercing": 30,
                    "skill": "Shadow Volley", "skill_desc": "Fires multiple arrows in a spread",
                    "description": "A bow made from shadow essence. Arrows can pierce through multiple enemies."
                },
                
                # Rare - Quality Weapons
                "Hunter's Bow": {
                    "type": "weapon", "element": "Physical", "tier": "Rare", "value": 1500,
                    "attack": 1400, "range": 30, "precision": 25,
                    "skill": "Piercing Arrow", "skill_desc": "Ignores enemy defense",
                    "description": "A standard bow used by skilled hunters for long-range combat. Fast firing with high precision."
                },
                "Shadow Dagger": {
                    "type": "weapon", "element": "Shadow", "tier": "Rare", "value": 2000,
                    "attack": 1300,
                    "skill": "Shadow Step", "skill_desc": "Temporary invisibility and critical damage boost",
                    "description": "A dagger imbued with shadow energy, used by Jinwoo's assassins. Grants invisibility for a short duration."
                },
                "Dagger of the Wind": {
                    "type": "weapon", "element": "Wind", "tier": "Rare", "value": 2500,
                    "attack": 1200, "evasion": 15, "attack_speed": 20,
                    "skill": "Wind Dash", "skill_desc": "Quick reposition and attack",
                    "description": "A lightweight dagger blessed by wind spirits. Enables quick strikes and dodges."
                }
            },
            "shields": {
                "Tank's Shield": {
                    "type": "shield", "tier": "SR", "value": 5000,
                    "defense": 2500, "block_rate": 35,
                    "skill": "Iron Wall", "skill_desc": "Reduces damage taken by 40% for 5 seconds",
                    "description": "Shield wielded by Tank, the shadow extracted from Ice Bear Alpha. Provides exceptional defense."
                }
            },
            "accessories": {
                "Goblin's Eye": {
                    "type": "accessory", "tier": "Rare", "value": 1000,
                    "crit_rate": 10, "perception": 15, "dodge_chance": 5,
                    "description": "A mystical eye extracted from a Goblin Boss, enhancing perception and critical hit capabilities."
                },
                "Aqua Ring": {
                    "type": "accessory", "element": "Water", "tier": "Rare", "value": 1200,
                    "heal_power": 10, "mana_regen": 5, "water_resistance": 20,
                    "description": "A ring imbued with the power of water. Enhances healing and mana regeneration."
                }
            },
            "consumables": {
                "Kamish's Rune Stone": {
                    "type": "consumable", "tier": "Rare", "value": 1500,
                    "effect": "fire_buff", "duration": 600, "fire_damage_boost": 20, "crit_boost": 10,
                    "description": "A rune stone crafted from the essence of Kamish's scales. Grants temporary fire damage and critical hit boost."
                },
                "Health Potion": {
                    "type": "consumable", "tier": "Common", "value": 50,
                    "effect": "heal", "heal_amount": 100,
                    "description": "A basic healing potion that restores health."
                },
                "Mana Potion": {
                    "type": "consumable", "tier": "Common", "value": 30,
                    "effect": "mana", "mana_amount": 50,
                    "description": "A basic mana potion that restores magical energy."
                }
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
    
    def get_tier_color_and_emoji(self, tier):
        """Get Discord color and emoji based on Solo Leveling tier"""
        tier_info = {
            "Common": {"color": discord.Color.light_grey(), "emoji": "⚪"},
            "Rare": {"color": discord.Color.blue(), "emoji": "🔵"},
            "SR": {"color": discord.Color.purple(), "emoji": "🟣"},
            "UR": {"color": discord.Color.gold(), "emoji": "🟡"}
        }
        return tier_info.get(tier, {"color": discord.Color.default(), "emoji": "⚪"})
    
    def generate_shop_inventory(self, hunter_level):
        """Generate shop inventory based on hunter level with tier requirements"""
        shop_items = []
        
        # Add items based on hunter level with Solo Leveling tier requirements
        for category, items in self.items_data.items():
            for item_name, item_data in items.items():
                # Tier-based level requirements matching Solo Leveling progression
                item_level_req = {
                    "Common": 1,
                    "Rare": 10,
                    "SR": 25,
                    "UR": 50
                }.get(item_data.get('tier', 'Common'), 1)
                
                if hunter_level >= item_level_req:
                    shop_items.append((item_name, item_data, category))
        
        # Sort by tier for better display (UR first, then SR, Rare, Common)
        tier_order = {"UR": 0, "SR": 1, "Rare": 2, "Common": 3}
        shop_items.sort(key=lambda x: tier_order.get(x[1].get('tier', 'Common'), 3))
        
        return shop_items
    
    @commands.command(name='shop')
    async def show_shop(self, ctx):
        """Display the interactive hunter shop"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        
        if user_id not in hunters_data:
            embed = discord.Embed(
                title="❌ Error",
                description="You need to start your journey first! Use `.start`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        hunter = hunters_data[user_id]
        hunter_level = hunter.get('level', 1)
        hunter_gold = hunter.get('gold', 0)
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        # Create interactive shop view
        view = ShopView(self.bot, user_id, hunter_level, hunter_gold, self.items_data)
        embed = view.get_shop_embed(colors)
        
        message = await ctx.send(embed=embed, view=view)
        view.message = message
    
    @commands.command(name='buy')
    async def buy_item(self, ctx, *, item_name):
        """Buy an item from the shop"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        
        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use `.start`")
            return
        
        hunter = hunters_data[user_id]
        hunter_gold = hunter.get('gold', 0)
        
        # Find the item in shop inventory
        shop_inventory = self.generate_shop_inventory(hunter['level'])
        item_found = None
        item_data = None
        
        for shop_item_name, shop_item_data in shop_inventory:
            if shop_item_name.lower() == item_name.lower():
                item_found = shop_item_name
                item_data = shop_item_data
                break
        
        if not item_found or not item_data:
            await ctx.send(f"'{item_name}' is not available in the shop!")
            return
        
        # At this point item_data is guaranteed to be not None
        item_price = item_data.get('value', 0)
        
        # Check if hunter has enough gold
        if hunter_gold < item_price:
            await ctx.send(f"You don't have enough gold! You need {item_price} gold but only have {hunter_gold}.")
            return
        
        # Purchase the item
        hunter['gold'] -= item_price
        
        # Add item to inventory with validation
        if 'inventory' not in hunter:
            hunter['inventory'] = {}
        
        # Add the item to inventory (new structure)
        if isinstance(hunter['inventory'], list):
            # Convert old list format to new dict format
            old_items = hunter['inventory']
            hunter['inventory'] = {}
            for item in old_items:
                hunter['inventory'][item] = hunter['inventory'].get(item, 0) + 1
        
        # Add the purchased item
        hunter['inventory'][item_found] = hunter['inventory'].get(item_found, 0) + 1
        
        # Update quest progress for item purchase
        try:
            from daily_quest_system import update_quest_progress
            update_quest_progress(hunter, "buy_items", 1)
        except:
            pass
        
        # Save data
        self.save_hunters_data(hunters_data)
        
        embed = discord.Embed(
            title="🛒 Purchase Successful!",
            description=f"You bought **{item_found}** for {item_price} gold!",
            color=self.get_rarity_color(item_data.get('rarity', 'Common'))
        )
        
        embed.add_field(
            name="Transaction",
            value=f"💰 Gold Spent: {item_price}\n💰 Remaining Gold: {hunter['gold']}",
            inline=False
        )
        
        # Show item stats - item_data is guaranteed to exist here
        stats_text = ""
        if item_data:  # Additional safety check for LSP
            for stat, value in item_data.items():
                if stat not in ['type', 'value', 'rarity', 'effect', 'description', 'heal_amount', 'mana_amount', 'exp_amount', 'boost_type', 'boost_amount', 'duration']:
                    stats_text += f"{stat.title()}: +{value}\n"
        
        if stats_text:
            embed.add_field(name="Item Stats", value=stats_text, inline=True)
        
        embed.set_footer(text="Use `.inventory` to see your items • `.equip <item>` to equip items")
        await ctx.send(embed=embed)
    
    @commands.command(name='sell')
    async def sell_item(self, ctx, *, item_name):
        """Sell an item from inventory for half its original price"""
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
        
        # Find item in inventory (case insensitive)
        item_found = None
        for item in inventory.keys():
            if item.lower() == item_name.lower():
                item_found = item
                break
        
        if not item_found or inventory.get(item_found, 0) <= 0:
            await ctx.send(f"You don't have '{item_name}' in your inventory!")
            return
        
        # Get item data to determine sell price from inventory system
        inventory_cog = self.bot.get_cog('Inventory')
        item_data = None
        
        if inventory_cog:
            item_data = inventory_cog.get_item_info(item_found)
        
        if not item_data:
            # Try to get from local shop data as fallback
            for category, items in self.items_data.items():
                if item_found in items:
                    item_data = items[item_found]
                    break
        
        if not item_data:
            await ctx.send("Item data not found!")
            return
        
        # Calculate sell price (50% of original value, minimum 1 gold)
        original_price = item_data.get('value', 10)
        sell_price = max(1, original_price // 2)
        
        # Remove one item from inventory and add gold
        inventory[item_found] -= 1
        if inventory[item_found] <= 0:
            del inventory[item_found]
        
        hunter['gold'] = hunter.get('gold', 0) + sell_price
        
        self.save_hunters_data(hunters_data)
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        embed = discord.Embed(
            title="💸 Item Sold!",
            description=f"You sold **{item_found}** for {sell_price} gold!",
            color=discord.Color(colors['success'])
        )
        
        embed.add_field(
            name="💰 Transaction Details",
            value=f"Original Price: {original_price} gold\nSell Price: {sell_price} gold (50%)\nTotal Gold: {hunter['gold']} gold",
            inline=False
        )
        
        # Show item rarity and remaining quantity
        rarity = item_data.get('rarity', 'Common')
        remaining = inventory.get(item_found, 0)
        embed.add_field(
            name="📊 Item Info",
            value=f"Rarity: {rarity}\nRemaining in inventory: {remaining}",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Shop(bot))
