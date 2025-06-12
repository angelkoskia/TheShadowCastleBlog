import discord
from discord.ext import commands
import json
import math
import asyncio
from datetime import datetime, timedelta

# Import leveling system and theme utilities
from utils.leveling_system import leveling_system, get_rank_role_name, RANK_ROLES
from utils.theme_utils import get_user_theme_colors, get_error_embed, get_info_embed

def load_hunters_data_ui():
    """Load hunter data within UI elements"""
    try:
        with open('hunters_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_hunters_data_ui(data):
    """Save hunter data within UI elements"""
    with open('hunters_data.json', 'w') as f:
        json.dump(data, f, indent=4)

def create_progress_bar(current, maximum, length=10):
    """Create a visual progress bar"""
    if maximum == 0:
        return "░" * length
    filled = int((current / maximum) * length)
    return "█" * filled + "░" * (length - filled)

class HelpView(discord.ui.View):
    """Interactive help menu with category navigation"""
    
    def __init__(self, bot, colors, hunter_exists):
        super().__init__(timeout=60)
        self.bot = bot
        self.colors = colors
        self.hunter_exists = hunter_exists
        self.current_page = "Main"
        
        # Define command categories
        self.command_categories = {
            "Main": [
                {"name": "🏠 General Commands", "value": "`.help` - This interactive menu\n`.commands` - Complete command list\n`.start` - Begin your hunter journey\n`.my_adventure` - View your private channel"},
            ],
            "Hunter Commands": [
                {"name": "📊 Profile & Stats", "value": "`.status` - Interactive hunter profile\n`.rest` - Recover HP/MP (5min cooldown)\n`.exp_info` - Detailed leveling information"},
                {"name": "⚔️ Combat", "value": "`.hunt` - Start a hunt for monsters\n`.attack` - Attack during battle\n`.defend` - Defend against attacks\n`.flee` - Attempt to escape battle"},
                {"name": "🎒 Inventory & Shop", "value": "`.inventory` - View your items\n`.shop` - Browse the hunter shop\n`.equip [item]` - Equip an item\n`.use [item]` - Use consumable items"},
                {"name": "🌀 Gates & Dungeons", "value": "`.gates` - List dimensional gates\n`.enter_gate [name]` - Enter a specific gate\n`.dungeons` - List available dungeons\n`.raid [name]` - Start a dungeon raid"},
                {"name": "📋 Quests & Training", "value": "`.daily` - View daily quests\n`.weekly` - View weekly quests\n`.special` - View special quests\n`.train [type]` - Start training session"},
                {"name": "⚡ PvP & Events", "value": "`.challenge [user]` - Challenge to PvP\n`.rankings` - View PvP leaderboard\n`.events` - Current global events"},
                {"name": "🎨 Customization", "value": "`.themes` - View available themes\n`.theme [name]` - Set your theme\n`.preview [theme]` - Preview a theme"},
                {"name": "📖 Solo Leveling Info", "value": "`.weaponsinfo` - All weapons and artifacts\n`.bossinfo` - Shadow army and boss details\n`.gatesinfo` - Dimensional gates information\n`.dungeonsinfo` - Instance dungeons guide\n`.slquickref` - Quick reference guide"}
            ],
            "Admin Commands": [
                {"name": "🔧 Administration", "value": "`.reset_levels` - Reset all players to level 1\n`.set_level [id] [level]` - Set specific user level\n`.set_jinwoo [user]` - Set as Shadow Monarch\n`.reset_stuck` - Reset stuck player states"},
                {"name": "🎯 Event Management", "value": "`.trigger_event [name]` - Manually trigger event\n`.end_event` - End current event\n`.event_cycle` - Rapid event testing"}
            ]
        }
        
        # Create category selection dropdown
        self.create_category_select()
    
    def create_category_select(self):
        """Create the category selection dropdown"""
        options = [
            discord.SelectOption(label="Main", description="General bot commands", emoji="🏠", value="Main")
        ]
        if self.hunter_exists:
            options.append(discord.SelectOption(label="Hunter Commands", description="Commands for hunters", emoji="⚔️", value="Hunter Commands"))
        options.append(discord.SelectOption(label="Admin Commands", description="Bot administration", emoji="⚙️", value="Admin Commands"))
        
        select = discord.ui.Select(
            placeholder="Select a command category...", 
            options=options, 
            custom_id="help_category_select"
        )
        select.callback = self.select_category_callback
        self.add_item(select)
    
    async def on_timeout(self):
        """Handle view timeout"""
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass
    
    def get_page_embed(self, category_name):
        """Generate embed for specific category"""
        embed = discord.Embed(
            title="📚 Solo Leveling RPG - Command Help",
            description=f"**Category: {category_name}**\n\nSelect a category below to explore commands.",
            color=discord.Color(self.colors['accent'])
        )
        
        category_data = self.command_categories.get(category_name, self.command_categories["Main"])
        for field in category_data:
            embed.add_field(name=field["name"], value=field["value"], inline=False)
        
        embed.set_footer(text=f"This menu expires in 60 seconds • Total Categories: {len(self.command_categories)}")
        return embed
    
    async def select_category_callback(self, interaction: discord.Interaction):
        """Handle category selection"""
        # Always defer first to prevent interaction timeout
        await interaction.response.defer()
        
        try:
            # Simplified user validation - just check if message exists
            if not hasattr(self, 'message') or not self.message:
                await interaction.followup.send("This menu session has expired. Please use the command again.", ephemeral=True)
                return
            
            selected_category = interaction.data['values'][0]
            self.current_page = selected_category
            
            new_embed = self.get_page_embed(selected_category)
            await interaction.edit_original_response(embed=new_embed, view=self)
            
        except Exception as e:
            print(f"[ERROR] HelpView select_category_callback: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.followup.send("An error occurred while processing your request.", ephemeral=True)
            except:
                pass

class StatusView(discord.ui.View):
    """Interactive status menu with multiple pages"""
    
    def __init__(self, bot, user_id, initial_page="main"):
        super().__init__(timeout=120)
        self.bot = bot
        self.user_id = str(user_id)
        self.current_page = initial_page
        
        # Add navigation buttons
        self.add_item(StatusButton("Main Profile", "main", "📊", discord.ButtonStyle.primary))
        self.add_item(StatusButton("Equipment", "equipment", "🛡️", discord.ButtonStyle.secondary))
        self.add_item(StatusButton("Statistics", "stats", "📈", discord.ButtonStyle.secondary))
        self.add_item(StatusButton("Progression", "progression", "⭐", discord.ButtonStyle.secondary))
        self.add_item(RefreshButton())
    
    async def on_timeout(self):
        """Handle view timeout"""
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass
    
    async def get_main_profile_embed(self, user_id):
        """Generate main profile embed"""
        hunters_data = load_hunters_data_ui()
        hunter = hunters_data.get(str(user_id))
        
        if not hunter:
            return get_error_embed(user_id, "Hunter profile not found!")
        
        colors = get_user_theme_colors(str(user_id))
        user = self.bot.get_user(int(user_id))
        username = user.display_name if user else "Unknown Hunter"
        
        # Calculate level progress
        total_exp = hunter.get('exp', 0)
        current_level = hunter.get('level', 1)
        current_rank = hunter.get('rank', 'E Rank')
        
        # Get EXP for current and next level
        current_level_exp = leveling_system._exp_table.get(current_level, 0)
        next_level_exp = leveling_system._exp_table.get(current_level + 1, current_level_exp + 1000)
        exp_progress = total_exp - current_level_exp
        exp_needed = next_level_exp - current_level_exp
        
        # Create progress bars
        hp_bar = create_progress_bar(hunter.get('hp', 100), hunter.get('max_hp', 100), 12)
        mp_bar = create_progress_bar(hunter.get('mp', 50), hunter.get('max_mp', 50), 12)
        exp_bar = create_progress_bar(exp_progress, exp_needed, 12)
        
        embed = discord.Embed(
            title=f"🏮 Hunter Profile: {username}",
            color=discord.Color(colors['accent'])
        )
        
        # Add custom title if exists
        if hunter.get('custom_title'):
            embed.description = f"**{hunter['custom_title']}**"
        
        # Basic info
        embed.add_field(
            name="📊 Basic Information",
            value=f"**Level:** {current_level} ({current_rank})\n"
                  f"**Gold:** {hunter.get('gold', 0):,}💰\n"
                  f"**Theme:** {hunter.get('theme', 'default').title()}",
            inline=True
        )
        
        # Health and Mana
        embed.add_field(
            name="💚 Health & Mana",
            value=f"**HP:** {hunter.get('hp', 100)}/{hunter.get('max_hp', 100)}\n{hp_bar}\n"
                  f"**MP:** {hunter.get('mp', 50)}/{hunter.get('max_mp', 50)}\n{mp_bar}",
            inline=True
        )
        
        # Core stats
        embed.add_field(
            name="⚔️ Combat Stats",
            value=f"**STR:** {hunter.get('strength', 10)}\n"
                  f"**AGI:** {hunter.get('agility', 10)}\n"
                  f"**INT:** {hunter.get('intelligence', 10)}\n"
                  f"**DEF:** {hunter.get('defense', 5)}",
            inline=True
        )
        
        # Experience progress
        embed.add_field(
            name="⭐ Experience Progress",
            value=f"**Current EXP:** {total_exp:,}\n"
                  f"**Progress:** {exp_progress:,}/{exp_needed:,}\n{exp_bar}\n"
                  f"**Next Level:** {current_level + 1}",
            inline=False
        )
        
        # Equipment summary
        equipment = hunter.get('equipment', {})
        weapon = equipment.get('weapon', 'None')
        armor = equipment.get('armor', 'None')
        accessory = equipment.get('accessory', 'None')
        
        embed.add_field(
            name="🛡️ Equipment Summary",
            value=f"**Weapon:** {weapon}\n**Armor:** {armor}\n**Accessory:** {accessory}",
            inline=True
        )
        
        # Activity status
        status_text = "Idle"
        if hunter.get('battle'):
            status_text = "In Combat"
        elif hunter.get('gate_battle'):
            status_text = "Exploring Gate"
        elif hunter.get('dungeon_battle'):
            status_text = "In Dungeon"
        
        embed.add_field(
            name="🎯 Current Status",
            value=f"**Activity:** {status_text}\n"
                  f"**Inventory:** {len(hunter.get('inventory', []))} items\n"
                  f"**Daily Kills:** {hunter.get('daily_kills', 0)}",
            inline=True
        )
        
        embed.set_footer(text="Use the buttons below to explore different sections")
        return embed
    
    async def get_equipment_embed(self, user_id):
        """Generate equipment details embed"""
        hunters_data = load_hunters_data_ui()
        hunter = hunters_data.get(str(user_id))
        
        if not hunter:
            return get_error_embed(user_id, "Hunter profile not found!")
        
        colors = get_user_theme_colors(str(user_id))
        user = self.bot.get_user(int(user_id))
        username = user.display_name if user else "Unknown Hunter"
        
        embed = discord.Embed(
            title=f"🛡️ Equipment Details: {username}",
            color=discord.Color(colors['accent'])
        )
        
        equipment = hunter.get('equipment', {})
        
        # Weapon details
        weapon = equipment.get('weapon')
        if weapon and weapon != 'None':
            embed.add_field(
                name="⚔️ Weapon",
                value=f"**{weapon}**\nEquipped and ready for battle",
                inline=False
            )
        else:
            embed.add_field(
                name="⚔️ Weapon",
                value="*No weapon equipped*\nVisit the shop to find weapons!",
                inline=False
            )
        
        # Armor details
        armor = equipment.get('armor')
        if armor and armor != 'None':
            embed.add_field(
                name="🛡️ Armor",
                value=f"**{armor}**\nProviding protection in combat",
                inline=False
            )
        else:
            embed.add_field(
                name="🛡️ Armor",
                value="*No armor equipped*\nArmor increases your defense!",
                inline=False
            )
        
        # Accessory details
        accessory = equipment.get('accessory')
        if accessory and accessory != 'None':
            embed.add_field(
                name="💍 Accessory",
                value=f"**{accessory}**\nEnhancing your abilities",
                inline=False
            )
        else:
            embed.add_field(
                name="💍 Accessory",
                value="*No accessory equipped*\nAccessories provide special bonuses!",
                inline=False
            )
        
        # Equipment bonuses
        embed.add_field(
            name="📈 Equipment Bonuses",
            value="Use `.inventory` to see detailed item stats\nUse `.equip [item]` to change equipment",
            inline=False
        )
        
        embed.set_footer(text="Equipment affects your combat performance")
        return embed
    
    async def get_stats_embed(self, user_id):
        """Generate detailed statistics embed"""
        hunters_data = load_hunters_data_ui()
        hunter = hunters_data.get(str(user_id))
        
        if not hunter:
            return get_error_embed(user_id, "Hunter profile not found!")
        
        colors = get_user_theme_colors(str(user_id))
        user = self.bot.get_user(int(user_id))
        username = user.display_name if user else "Unknown Hunter"
        
        embed = discord.Embed(
            title=f"📈 Detailed Statistics: {username}",
            color=discord.Color(colors['accent'])
        )
        
        # Base vs current stats
        base_str = hunter.get('base_strength', hunter.get('strength', 10))
        base_agi = hunter.get('base_agility', hunter.get('agility', 10))
        base_int = hunter.get('base_intelligence', hunter.get('intelligence', 10))
        base_def = hunter.get('base_defense', hunter.get('defense', 5))
        
        current_str = hunter.get('strength', 10)
        current_agi = hunter.get('agility', 10)
        current_int = hunter.get('intelligence', 10)
        current_def = hunter.get('defense', 5)
        
        embed.add_field(
            name="💪 Strength",
            value=f"**Base:** {base_str}\n**Current:** {current_str}\n**Bonus:** +{current_str - base_str}",
            inline=True
        )
        
        embed.add_field(
            name="💨 Agility",
            value=f"**Base:** {base_agi}\n**Current:** {current_agi}\n**Bonus:** +{current_agi - base_agi}",
            inline=True
        )
        
        embed.add_field(
            name="🧠 Intelligence",
            value=f"**Base:** {base_int}\n**Current:** {current_int}\n**Bonus:** +{current_int - base_int}",
            inline=True
        )
        
        embed.add_field(
            name="🛡️ Defense",
            value=f"**Base:** {base_def}\n**Current:** {current_def}\n**Bonus:** +{current_def - base_def}",
            inline=True
        )
        
        # Health and Mana breakdown
        base_hp = 100 + (hunter.get('level', 1) - 1) * 25
        base_mp = 50 + (hunter.get('level', 1) - 1) * 15
        
        embed.add_field(
            name="❤️ Health Points",
            value=f"**Current:** {hunter.get('hp', 100)}\n**Maximum:** {hunter.get('max_hp', 100)}\n**Base for Level:** {base_hp}",
            inline=True
        )
        
        embed.add_field(
            name="💙 Mana Points",
            value=f"**Current:** {hunter.get('mp', 50)}\n**Maximum:** {hunter.get('max_mp', 50)}\n**Base for Level:** {base_mp}",
            inline=True
        )
        
        # Combat statistics
        battles_won = hunter.get('battles_won', 0)
        battles_lost = hunter.get('battles_lost', 0)
        total_battles = battles_won + battles_lost
        win_rate = (battles_won / total_battles * 100) if total_battles > 0 else 0
        
        embed.add_field(
            name="⚔️ Combat Record",
            value=f"**Battles Won:** {battles_won}\n**Battles Lost:** {battles_lost}\n**Win Rate:** {win_rate:.1f}%",
            inline=False
        )
        
        embed.set_footer(text="Stats are affected by equipment and training")
        return embed
    
    async def get_progression_embed(self, user_id):
        """Generate progression and achievements embed"""
        hunters_data = load_hunters_data_ui()
        hunter = hunters_data.get(str(user_id))
        
        if not hunter:
            return get_error_embed(user_id, "Hunter profile not found!")
        
        colors = get_user_theme_colors(str(user_id))
        user = self.bot.get_user(int(user_id))
        username = user.display_name if user else "Unknown Hunter"
        
        embed = discord.Embed(
            title=f"⭐ Progression & Achievements: {username}",
            color=discord.Color(colors['accent'])
        )
        
        current_level = hunter.get('level', 1)
        current_rank = hunter.get('rank', 'E Rank')
        
        # Rank progression
        rank_order = ['E Rank', 'D Rank', 'C Rank', 'B Rank', 'A Rank', 'S Rank', 'National Level Hunter', 'Monarch']
        current_rank_index = rank_order.index(current_rank) if current_rank in rank_order else 0
        next_rank = rank_order[current_rank_index + 1] if current_rank_index < len(rank_order) - 1 else "Maximum Rank"
        
        embed.add_field(
            name="🏆 Rank Progression",
            value=f"**Current Rank:** {current_rank}\n**Next Rank:** {next_rank}\n**Progress:** {current_rank_index + 1}/{len(rank_order)}",
            inline=False
        )
        
        # Experience tracking
        total_exp = hunter.get('exp', 0)
        exp_to_max = leveling_system._exp_table.get(100, 1000000) - total_exp
        
        embed.add_field(
            name="📊 Experience Tracking",
            value=f"**Total EXP Earned:** {total_exp:,}\n**EXP to Max Level:** {exp_to_max:,}\n**Current Level:** {current_level}/100",
            inline=True
        )
        
        # Quests completed
        daily_completed = len(hunter.get('completed_daily_quests', []))
        weekly_completed = len(hunter.get('completed_weekly_quests', []))
        special_completed = len(hunter.get('completed_special_quests', []))
        
        embed.add_field(
            name="📋 Quest Progress",
            value=f"**Daily Completed:** {daily_completed}\n**Weekly Completed:** {weekly_completed}\n**Special Completed:** {special_completed}",
            inline=True
        )
        
        # Activity tracking
        gates_cleared = hunter.get('gates_cleared', 0)
        dungeons_cleared = hunter.get('dungeons_cleared', 0)
        monsters_defeated = hunter.get('monsters_defeated', 0)
        
        embed.add_field(
            name="🎯 Activity Summary",
            value=f"**Gates Cleared:** {gates_cleared}\n**Dungeons Cleared:** {dungeons_cleared}\n**Monsters Defeated:** {monsters_defeated}",
            inline=False
        )
        
        # PvP statistics
        pvp_wins = hunter.get('pvp_wins', 0)
        pvp_losses = hunter.get('pvp_losses', 0)
        pvp_rank = hunter.get('pvp_rank', 'Unranked')
        
        embed.add_field(
            name="⚡ PvP Statistics",
            value=f"**PvP Wins:** {pvp_wins}\n**PvP Losses:** {pvp_losses}\n**PvP Rank:** {pvp_rank}",
            inline=True
        )
        
        # Achievements
        achievements = hunter.get('achievements', [])
        if achievements:
            embed.add_field(
                name="🏅 Recent Achievements",
                value="\n".join(achievements[-3:]) if len(achievements) > 3 else "\n".join(achievements),
                inline=True
            )
        else:
            embed.add_field(
                name="🏅 Achievements",
                value="*No achievements yet*\nComplete quests and battles to earn achievements!",
                inline=True
            )
        
        embed.set_footer(text="Keep hunting to unlock more achievements!")
        return embed

class StatusButton(discord.ui.Button):
    """Custom button for status navigation"""
    
    def __init__(self, label, page, emoji, style):
        super().__init__(label=label, style=style, emoji=emoji, custom_id=f"status_{page}")
        self.page = page
    
    async def callback(self, interaction: discord.Interaction):
        # Always defer first to prevent interaction timeout
        await interaction.response.defer()
        
        try:
            # Simplified validation - just check if view has message
            if not hasattr(self.view, 'message') or not self.view.message:
                await interaction.followup.send("This status session has expired. Please use the command again.", ephemeral=True)
                return
            
            self.view.current_page = self.page
            
            # Update button styles
            for item in self.view.children:
                if isinstance(item, StatusButton):
                    if item.page == self.page:
                        item.style = discord.ButtonStyle.primary
                    else:
                        item.style = discord.ButtonStyle.secondary
            
            # Get the appropriate embed
            if self.page == "main":
                embed = await self.view.get_main_profile_embed(self.view.user_id)
            elif self.page == "equipment":
                embed = await self.view.get_equipment_embed(self.view.user_id)
            elif self.page == "stats":
                embed = await self.view.get_stats_embed(self.view.user_id)
            elif self.page == "progression":
                embed = await self.view.get_progression_embed(self.view.user_id)
            else:
                embed = await self.view.get_main_profile_embed(self.view.user_id)
            
            await interaction.edit_original_response(embed=embed, view=self.view)
            
        except Exception as e:
            print(f"[ERROR] StatusButton callback: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.followup.send("An error occurred while processing your request.", ephemeral=True)
            except:
                pass

class RefreshButton(discord.ui.Button):
    """Refresh button to update status data"""
    
    def __init__(self):
        super().__init__(label="Refresh", style=discord.ButtonStyle.success, emoji="🔄", custom_id="status_refresh")
    
    async def callback(self, interaction: discord.Interaction):
        # Always defer first to prevent interaction timeout
        await interaction.response.defer()
        
        try:
            # Simplified validation - just check if view has message
            if not hasattr(self.view, 'message') or not self.view.message:
                await interaction.followup.send("This status session has expired. Please use the command again.", ephemeral=True)
                return
            
            # Refresh the current page
            if self.view.current_page == "main":
                embed = await self.view.get_main_profile_embed(self.view.user_id)
            elif self.view.current_page == "equipment":
                embed = await self.view.get_equipment_embed(self.view.user_id)
            elif self.view.current_page == "stats":
                embed = await self.view.get_stats_embed(self.view.user_id)
            elif self.view.current_page == "progression":
                embed = await self.view.get_progression_embed(self.view.user_id)
            else:
                embed = await self.view.get_main_profile_embed(self.view.user_id)
            
            await interaction.edit_original_response(embed=embed, view=self.view)
            
        except Exception as e:
            print(f"[ERROR] RefreshButton callback: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.followup.send("An error occurred while refreshing your status.", ephemeral=True)
            except:
                pass

class CombatView(discord.ui.View):
    """Interactive combat view with action buttons"""
    
    def __init__(self, bot, ctx, user_id, monster_data, combat_type="hunt"):
        super().__init__(timeout=120)  # 2-minute timeout for inactivity
        self.bot = bot
        self.ctx = ctx
        self.user_id = str(user_id)
        self.monster_data = monster_data
        self.combat_type = combat_type
        self.message = None
        self.player_action = None
        self.player_turn_active = True
        self.combat_ended = False
        self.item_used = None
        self.victory_data = None
        
        # Add Use Item button conditionally for hunt combat
        if combat_type == "hunt":
            use_item_btn = discord.ui.Button(
                label="Use Item", 
                style=discord.ButtonStyle.blurple, 
                custom_id="combat_item", 
                emoji="🎒"
            )
            use_item_btn.callback = self.item_button_callback
            self.add_item(use_item_btn)

    async def on_timeout(self):
        """Handle view timeout"""
        if self.message and not self.combat_ended:
            for item in self.children:
                item.disabled = True
            try:
                await self.message.edit(content="Combat session timed out. You have fled the battle.", view=self)
            except discord.HTTPException:
                pass
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the correct user can interact"""
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message("This isn't your battle!", ephemeral=True)
            return False
        if not self.player_turn_active:
            await interaction.response.send_message("Wait for your turn!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Attack", style=discord.ButtonStyle.red, custom_id="combat_attack", emoji="⚔️")
    async def attack_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.player_action = "attack"
        self.player_turn_active = False
        self.stop()

    @discord.ui.button(label="Defend", style=discord.ButtonStyle.green, custom_id="combat_defend", emoji="🛡️")
    async def defend_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.player_action = "defend"
        self.player_turn_active = False
        self.stop()

    @discord.ui.button(label="Flee", style=discord.ButtonStyle.grey, custom_id="combat_flee", emoji="🏃")
    async def flee_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.player_action = "flee"
        self.player_turn_active = False
        self.stop()

    async def item_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Load hunter data to check inventory
        hunters_data = load_hunters_data_ui()
        hunter = hunters_data.get(self.user_id)
        
        if not hunter or not hunter.get('inventory'):
            await interaction.followup.send("You have no items to use!", ephemeral=True)
            return
            
        # For now, auto-use the first health potion found
        inventory = hunter.get('inventory', [])
        health_items = [item for item in inventory if 'potion' in item.lower() and 'health' in item.lower()]
        
        if health_items:
            self.player_action = "use_item"
            self.item_used = health_items[0]
            self.player_turn_active = False
            self.stop()
        else:
            await interaction.followup.send("You have no usable combat items!", ephemeral=True)

    def create_combat_embed(self, hunter, monster, turn_info=""):
        """Create combat status embed"""
        colors = get_user_theme_colors(self.user_id)
        
        # Create health bars
        hunter_hp_bar = create_progress_bar(hunter['hp'], hunter.get('max_hp', 100))
        hunter_mp_bar = create_progress_bar(hunter['mp'], hunter.get('max_mp', 50))
        monster_hp_bar = create_progress_bar(monster['current_hp'], monster['max_hp'])
        
        embed = discord.Embed(
            title=f"⚔️ Battle: {hunter.get('name', 'Hunter')} vs {monster['name']}",
            description=f"**{monster['name']}**\n"
                       f"❤️ HP: {monster_hp_bar} {monster['current_hp']}/{monster['max_hp']}\n\n"
                       f"**Your Status**\n"
                       f"❤️ HP: {hunter_hp_bar} {hunter['hp']}/{hunter.get('max_hp', 100)}\n"
                       f"💠 MP: {hunter_mp_bar} {hunter['mp']}/{hunter.get('max_mp', 50)}",
            color=discord.Color(colors['combat'])
        )
        
        if turn_info:
            embed.add_field(name="Combat Log", value=turn_info, inline=False)
            
        embed.set_footer(text="Choose your action!")
        return embed

    def disable_all_buttons(self):
        """Disable all combat buttons"""
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True