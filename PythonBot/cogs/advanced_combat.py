import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import json
import random
from utils.ability_utils import (
    initialize_hunter_abilities, 
    get_ability_data, 
    apply_ability_effect,
    is_ability_on_cooldown,
    get_remaining_cooldown,
    process_turn_effects,
    get_effective_stats,
    get_hunter_abilities_by_level
)
from utils.boss_dialogue import (
    get_boss_dialogue,
    format_boss_encounter_text,
    get_boss_status_effects,
    should_trigger_dialogue,
    get_contextual_boss_response
)

class AdvancedCombat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_combats = {}  # Track active combat sessions
    
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
    
    def load_gates_data(self):
        """Load gates data from JSON file"""
        try:
            with open('data/gates.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def load_dungeons_data(self):
        """Load dungeons data from JSON file"""
        try:
            with open('data/dungeons.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def load_monster_data(self):
        """Load monster data from JSON file"""
        try:
            with open('data/monsters.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    @commands.command(name='abilities')
    async def show_abilities(self, ctx):
        """Display hunter's abilities and their status"""
        user_id = str(ctx.author.id)
        hunters_data = self.load_hunters_data()
        
        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use `.start`")
            return
        
        hunter = hunters_data[user_id]
        initialize_hunter_abilities(hunter)
        
        # Update abilities based on level
        current_level = hunter.get('level', 1)
        available_abilities = get_hunter_abilities_by_level(current_level)
        hunter['abilities'] = available_abilities
        
        self.save_hunters_data(hunters_data)
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        embed = discord.Embed(
            title="⚔️ Combat Abilities",
            description=f"**Mana:** {hunter.get('mana', 0)}/{hunter.get('max_mana', 100)}",
            color=discord.Color(colors['accent'])
        )
        
        abilities_text = ""
        for ability_id in hunter.get('abilities', []):
            ability_data = get_ability_data(ability_id)
            if ability_data:
                cooldown_status = ""
                if is_ability_on_cooldown(hunter, ability_id):
                    remaining = get_remaining_cooldown(hunter, ability_id)
                    cooldown_status = f" (Cooldown: {remaining})"
                
                mana_cost = ability_data.get('mana_cost', 0)
                abilities_text += f"**{ability_data['name']}** - {mana_cost} MP{cooldown_status}\n"
                abilities_text += f"*{ability_data['description']}*\n\n"
        
        if not abilities_text:
            abilities_text = "No abilities learned yet."
        
        embed.add_field(name="Your Abilities", value=abilities_text, inline=False)
        embed.set_footer(text="Use abilities during combat with the interactive buttons")
        
        await ctx.send(embed=embed)
    
    @commands.command(name='gates')
    async def show_gates(self, ctx):
        """Display available gates with interactive UI"""
        user_id = str(ctx.author.id)
        hunters_data = self.load_hunters_data()
        
        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use `.start`")
            return
        
        hunter = hunters_data[user_id]
        gates_data = self.load_gates_data()
        
        if not gates_data:
            await ctx.send("No gates are currently available.")
            return
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        embed = discord.Embed(
            title="🌀 Available Gates",
            description="Select a gate to explore. Each gate contains unique monsters and rewards.",
            color=discord.Color(colors['primary'])
        )
        
        view = GateSelectionView(ctx, hunter, gates_data, self)
        message = await ctx.send(embed=embed, view=view)
        view.message = message
    
    @commands.command(name='dungeons')
    async def show_dungeons(self, ctx):
        """Display available dungeons with interactive UI"""
        user_id = str(ctx.author.id)
        hunters_data = self.load_hunters_data()
        
        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use `.start`")
            return
        
        hunter = hunters_data[user_id]
        dungeons_data = self.load_dungeons_data()
        
        if not dungeons_data:
            await ctx.send("No dungeons are currently available.")
            return
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        embed = discord.Embed(
            title="🏰 Available Dungeons",
            description="Multi-floor dungeons with increasing difficulty and greater rewards.",
            color=discord.Color(colors['primary'])
        )
        
        view = DungeonSelectionView(ctx, hunter, dungeons_data, self)
        message = await ctx.send(embed=embed, view=view)
        view.message = message
    
    async def start_gate_exploration(self, ctx, gate_id, hunter):
        """Start exploring a gate"""
        gates_data = self.load_gates_data()
        gate = gates_data.get(gate_id)
        
        if not gate:
            await ctx.send("Gate not found!")
            return
        
        # Check level requirement
        required_level = gate.get('required_level', 1)
        if hunter.get('level', 1) < required_level:
            await ctx.send(f"You need to be level {required_level} to enter this gate!")
            return
        
        # Select random monster from gate's monster pool
        monster_pool = gate.get('monster_pool', [])
        if not monster_pool:
            await ctx.send("No monsters found in this gate!")
            return
        
        monster_name = random.choice(monster_pool)
        monster_data = self.load_monster_data()
        
        # Find monster in the data
        selected_monster = None
        for monster_key, monster_info in monster_data.items():
            if monster_info.get('name', '').lower() == monster_name.lower():
                selected_monster = monster_info.copy()
                break
        
        if not selected_monster:
            await ctx.send(f"Monster '{monster_name}' not found in database!")
            return
        
        # Initialize combat
        await self.start_advanced_combat(ctx, hunter, selected_monster, combat_type="gate", location_data=gate)
    
    async def start_advanced_combat(self, ctx, hunter, monster, combat_type="hunt", location_data=None):
        """Start advanced combat with abilities and boss dialogue"""
        user_id = str(ctx.author.id)
        
        # Initialize hunter abilities
        initialize_hunter_abilities(hunter)
        
        # Check if this is a boss encounter
        is_boss = monster.get('boss', False)
        monster_name = monster.get('name', 'Monster')
        
        # Create combat view with abilities
        combat_view = AdvancedCombatView(self.bot, ctx, user_id, monster.copy(), combat_type, location_data, self)
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        # Create enhanced embed with boss dialogue
        embed_title = f"⚔️ Combat: {hunter.get('name', 'Hunter')} vs {monster_name}"
        if is_boss:
            embed_title = f"💀 BOSS ENCOUNTER: {monster_name}"
        
        embed = discord.Embed(
            title=embed_title,
            color=discord.Color(colors['accent'] if not is_boss else colors['error'])
        )
        
        # Add boss encounter dialogue
        description_text = monster.get('description', f'A powerful {monster_name}')
        if is_boss:
            boss_dialogue = format_boss_encounter_text(monster_name, "encounter")
            description_text += boss_dialogue
        
        embed.description = description_text
        
        # Add combat info
        embed.add_field(
            name="🛡️ Your Status",
            value=f"HP: {hunter.get('hp', 100)}/{hunter.get('max_hp', 100)}\nMP: {hunter.get('mana', 100)}/{hunter.get('max_mana', 100)}",
            inline=True
        )
        
        # Enhanced enemy status for bosses
        enemy_status = f"HP: {monster.get('hp', 50)}/{monster.get('hp', 50)}\nATK: {monster.get('attack', 10)}"
        if is_boss:
            weaknesses = monster.get('weaknesses', [])
            if weaknesses:
                enemy_status += f"\n**Weak to:** {', '.join(weaknesses[:2])}"
        
        embed.add_field(
            name="👹 Enemy Status" if not is_boss else "💀 Boss Status", 
            value=enemy_status,
            inline=True
        )
        
        if location_data:
            embed.add_field(
                name="📍 Location",
                value=f"{location_data.get('name', 'Unknown')} ({location_data.get('difficulty', 'Unknown')})",
                inline=False
            )
        
        # Add boss status effects if any
        if is_boss:
            status_effects = get_boss_status_effects(monster_name, monster.get('hp', 50), monster.get('hp', 50))
            if status_effects:
                embed.add_field(
                    name="🔥 Boss Effects",
                    value="\n".join(status_effects),
                    inline=False
                )
        
        embed.set_footer(text="Use the buttons below to choose your combat action")
        
        # Send to private combat channel if available
        combat_channels = getattr(self.bot, 'combat_channels', {})
        target_channel = combat_channels.get(user_id, ctx.channel)
        
        message = await target_channel.send(embed=embed, view=combat_view)
        combat_view.message = message
        
        # Store combat session with boss info
        self.active_combats[user_id] = {
            'hunter': hunter,
            'monster': monster,
            'combat_type': combat_type,
            'location_data': location_data,
            'view': combat_view,
            'is_boss': is_boss,
            'last_dialogue_hp': monster.get('hp', 50),
            'original_hp': monster.get('hp', 50)
        }

class GateSelectionView(View):
    """Interactive view for selecting gates"""
    
    def __init__(self, ctx, hunter, gates_data, combat_cog):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.hunter = hunter
        self.gates_data = gates_data
        self.combat_cog = combat_cog
        self.message = None
        self.selected_gate = None
        
        # Add gate selection dropdown
        self.add_item(GateSelectDropdown(self))
        
        # Add action buttons (initially disabled)
        self.view_details_btn = Button(label="📋 View Details", style=discord.ButtonStyle.secondary, disabled=True)
        self.view_details_btn.callback = self.view_details_callback
        self.add_item(self.view_details_btn)
        
        self.enter_gate_btn = Button(label="🚪 Enter Gate", style=discord.ButtonStyle.success, disabled=True)
        self.enter_gate_btn.callback = self.enter_gate_callback
        self.add_item(self.enter_gate_btn)
    
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
        """Update button states based on selection"""
        enabled = self.selected_gate is not None
        self.view_details_btn.disabled = not enabled
        self.enter_gate_btn.disabled = not enabled
    
    async def view_details_callback(self, interaction):
        """Show detailed information about the selected gate"""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the command user can interact with this!", ephemeral=True)
            return
        
        if not self.selected_gate:
            await interaction.response.send_message("Please select a gate first!", ephemeral=True)
            return
        
        gate = self.gates_data[self.selected_gate]
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(self.ctx.author.id)
        
        embed = discord.Embed(
            title=f"🌀 {gate['name']}",
            description=gate['description'],
            color=discord.Color(colors['secondary'])
        )
        
        embed.add_field(name="Difficulty", value=gate['difficulty'], inline=True)
        embed.add_field(name="Required Level", value=gate['required_level'], inline=True)
        embed.add_field(name="Floors", value=gate['floors'], inline=True)
        
        monsters_text = ", ".join(gate['monster_pool'])
        embed.add_field(name="Monsters", value=monsters_text, inline=False)
        
        boss_text = gate.get('boss_id', 'Unknown')
        embed.add_field(name="Boss", value=boss_text, inline=False)
        
        rewards = gate['rewards']
        rewards_text = f"EXP: {rewards['exp']}\nGold: {rewards['gold']}"
        if rewards.get('items'):
            rewards_text += "\nPossible Items:"
            for item in rewards['items']:
                chance_percent = int(item['chance'] * 100)
                rewards_text += f"\n• {item['name']} ({chance_percent}%)"
        
        embed.add_field(name="Rewards", value=rewards_text, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def enter_gate_callback(self, interaction):
        """Enter the selected gate"""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the command user can interact with this!", ephemeral=True)
            return
        
        if not self.selected_gate:
            await interaction.response.send_message("Please select a gate first!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Start gate exploration
        await self.combat_cog.start_gate_exploration(self.ctx, self.selected_gate, self.hunter)
        
        # Disable view
        for item in self.children:
            item.disabled = True
        
        try:
            await self.message.edit(view=self)
        except:
            pass

class GateSelectDropdown(Select):
    """Dropdown for selecting gates"""
    
    def __init__(self, gate_view):
        self.gate_view = gate_view
        
        options = []
        for gate_id, gate_data in gate_view.gates_data.items():
            # Check if hunter meets level requirement
            required_level = gate_data.get('required_level', 1)
            hunter_level = gate_view.hunter.get('level', 1)
            
            if hunter_level >= required_level:
                difficulty_emoji = {
                    'D': '🟢', 'C': '🔵', 'B': '🟡', 
                    'A': '🟠', 'S': '🔴', 'National': '⚫'
                }.get(gate_data.get('difficulty'), '⚪')
                
                options.append(discord.SelectOption(
                    label=gate_data['name'][:25],
                    description=f"{gate_data['difficulty']}-Rank • Level {required_level}+"[:50],
                    emoji=difficulty_emoji,
                    value=gate_id
                ))
        
        if not options:
            options.append(discord.SelectOption(
                label="No accessible gates",
                description="Level up to access more gates",
                emoji="🚫",
                value="none"
            ))
        
        super().__init__(placeholder="Select a gate to explore...", options=options[:25], min_values=0, max_values=1)
    
    async def callback(self, interaction):
        """Handle gate selection"""
        if interaction.user.id != self.gate_view.ctx.author.id:
            await interaction.response.send_message("Only the command user can interact with this!", ephemeral=True)
            return
        
        if self.values[0] == "none":
            await interaction.response.send_message("No gates available at your level!", ephemeral=True)
            return
        
        self.gate_view.selected_gate = self.values[0]
        self.gate_view.update_buttons()
        
        await interaction.response.edit_message(view=self.gate_view)

class DungeonSelectionView(View):
    """Interactive view for selecting dungeons (similar to gates but for multi-floor content)"""
    
    def __init__(self, ctx, hunter, dungeons_data, combat_cog):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.hunter = hunter
        self.dungeons_data = dungeons_data
        self.combat_cog = combat_cog
        self.message = None
        self.selected_dungeon = None
        
        # Add dungeon selection dropdown
        self.add_item(DungeonSelectDropdown(self))
        
        # Add action buttons (initially disabled)
        self.view_details_btn = Button(label="📋 View Details", style=discord.ButtonStyle.secondary, disabled=True)
        self.view_details_btn.callback = self.view_details_callback
        self.add_item(self.view_details_btn)
        
        self.enter_dungeon_btn = Button(label="🏰 Enter Dungeon", style=discord.ButtonStyle.success, disabled=True)
        self.enter_dungeon_btn.callback = self.enter_dungeon_callback
        self.add_item(self.enter_dungeon_btn)
    
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
        """Update button states based on selection"""
        enabled = self.selected_dungeon is not None
        self.view_details_btn.disabled = not enabled
        self.enter_dungeon_btn.disabled = not enabled
    
    async def view_details_callback(self, interaction):
        """Show detailed information about the selected dungeon"""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the command user can interact with this!", ephemeral=True)
            return
        
        if not self.selected_dungeon:
            await interaction.response.send_message("Please select a dungeon first!", ephemeral=True)
            return
        
        dungeon = self.dungeons_data[self.selected_dungeon]
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(self.ctx.author.id)
        
        embed = discord.Embed(
            title=f"🏰 {dungeon['name']}",
            description=dungeon['description'],
            color=discord.Color(colors['secondary'])
        )
        
        embed.add_field(name="Difficulty", value=dungeon['difficulty'], inline=True)
        embed.add_field(name="Required Level", value=dungeon['required_level'], inline=True)
        embed.add_field(name="Floors", value=dungeon['floors'], inline=True)
        
        monsters_text = ", ".join(dungeon['monster_pool'])
        embed.add_field(name="Monsters", value=monsters_text, inline=False)
        
        boss_text = dungeon.get('boss_id', 'Unknown')
        embed.add_field(name="Final Boss", value=boss_text, inline=False)
        
        rewards = dungeon['rewards']
        rewards_text = f"EXP: {rewards['exp']}\nGold: {rewards['gold']}"
        if rewards.get('items'):
            rewards_text += "\nPossible Items:"
            for item in rewards['items']:
                chance_percent = int(item['chance'] * 100)
                rewards_text += f"\n• {item['name']} ({chance_percent}%)"
        
        embed.add_field(name="Completion Rewards", value=rewards_text, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def enter_dungeon_callback(self, interaction):
        """Enter the selected dungeon"""
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the command user can interact with this!", ephemeral=True)
            return
        
        if not self.selected_dungeon:
            await interaction.response.send_message("Please select a dungeon first!", ephemeral=True)
            return
        
        await interaction.response.send_message("🏰 Dungeon raids will be available in the next update! For now, try gates with `.gates`", ephemeral=True)

class DungeonSelectDropdown(Select):
    """Dropdown for selecting dungeons"""
    
    def __init__(self, dungeon_view):
        self.dungeon_view = dungeon_view
        
        options = []
        for dungeon_id, dungeon_data in dungeon_view.dungeons_data.items():
            # Check if hunter meets level requirement
            required_level = dungeon_data.get('required_level', 1)
            hunter_level = dungeon_view.hunter.get('level', 1)
            
            if hunter_level >= required_level:
                difficulty_emoji = {
                    'D': '🟢', 'C': '🔵', 'B': '🟡', 
                    'A': '🟠', 'S': '🔴', 'National': '⚫'
                }.get(dungeon_data.get('difficulty'), '⚪')
                
                floors = dungeon_data.get('floors', 1)
                options.append(discord.SelectOption(
                    label=dungeon_data['name'][:25],
                    description=f"{dungeon_data['difficulty']}-Rank • {floors} Floors • Level {required_level}+"[:50],
                    emoji=difficulty_emoji,
                    value=dungeon_id
                ))
        
        if not options:
            options.append(discord.SelectOption(
                label="No accessible dungeons",
                description="Level up to access more dungeons",
                emoji="🚫",
                value="none"
            ))
        
        super().__init__(placeholder="Select a dungeon to raid...", options=options[:25], min_values=0, max_values=1)
    
    async def callback(self, interaction):
        """Handle dungeon selection"""
        if interaction.user.id != self.dungeon_view.ctx.author.id:
            await interaction.response.send_message("Only the command user can interact with this!", ephemeral=True)
            return
        
        if self.values[0] == "none":
            await interaction.response.send_message("No dungeons available at your level!", ephemeral=True)
            return
        
        self.dungeon_view.selected_dungeon = self.values[0]
        self.dungeon_view.update_buttons()
        
        await interaction.response.edit_message(view=self.dungeon_view)

class AdvancedCombatView(View):
    """Enhanced combat view with abilities"""
    
    def __init__(self, bot, ctx, user_id, monster_data, combat_type="hunt", location_data=None, combat_cog=None):
        super().__init__(timeout=180)
        self.bot = bot
        self.ctx = ctx
        self.user_id = user_id
        self.monster_data = monster_data
        self.combat_type = combat_type
        self.location_data = location_data
        self.combat_cog = combat_cog
        self.message = None
        
        self.add_combat_buttons()
    
    def add_combat_buttons(self):
        """Add combat buttons including abilities"""
        self.clear_items()
        
        hunters_data = self.combat_cog.load_hunters_data()
        hunter = hunters_data.get(self.user_id, {})
        
        # Basic Attack button
        attack_btn = Button(label="⚔️ Attack", style=discord.ButtonStyle.primary)
        attack_btn.callback = self.attack_callback
        self.add_item(attack_btn)
        
        # Ability buttons
        abilities = hunter.get('abilities', [])
        for ability_id in abilities[:3]:  # Limit to 3 abilities to fit in one row
            ability_data = get_ability_data(ability_id)
            if ability_data:
                is_on_cooldown = is_ability_on_cooldown(hunter, ability_id)
                has_mana = hunter.get('mana', 0) >= ability_data['mana_cost']
                
                button_label = ability_data['name'][:20]  # Truncate for button
                if is_on_cooldown:
                    remaining = get_remaining_cooldown(hunter, ability_id)
                    button_label = f"{ability_data['name'][:15]} ({remaining})"
                elif not has_mana:
                    button_label = f"{ability_data['name'][:15]} (No MP)"
                
                ability_btn = Button(
                    label=button_label,
                    style=discord.ButtonStyle.secondary,
                    disabled=is_on_cooldown or not has_mana
                )
                ability_btn.callback = lambda interaction, aid=ability_id: self.ability_callback(interaction, aid)
                self.add_item(ability_btn)
        
        # Flee button
        flee_btn = Button(label="🏃 Flee", style=discord.ButtonStyle.danger)
        flee_btn.callback = self.flee_callback
        self.add_item(flee_btn)
    
    async def attack_callback(self, interaction):
        """Handle basic attack"""
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message("This isn't your battle!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        hunters_data = self.combat_cog.load_hunters_data()
        hunter = hunters_data.get(self.user_id, {})
        
        # Player attacks monster
        effective_stats = get_effective_stats(hunter)
        damage_dealt = max(1, effective_stats['strength'] - self.monster_data.get('defense', 0))
        self.monster_data['hp'] = max(0, self.monster_data.get('hp', 1) - damage_dealt)
        
        result_text = f"You dealt {damage_dealt} damage!"
        
        # Check if monster is defeated
        if self.monster_data['hp'] <= 0:
            await self.handle_victory(interaction, hunter, hunters_data)
            return
        
        # Monster attacks back
        monster_damage = max(1, self.monster_data.get('attack', 5) - effective_stats['defense'])
        
        # Check for evasion buff
        temp_buffs = hunter.get('temp_buffs', {})
        if 'evasion' in temp_buffs:
            result_text += f"\n\nYou evaded the {self.monster_data.get('name', 'monster')}'s attack!"
            del temp_buffs['evasion']
        else:
            hunter['hp'] = max(0, hunter.get('hp', 100) - monster_damage)
            result_text += f"\n\nThe {self.monster_data.get('name', 'monster')} dealt {monster_damage} damage to you!"
        
        # Process turn effects
        turn_effects = process_turn_effects(hunter)
        if turn_effects:
            result_text += f"\n\n{turn_effects}"
        
        # Save hunter data
        hunters_data[self.user_id] = hunter
        self.combat_cog.save_hunters_data(hunters_data)
        
        # Check if hunter is defeated
        if hunter['hp'] <= 0:
            await self.handle_defeat(interaction)
            return
        
        # Update combat display
        await self.update_combat_display(interaction, result_text)
    
    async def ability_callback(self, interaction, ability_id):
        """Handle ability usage"""
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message("This isn't your battle!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        hunters_data = self.combat_cog.load_hunters_data()
        hunter = hunters_data.get(self.user_id, {})
        
        # Apply ability effect
        result_message, success = apply_ability_effect(hunter, self.monster_data, ability_id)
        
        if not success:
            await interaction.followup.send(result_message, ephemeral=True)
            return
        
        result_text = result_message
        
        # Check if monster is defeated
        if self.monster_data['hp'] <= 0:
            await self.handle_victory(interaction, hunter, hunters_data)
            return
        
        # Monster counter-attack (if not frozen)
        if self.monster_data.get('frozen_turns', 0) > 0:
            self.monster_data['frozen_turns'] -= 1
            result_text += f"\n\nThe {self.monster_data.get('name', 'monster')} is frozen and cannot attack!"
        else:
            effective_stats = get_effective_stats(hunter)
            monster_damage = max(1, self.monster_data.get('attack', 5) - effective_stats['defense'])
            
            # Check for evasion buff
            temp_buffs = hunter.get('temp_buffs', {})
            if 'evasion' in temp_buffs:
                result_text += f"\n\nYou evaded the {self.monster_data.get('name', 'monster')}'s attack!"
                del temp_buffs['evasion']
            else:
                hunter['hp'] = max(0, hunter.get('hp', 100) - monster_damage)
                result_text += f"\n\nThe {self.monster_data.get('name', 'monster')} dealt {monster_damage} damage to you!"
        
        # Process turn effects
        turn_effects = process_turn_effects(hunter)
        if turn_effects:
            result_text += f"\n\n{turn_effects}"
        
        # Save hunter data
        hunters_data[self.user_id] = hunter
        self.combat_cog.save_hunters_data(hunters_data)
        
        # Check if hunter is defeated
        if hunter['hp'] <= 0:
            await self.handle_defeat(interaction)
            return
        
        # Update combat display
        await self.update_combat_display(interaction, result_text)
    
    async def flee_callback(self, interaction):
        """Handle flee attempt"""
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message("This isn't your battle!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # 80% chance to flee successfully
        if random.random() < 0.8:
            for item in self.children:
                item.disabled = True
            
            await interaction.followup.send("🏃 You successfully fled from battle!")
            
            try:
                await self.message.edit(view=self)
            except:
                pass
        else:
            await interaction.followup.send("❌ You failed to escape! The monster blocks your path.", ephemeral=True)
    
    async def update_combat_display(self, interaction, result_text):
        """Update the combat embed and buttons with boss dialogue"""
        hunters_data = self.combat_cog.load_hunters_data()
        hunter = hunters_data.get(self.user_id, {})
        
        # Check for boss dialogue triggers
        monster_name = self.monster_data.get('name', 'Monster')
        is_boss = self.monster_data.get('boss', False)
        combat_session = self.combat_cog.active_combats.get(self.user_id, {})
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(self.user_id)
        
        # Check for dialogue triggers
        additional_dialogue = ""
        if is_boss and combat_session:
            current_hp = self.monster_data.get('hp', 50)
            max_hp = combat_session.get('original_hp', current_hp)
            last_dialogue_hp = combat_session.get('last_dialogue_hp', max_hp)
            
            # Check for HP-based dialogue triggers
            dialogue_trigger = should_trigger_dialogue(current_hp, max_hp, last_dialogue_hp)
            if dialogue_trigger:
                boss_dialogue = get_boss_dialogue(monster_name, dialogue_trigger)
                if boss_dialogue:
                    additional_dialogue = f"\n\n{boss_dialogue}"
                    combat_session['last_dialogue_hp'] = current_hp
        
        # Enhanced title for bosses
        embed_title = f"⚔️ Combat: {hunter.get('name', 'Hunter')} vs {monster_name}"
        if is_boss:
            embed_title = f"💀 BOSS ENCOUNTER: {monster_name}"
        
        embed = discord.Embed(
            title=embed_title,
            description=result_text + additional_dialogue,
            color=discord.Color(colors['accent'] if not is_boss else colors['error'])
        )
        
        embed.add_field(
            name="🛡️ Your Status",
            value=f"HP: {hunter.get('hp', 100)}/{hunter.get('max_hp', 100)}\nMP: {hunter.get('mana', 100)}/{hunter.get('max_mana', 100)}",
            inline=True
        )
        
        # Enhanced enemy status with boss effects
        enemy_status = f"HP: {self.monster_data.get('hp', 50)}\nATK: {self.monster_data.get('attack', 10)}"
        if is_boss:
            # Add boss status effects
            current_hp = self.monster_data.get('hp', 50)
            max_hp = combat_session.get('original_hp', current_hp)
            status_effects = get_boss_status_effects(monster_name, current_hp, max_hp)
            if status_effects:
                enemy_status += f"\n{status_effects[0]}"
        
        embed.add_field(
            name="👹 Enemy Status" if not is_boss else "💀 Boss Status", 
            value=enemy_status,
            inline=True
        )
        
        if self.location_data:
            embed.add_field(
                name="📍 Location",
                value=f"{self.location_data.get('name', 'Unknown')} ({self.location_data.get('difficulty', 'Unknown')})",
                inline=False
            )
        
        # Update buttons
        self.add_combat_buttons()
        
        try:
            await self.message.edit(embed=embed, view=self)
        except:
            pass
    
    async def handle_victory(self, interaction, hunter, hunters_data):
        """Handle combat victory"""
        for item in self.children:
            item.disabled = True
        
        # Calculate rewards
        base_exp = self.monster_data.get('exp_reward', 25)
        base_gold = self.monster_data.get('gold_reward', 15)
        
        # Bonus rewards for gates
        if self.location_data and self.combat_type == "gate":
            location_rewards = self.location_data.get('rewards', {})
            base_exp += location_rewards.get('exp', 0)
            base_gold += location_rewards.get('gold', 0)
        
        hunter['gold'] = hunter.get('gold', 0) + base_gold
        
        # Award experience
        from main import award_exp
        level_data = await award_exp(self.user_id, base_exp, self.bot)
        
        # Update quest progress
        from daily_quest_system import update_quest_progress
        update_quest_progress(hunter, 'kill_monsters', 1)
        
        hunters_data[self.user_id] = hunter
        self.combat_cog.save_hunters_data(hunters_data)
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(self.user_id)
        
        embed = discord.Embed(
            title="🎉 Victory!",
            description=f"You defeated the {self.monster_data.get('name', 'monster')}!",
            color=discord.Color(colors['success'])
        )
        
        embed.add_field(
            name="💰 Rewards",
            value=f"EXP: +{base_exp}\nGold: +{base_gold}",
            inline=True
        )
        
        if level_data.get('levels_gained', 0) > 0:
            embed.add_field(
                name="📈 Level Up!",
                value=f"Level {level_data['old_level']} → {level_data['new_level']}",
                inline=True
            )
        
        try:
            await self.message.edit(embed=embed, view=self)
        except:
            pass
    
    async def handle_defeat(self, interaction):
        """Handle combat defeat"""
        for item in self.children:
            item.disabled = True
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(self.user_id)
        
        embed = discord.Embed(
            title="💀 Defeat",
            description=f"You were defeated by the {self.monster_data.get('name', 'monster')}...",
            color=discord.Color(colors['error'])
        )
        
        embed.add_field(
            name="Result",
            value="You respawn at the Hunter's Guild with 1 HP.\nNo experience or gold lost.",
            inline=False
        )
        
        # Reset hunter HP to 1
        hunters_data = self.combat_cog.load_hunters_data()
        hunter = hunters_data.get(self.user_id, {})
        hunter['hp'] = 1
        hunters_data[self.user_id] = hunter
        self.combat_cog.save_hunters_data(hunters_data)
        
        try:
            await self.message.edit(embed=embed, view=self)
        except:
            pass

async def setup(bot):
    await bot.add_cog(AdvancedCombat(bot))