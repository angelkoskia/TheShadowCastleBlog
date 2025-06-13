import discord
from discord.ext import commands
import json
import random
import asyncio

class Gates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gate_data = self.load_gate_data()
        self.active_explorations = {}  # Track active doorway explorations
    
    def load_gate_data(self):
        """Load gate configuration from JSON file"""
        try:
            with open('data/gates.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self.get_default_gates()
    
    def get_default_gates(self):
        """Default gate configuration if file doesn't exist"""
        return {
            "gates": {
                "E-Rank": [
                    {"name": "Abandoned Factory", "difficulty": 1, "level_req": 1, "rewards": {"exp": 50, "gold": 100}},
                    {"name": "Dark Alley", "difficulty": 2, "level_req": 3, "rewards": {"exp": 75, "gold": 150}}
                ],
                "D-Rank": [
                    {"name": "Haunted School", "difficulty": 3, "level_req": 10, "rewards": {"exp": 150, "gold": 300}},
                    {"name": "Underground Tunnel", "difficulty": 4, "level_req": 15, "rewards": {"exp": 200, "gold": 400}}
                ],
                "C-Rank": [
                    {"name": "Ancient Ruins", "difficulty": 5, "level_req": 25, "rewards": {"exp": 350, "gold": 700}},
                    {"name": "Mystic Forest", "difficulty": 6, "level_req": 30, "rewards": {"exp": 450, "gold": 900}}
                ],
                "B-Rank": [
                    {"name": "Crystal Caverns", "difficulty": 7, "level_req": 40, "rewards": {"exp": 600, "gold": 1200}},
                    {"name": "Demon's Lair", "difficulty": 8, "level_req": 45, "rewards": {"exp": 750, "gold": 1500}}
                ],
                "A-Rank": [
                    {"name": "Dragon's Den", "difficulty": 9, "level_req": 60, "rewards": {"exp": 1000, "gold": 2000}},
                    {"name": "Shadow Realm", "difficulty": 10, "level_req": 70, "rewards": {"exp": 1250, "gold": 2500}}
                ],
                "S-Rank": [
                    {"name": "Heaven's Trial", "difficulty": 12, "level_req": 80, "rewards": {"exp": 1750, "gold": 3500}},
                    {"name": "Monarch's Domain", "difficulty": 15, "level_req": 90, "rewards": {"exp": 2500, "gold": 5000}}
                ],
                "Red-Gate": [
                    {"name": "Red Gate (E)", "difficulty": 3, "level_req": 5, "special_access": "red_gates", "rewards": {"exp": 200, "gold": 400, "items": ["Shadow Fragment"]}},
                    {"name": "Red Gate (D)", "difficulty": 6, "level_req": 15, "special_access": "red_gates", "rewards": {"exp": 500, "gold": 800, "items": ["Shadow Essence"]}},
                    {"name": "Red Gate (C)", "difficulty": 10, "level_req": 30, "special_access": "red_gates", "rewards": {"exp": 1000, "gold": 1600, "items": ["Shadow Crystal"]}},
                    {"name": "Red Gate (B)", "difficulty": 15, "level_req": 45, "special_access": "red_gates", "rewards": {"exp": 1800, "gold": 2800, "items": ["Shadow Stone"]}},
                    {"name": "Red Gate (A)", "difficulty": 20, "level_req": 65, "special_access": "red_gates", "rewards": {"exp": 2800, "gold": 4200, "items": ["Shadow Core"]}},
                    {"name": "Red Gate (S)", "difficulty": 25, "level_req": 85, "special_access": "red_gates", "rewards": {"exp": 4000, "gold": 6000, "items": ["Shadow Heart"]}}
                ]
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
    
    @commands.command(name='gates', aliases=['doorways'])
    async def list_gates(self, ctx):
        """Display available dimensional gates"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        
        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use `.start`")
            return
        
        hunter = hunters_data[user_id]
        hunter_level = hunter['level']
        hunter_rank = hunter['rank']
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        embed = discord.Embed(
            title="🌀 Dimensional Gates",
            description="Choose a gate to explore based on your rank and level",
            color=discord.Color(colors['accent'])
        )
        
        # Show all available doorways by rank
        all_ranks = ["E-Rank", "D-Rank", "C-Rank", "B-Rank", "A-Rank", "S-Rank"]
        hunter_rank_index = all_ranks.index(f"{hunter_rank}-Rank") if f"{hunter_rank}-Rank" in all_ranks else 0
        
        for i, rank in enumerate(all_ranks):
            if rank in self.gate_data["gates"]:
                gates = self.gate_data["gates"][rank]
                gate_list = ""
                
                for gate in gates:
                    if i <= hunter_rank_index and hunter_level >= gate["level_req"]:
                        status = "✅ Available"
                        status_color = "🟢"
                    elif i <= hunter_rank_index:
                        status = f"🔒 Level {gate['level_req']} required"
                        status_color = "🟡"
                    else:
                        status = f"🔒 {rank} required"
                        status_color = "🔴"
                    
                    gate_list += f"{status_color} **{gate['name']}** (Lv.{gate['level_req']}+)\n"
                    gate_list += f"   Difficulty: {gate['difficulty']} | Rewards: {gate['rewards']['exp']} EXP, {gate['rewards']['gold']} Gold\n"
                    gate_list += f"   Status: {status}\n\n"
                
                if gate_list:
                    rank_color = "🟢" if i <= hunter_rank_index else "🔴"
                    embed.add_field(name=f"{rank_color} {rank} Gates", value=gate_list, inline=False)
        
        # Show Red Gates only if player has special access
        special_access = hunter.get('special_access', {})
        if special_access.get('red_gates', False) and "Red-Gate" in self.gate_data["gates"]:
            red_gates = self.gate_data["gates"]["Red-Gate"]
            red_gate_list = ""
            
            for gate in red_gates:
                if hunter_level >= gate["level_req"]:
                    status = "✅ Available"
                    status_color = "🔴"
                else:
                    status = f"🔒 Level {gate['level_req']} required"
                    status_color = "🟡"
                
                red_gate_list += f"{status_color} **{gate['name']}** (Lv.{gate['level_req']}+)\n"
                red_gate_list += f"   Difficulty: {gate['difficulty']} | Rewards: {gate['rewards']['exp']} EXP, {gate['rewards']['gold']} Gold\n"
                if 'items' in gate['rewards']:
                    red_gate_list += f"   Special Items: {', '.join(gate['rewards']['items'])}\n"
                red_gate_list += f"   Status: {status}\n\n"
            
            if red_gate_list:
                embed.add_field(name="🔴 Red Gates (Special Access)", value=red_gate_list, inline=False)
        
        embed.set_footer(text="Use `.enter_gate <name>` to enter a dimensional gate")
        await ctx.send(embed=embed)
    
    @commands.command(name='enter_gate', aliases=['enter_doorway'])
    async def enter_gate(self, ctx, *, gate_name):
        """Enter a specific dimensional gate"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        
        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use `.start`")
            return
        
        hunter = hunters_data[user_id]
        
        # Check if hunter is already in any type of battle or exploration
        if hunter.get('battle') or hunter.get('gate_battle') or hunter.get('dungeon_battle'):
            await ctx.send("You're already in battle! Finish your current fight first.")
            return
            
        # Check if already exploring a doorway
        if user_id in self.active_explorations:
            await ctx.send("You're already exploring a dimensional gate! Complete your current exploration first.")
            return
        
        # Find the gate
        selected_gate = None
        gate_rank = None
        for rank, gates in self.gate_data["gates"].items():
            for gate in gates:
                if gate["name"].lower() == gate_name.lower():
                    selected_gate = gate
                    gate_rank = rank
                    break
        
        if not selected_gate:
            await ctx.send(f"Dimensional gate '{gate_name}' not found! Use `.gates` to see available gates.")
            return
        
        # Check special access for Red Gates
        if gate_rank == "Red-Gate":
            special_access = hunter.get('special_access', {})
            if not special_access.get('red_gates', False):
                await ctx.send("🔴 **Access Denied!** You need a Red Gate Key to enter Red Gates.\nUse a Red Gate Key with `.use Red Gate Key` to unlock access.")
                return
        
        # Check level requirement
        if hunter['level'] < selected_gate["level_req"]:
            await ctx.send(f"You need to be level {selected_gate['level_req']} to enter this dimensional gate!")
            return
        
        # Start gate exploration
        embed = discord.Embed(
            title=f"🌀 Entering {selected_gate['name']}",
            description="You step through the dimensional gate...",
            color=discord.Color.dark_purple()
        )
        
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(2)
        
        # Determine floors based on gate type and difficulty
        if selected_gate['name'].startswith('Red Gate'):
            max_floors = 5 + selected_gate['difficulty'] // 3  # Red gates have more floors
        else:
            max_floors = 3 + selected_gate['difficulty'] // 4  # Regular gates scale with difficulty
        
        boss_floor = max_floors  # Boss is on the final floor
        
        # Start interactive gate exploration with floors
        gate_data = {
            "gate_name": selected_gate['name'],
            "current_floor": 1,
            "max_floors": max_floors,
            "boss_floor": boss_floor,
            "difficulty": selected_gate['difficulty'],
            "rewards": selected_gate['rewards'],
            "total_exp": 0,
            "total_gold": 0,
            "hunter_hp": hunter['hp'],
            "hunter_max_hp": hunter.get('max_hp', 100),
            "gate_type": "red" if selected_gate['name'].startswith('Red Gate') else "normal"
        }
        
        # Store active gate exploration
        if not hasattr(self, 'active_explorations'):
            self.active_explorations = {}
        self.active_explorations[user_id] = gate_data
        
        # Start first floor
        await self.process_gate_floor(ctx, user_id)
    
    async def process_gate_floor(self, ctx, user_id):
        """Process a single floor of the gate"""
        if user_id not in self.active_explorations:
            return
        
        exploration = self.active_explorations[user_id]
        hunters_data = self.load_hunters_data()
        hunter = hunters_data[user_id]
        
        current_floor = exploration["current_floor"]
        
        # Ensure boss_floor exists with proper fallback
        if "boss_floor" not in exploration:
            exploration["boss_floor"] = exploration.get("max_floors", 3)
        
        boss_floor = exploration["boss_floor"]
        
        # Check if exploration is complete
        if current_floor > boss_floor:
            await self.complete_gate_exploration(ctx, user_id, True)
            return
            
        is_boss_floor = current_floor == boss_floor
        
        # Generate monster for this floor with proper scaling
        if is_boss_floor:
            # Boss monster with enhanced stats and rewards
            if exploration.get("gate_type") == "red":
                base_hp = 120 + (exploration["difficulty"] * 20)
                base_attack = 25 + (exploration["difficulty"] * 4)
                boss_name = f"Red {exploration['gate_name']} King"
            else:
                base_hp = 100 + (exploration["difficulty"] * 15)
                base_attack = 20 + (exploration["difficulty"] * 3)
                boss_name = f"{exploration['gate_name']} Boss"
            
            monster = {
                "name": boss_name,
                "hp": base_hp,
                "attack": base_attack,
                "defense": 3 + (exploration["difficulty"] // 2),
                "exp_reward": exploration["rewards"]["exp"],
                "gold_reward": exploration["rewards"]["gold"],
                "level": 5 + exploration["difficulty"],
                "abilities": ["Powerful Strike", "Rage"],
                "rarity": "boss"
            }
        else:
            # Regular floor monster with scaling difficulty
            floor_multiplier = 1.2 ** (current_floor - 1)
            base_hp = int((25 + (exploration["difficulty"] * 4)) * floor_multiplier)
            base_attack = int((6 + (exploration["difficulty"] * 2)) * floor_multiplier)
            
            monster_types = ["Guardian", "Sentinel", "Warden", "Keeper", "Protector"]
            monster_name = f"Floor {current_floor} {monster_types[(current_floor - 1) % len(monster_types)]}"
            
            monster = {
                "name": monster_name,
                "hp": base_hp,
                "attack": base_attack,
                "defense": 1 + (exploration["difficulty"] // 3),
                "exp_reward": int((20 + (current_floor * 8)) * (1 + exploration["difficulty"] * 0.1)),
                "gold_reward": int((30 + (current_floor * 15)) * (1 + exploration["difficulty"] * 0.1)),
                "level": current_floor + exploration["difficulty"] // 2,
                "abilities": ["Strike"],
                "rarity": "common"
            }
        
        if is_boss_floor:
            # Boss encounter - ask player if they want to fight or flee
            from utils.theme_utils import get_user_theme_colors
            colors = get_user_theme_colors(ctx.author.id)
            
            embed = discord.Embed(
                title=f"👑 Floor {current_floor} - Boss Chamber",
                description=f"You stand before the chamber of **{monster['name']}**\n\nA powerful aura emanates from within. This is your final challenge!",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="Boss Information",
                value=f"👹 **{monster['name']}**\n🏷️ Level: {monster['level']}\n⚔️ Difficulty: {monster['rarity'].title()}",
                inline=True
            )
            
            embed.add_field(
                name="Your Status",
                value=f"❤️ HP: {hunter['hp']}/{hunter.get('max_hp', 100)}\n⭐ Level: {hunter['level']}",
                inline=True
            )
            
            embed.add_field(
                name="Choose Your Action",
                value="⚔️ **Fight** - Challenge the boss\n🏃 **Flee** - Return safely with current rewards",
                inline=False
            )
            
            message = await ctx.send(embed=embed)
            await message.add_reaction("⚔️")
            await message.add_reaction("🏃")
            
            def check(reaction, user):
                return (user.id == ctx.author.id and str(reaction.emoji) in ["⚔️", "🏃"] and 
                       reaction.message.id == message.id)
            
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
                
                if str(reaction.emoji) == "🏃":
                    # Player chose to flee - complete exploration
                    await self.complete_gate_exploration(ctx, user_id, True)
                    return
                else:
                    # Player chose to fight - start boss battle
                    hunter['gate_battle'] = {
                        'monster': monster,
                        'monster_hp': monster['hp'],
                        'floor': current_floor,
                        'is_boss': is_boss_floor
                    }
                    
                    self.save_hunters_data(hunters_data)
                    
                    embed = discord.Embed(
                        title=f"⚔️ Boss Battle - {monster['name']}",
                        description=f"The battle begins! Face the mighty {monster['name']}!",
                        color=discord.Color.red()
                    )
                    
            except asyncio.TimeoutError:
                await ctx.send("You hesitated too long! The gate exploration has been cancelled.")
                if user_id in self.active_explorations:
                    del self.active_explorations[user_id]
                return
        else:
            # Regular floor exploration - automatically proceed
            await self.explore_floor(ctx, user_id, current_floor, exploration)
            return
        
        # Create battle embed for boss fights
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        embed = discord.Embed(
            title=f"⚔️ Floor {current_floor} - {monster['name']}",
            description=f"A {monster['name']} blocks your path!" + (" This is the final boss!" if is_boss_floor else ""),
            color=discord.Color.red() if is_boss_floor else discord.Color(colors['accent'])
        )
        
        def create_progress_bar(current, maximum, length=10):
            filled = int((current / maximum) * length)
            bar = "█" * filled + "░" * (length - filled)
            return f"{bar} {current}/{maximum}"
        
        hunter_bar = create_progress_bar(hunter['hp'], hunter.get('max_hp', 100))
        monster_bar = create_progress_bar(monster['hp'], monster['hp'])
        
        embed.add_field(
            name="Your Status",
            value=f"❤️ HP: {hunter['hp']}/{hunter.get('max_hp', 100)}\n{hunter_bar}",
            inline=True
        )
        
        embed.add_field(
            name="Enemy Status", 
            value=f"👹 {monster['name']}\n❤️ HP: {monster['hp']}/{monster['hp']}\n{monster_bar}",
            inline=True
        )
        
        embed.add_field(
            name="Combat Commands",
            value="`.attack` - Attack the enemy\n`.defend` - Reduce incoming damage\n`.flee` - Escape from battle",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def explore_floor(self, ctx, user_id, current_floor, exploration):
        """Automatically explore a regular floor"""
        hunters_data = self.load_hunters_data()
        hunter = hunters_data[user_id]
        
        # Ensure boss_floor exists with proper fallback
        if "boss_floor" not in exploration:
            exploration["boss_floor"] = exploration.get("max_floors", 3)
        
        import random
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        # Calculate exploration success chance
        hunter_power = hunter['strength'] + hunter['agility'] + hunter['intelligence'] + (hunter['level'] * 2)
        floor_difficulty = exploration["difficulty"] + (current_floor * 3)
        success_chance = 0.7 + ((hunter_power - floor_difficulty) * 0.01)
        success_chance = max(0.3, min(0.9, success_chance))
        
        embed = discord.Embed(
            title=f"🗺️ Floor {current_floor} Exploration",
            color=discord.Color(colors['accent'])
        )
        
        if random.random() < success_chance:
            # Successful exploration
            exp_gained = 15 + (current_floor * 8) + (exploration["difficulty"] * 2)
            gold_gained = 25 + (current_floor * 12) + (exploration["difficulty"] * 3)
            
            exploration['total_exp'] += exp_gained
            exploration['total_gold'] += gold_gained
            
            embed.description = f"You successfully explore floor {current_floor}!"
            embed.color = discord.Color.green()
            embed.add_field(
                name="Floor Cleared",
                value=f"💰 {gold_gained} Gold\n⭐ {exp_gained} EXP\nMoving to next floor...",
                inline=False
            )
            
            # Advance to next floor
            exploration['current_floor'] += 1
            await ctx.send(embed=embed)
            await asyncio.sleep(2)
            await self.process_gate_floor(ctx, user_id)
        else:
            # Failed exploration - player takes damage
            damage = random.randint(15, 35)
            hunter['hp'] = max(0, hunter['hp'] - damage)
            
            embed.description = f"Floor {current_floor} proves dangerous!"
            embed.color = discord.Color.orange()
            embed.add_field(
                name="Exploration Result",
                value=f"💔 You took {damage} damage\n❤️ HP: {hunter['hp']}/{hunter.get('max_hp', 100)}",
                inline=False
            )
            
            if hunter['hp'] <= 0:
                # Player died - implement death penalty
                await self.handle_death(ctx, user_id, hunter, hunters_data, "floor exploration")
                return
            else:
                embed.add_field(
                    name="Continue?",
                    value="React with ⚔️ to continue or 🏃 to retreat",
                    inline=False
                )
                
                message = await ctx.send(embed=embed)
                await message.add_reaction("⚔️")
                await message.add_reaction("🏃")
                
                def check(reaction, user):
                    return (user.id == ctx.author.id and str(reaction.emoji) in ["⚔️", "🏃"] and 
                           reaction.message.id == message.id)
                
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
                    
                    if str(reaction.emoji) == "🏃":
                        await self.complete_gate_exploration(ctx, user_id, True)
                    else:
                        # Continue exploring
                        exploration['current_floor'] += 1
                        self.save_hunters_data(hunters_data)
                        await asyncio.sleep(1)
                        await self.process_gate_floor(ctx, user_id)
                        
                except asyncio.TimeoutError:
                    await ctx.send("No response received. Retreating from gate...")
                    await self.complete_gate_exploration(ctx, user_id, True)
    
    async def handle_death(self, ctx, user_id, hunter, hunters_data, death_cause):
        """Handle player death with 3-minute respawn timer"""
        import time
        
        # Set death timer (3 minutes)
        death_time = time.time() + 180  # 3 minutes
        hunter['death_timer'] = death_time
        hunter['hp'] = hunter.get('max_hp', 100)  # Respawn with full health
        
        # Clear any active battles
        if 'gate_battle' in hunter:
            del hunter['gate_battle']
        
        # Remove from active exploration
        if hasattr(self, 'active_explorations') and user_id in self.active_explorations:
            del self.active_explorations[user_id]
        
        self.save_hunters_data(hunters_data)
        
        embed = discord.Embed(
            title="💀 Death",
            description=f"You have died during {death_cause}!",
            color=discord.Color.dark_red()
        )
        
        embed.add_field(
            name="Respawn Timer",
            value="⏰ You must wait **3 minutes** before taking any actions.\nUse `.status` to check remaining time.",
            inline=False
        )
        
        embed.add_field(
            name="Penalty",
            value="❤️ Respawned with full health\n🚫 All activities disabled for 3 minutes",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def complete_gate_exploration(self, ctx, user_id, success):
        """Complete the gate exploration and award rewards"""
        if user_id not in self.active_explorations:
            return
        
        exploration = self.active_explorations[user_id]
        
        # Prevent duplicate completion calls
        if exploration.get('completed', False):
            return
        exploration['completed'] = True
        
        # Ensure boss_floor exists with proper fallback
        if "boss_floor" not in exploration:
            exploration["boss_floor"] = exploration.get("max_floors", 3)
        
        hunters_data = self.load_hunters_data()
        hunter = hunters_data[user_id]
        
        # Award accumulated rewards
        total_exp = exploration["total_exp"]
        total_gold = exploration["total_gold"]
        
        level_ups = 0
        rank_up_msg = ""
        level_up_data = None
        
        if success and total_exp > 0:
            # Award EXP using new leveling system
            from utils.leveling_system import award_exp, send_level_up_notification
            level_up_data = await award_exp(user_id, total_exp, self.bot, "gate_clear")
            
            hunter['gold'] = hunter.get('gold', 0) + total_gold
            
            # Track gate completion for rank progression
            hunter['gates_cleared'] = hunter.get('gates_cleared', 0) + 1
            
            # Update quest progress
            try:
                from daily_quest_system import update_quest_progress
                update_quest_progress(hunter, "clear_gates", 1)
                update_quest_progress(hunter, "earn_gold", total_gold)
            except:
                pass
            
            # Handle level up notifications
            if level_up_data.get("levels_gained", 0) > 0:
                level_ups = level_up_data["levels_gained"]
                await send_level_up_notification(ctx.author, level_up_data)
                
                # Announce rank up if applicable
                if level_up_data.get("rank_changed", False):
                    rank_up_msg = f"\n🎊 **RANK UP!** You are now {level_up_data['new_rank']}-Rank!"
            
            # Check for rank up
            try:
                from main import check_rank_up
                if check_rank_up(hunter):
                    rank_up_msg = f"\n🎊 **RANK UP!** You are now {hunter['rank']}-Rank!"
            except:
                pass
            
            # Restore some HP
            hunter['hp'] = min(hunter.get('max_hp', 100), hunter['hp'] + 30)
        
        # Clean up exploration and hunter battle state
        del self.active_explorations[user_id]
        
        # Clear gate battle state from hunter
        if 'gate_battle' in hunter:
            del hunter['gate_battle']
            
        self.save_hunters_data(hunters_data)
        
        if success:
            embed = discord.Embed(
                title="🏆 Gate Exploration Completed!",
                description=f"You have successfully explored {exploration['gate_name']}!",
                color=discord.Color.gold()
            )
            
            rewards_text = f"💰 {total_gold} Gold\n⭐ {total_exp} EXP"
            if level_ups > 0:
                rewards_text += f"\n🎉 Level Up! (+{level_ups} levels)"
            rewards_text += rank_up_msg
            
            embed.add_field(name="Total Rewards", value=rewards_text, inline=True)
            embed.add_field(
                name="Floors Cleared",
                value=f"{exploration['current_floor']}/{exploration['boss_floor']}",
                inline=True
            )
        else:
            embed = discord.Embed(
                title="💀 Gate Exploration Failed",
                description=f"You were defeated in {exploration['gate_name']}.",
                color=discord.Color.red()
            )
            embed.add_field(name="No rewards gained", value="Better luck next time!", inline=False)
        
        await ctx.send(embed=embed)
        
        # Send detailed victory screen to private channel
        if success:
            # Import the completion function
            import main
            victory_data = {
                'monster_name': f"{exploration['gate_name']} (Gate Exploration)",
                'gold_gained': total_gold,
                'exp_gained': total_exp,
                'level_up_data': level_up_data if level_ups > 0 else None,
                'hunter_stats': {
                    'level': hunter['level'],
                    'hp': hunter['hp'],
                    'max_hp': hunter.get('max_hp', 100),
                    'gold': hunter['gold']
                },
                'additional_info': f"Floors Cleared: {exploration['current_floor']}/{exploration['boss_floor']}" + rank_up_msg
            }
            await main.send_combat_completion_message(user_id, victory_data)
    

    
    async def handle_boss_encounter(self, ctx, user_id, exploration):
        """Handle boss floor encounter with player choice"""
        hunters_data = self.load_hunters_data()
        hunter = hunters_data[user_id]
        
        embed = discord.Embed(
            title="⚠️ Boss Floor Reached!",
            description="You've reached the final floor and sense a powerful presence ahead.",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="Boss Encounter",
            value="A mighty boss guards the gate's exit. Choose your action:",
            inline=False
        )
        
        embed.add_field(
            name="Options",
            value="React with ⚔️ to fight the boss\nReact with 🏃 to retreat safely",
            inline=False
        )
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("⚔️")
        await message.add_reaction("🏃")
        
        def check(reaction, user):
            return user.id == ctx.author.id and str(reaction.emoji) in ["⚔️", "🏃"] and reaction.message.id == message.id
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == "⚔️":
                # Fight the boss
                await self.start_boss_battle(ctx, user_id, exploration)
            else:
                # Retreat safely
                await self.complete_gate_exploration(ctx, user_id, False)
                
        except asyncio.TimeoutError:
            # Default to retreat if no response
            await ctx.send("You hesitate too long and decide to retreat safely.")
            await self.complete_gate_exploration(ctx, user_id, False)
    
    async def start_boss_battle(self, ctx, user_id, exploration):
        """Start a boss battle"""
        hunters_data = self.load_hunters_data()
        hunter = hunters_data[user_id]
        
        # Create boss based on gate difficulty
        boss_level = exploration['difficulty'] * 2 + 5
        boss = {
            "name": f"Gate Boss",
            "level": boss_level,
            "hp": boss_level * 25,
            "attack": boss_level * 3,
            "defense": boss_level * 2
        }
        
        # Set up boss battle
        hunter['gate_battle'] = {
            "boss": boss,
            "boss_hp": boss["hp"],
            "boss_max_hp": boss["hp"],
            "exploration_id": user_id
        }
        
        self.save_hunters_data({user_id: hunter})
        
        embed = discord.Embed(
            title="⚔️ Boss Battle!",
            description=f"You face the {boss['name']} (Level {boss['level']})!",
            color=discord.Color.dark_red()
        )
        
        embed.add_field(
            name="Boss Stats",
            value=f"❤️ HP: {boss['hp']}\n⚔️ ATK: {boss['attack']}\n🛡️ DEF: {boss['defense']}",
            inline=True
        )
        
        embed.add_field(
            name="Your Stats",
            value=f"❤️ HP: {hunter['hp']}/{hunter.get('max_hp', 100)}\n⚔️ STR: {hunter['strength']}\n🏃 AGI: {hunter['agility']}",
            inline=True
        )
        
        embed.add_field(
            name="Combat Commands",
            value="Use `.attack`, `.defend`, or `.flee` to take action!",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Gates(bot))
