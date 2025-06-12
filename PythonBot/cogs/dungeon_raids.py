import discord
from discord.ext import commands
import json
import random
import asyncio

class DungeonRaids(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_raids = {}  # Store active dungeon raids
        self.dungeon_data = self.load_dungeon_data()
    
    def load_dungeon_data(self):
        """Load dungeon configuration"""
        return {
            "dungeons": {
                "Abandoned Mine": {
                    "min_level": 1,
                    "min_rank": "E",
                    "floors": 3,
                    "boss_floor": 3,
                    "base_difficulty": 10,
                    "rewards": {
                        "exp_per_floor": 50,
                        "gold_per_floor": 75,
                        "boss_exp": 200,
                        "boss_gold": 300
                    }
                },
                "Goblin Cave": {
                    "min_level": 5,
                    "min_rank": "D",
                    "floors": 4,
                    "boss_floor": 4,
                    "base_difficulty": 20,
                    "rewards": {
                        "exp_per_floor": 100,
                        "gold_per_floor": 150,
                        "boss_exp": 400,
                        "boss_gold": 600
                    }
                },
                "Demon Castle": {
                    "min_level": 25,
                    "min_rank": "C",
                    "floors": 5,
                    "boss_floor": 5,
                    "base_difficulty": 30,
                    "rewards": {
                        "exp_per_floor": 200,
                        "gold_per_floor": 300,
                        "boss_exp": 1000,
                        "boss_gold": 1500
                    }
                },
                "Red Gate Portal": {
                    "min_level": 40,
                    "min_rank": "B",
                    "floors": 10,
                    "boss_floor": 10,
                    "base_difficulty": 50,
                    "rewards": {
                        "exp_per_floor": 300,
                        "gold_per_floor": 500,
                        "boss_exp": 2000,
                        "boss_gold": 3000
                    }
                },
                "Monarch's Domain": {
                    "min_level": 90,
                    "min_rank": "S",
                    "floors": 15,
                    "boss_floor": 15,
                    "base_difficulty": 100,
                    "rewards": {
                        "exp_per_floor": 500,
                        "gold_per_floor": 800,
                        "boss_exp": 5000,
                        "boss_gold": 8000
                    }
                },
                "Red Dungeon": {
                    "min_level": 30,
                    "min_rank": "C",
                    "floors": 8,
                    "boss_floor": 8,
                    "base_difficulty": 40,
                    "special_access": "Red",
                    "rewards": {
                        "exp_per_floor": 250,
                        "gold_per_floor": 400,
                        "boss_exp": 1500,
                        "boss_gold": 2500
                    }
                },
                "Blue Dungeon": {
                    "min_level": 50,
                    "min_rank": "B",
                    "floors": 12,
                    "boss_floor": 12,
                    "base_difficulty": 60,
                    "special_access": "Blue",
                    "rewards": {
                        "exp_per_floor": 400,
                        "gold_per_floor": 600,
                        "boss_exp": 2500,
                        "boss_gold": 4000
                    }
                },
                "Gold Dungeon": {
                    "min_level": 70,
                    "min_rank": "A",
                    "floors": 20,
                    "boss_floor": 20,
                    "base_difficulty": 80,
                    "special_access": "Gold",
                    "rewards": {
                        "exp_per_floor": 600,
                        "gold_per_floor": 1000,
                        "boss_exp": 4000,
                        "boss_gold": 7000
                    }
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
    
    def get_rank_value(self, rank):
        """Convert rank to numerical value for comparison"""
        rank_values = {"E": 1, "D": 2, "C": 3, "B": 4, "A": 5, "S": 6, "National Level": 7}
        return rank_values.get(rank, 1)
    
    @commands.command(name='dungeons')
    async def list_dungeons(self, ctx):
        """Display available dungeons"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        
        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use `.start`")
            return
        
        hunter = hunters_data[user_id]
        hunter_level = hunter['level']
        hunter_rank = hunter['rank']
        hunter_rank_value = self.get_rank_value(hunter_rank)
        
        embed = discord.Embed(
            title="🏰 Available Dungeon Raids",
            description="Multi-floor dungeons with powerful bosses",
            color=discord.Color.dark_red()
        )
        
        special_access = hunter.get('special_access', {})
        special_dungeons = special_access.get('special_dungeons', [])
        
        for dungeon_name, dungeon in self.dungeon_data["dungeons"].items():
            # Check if this is a special dungeon
            is_special = dungeon.get("special_access")
            if is_special and is_special not in special_dungeons:
                continue  # Skip special dungeons without access
            
            min_rank_value = self.get_rank_value(dungeon["min_rank"])
            
            if hunter_level >= dungeon["min_level"] and hunter_rank_value >= min_rank_value:
                status = "✅ Available"
                color = "🟢"
            else:
                status = f"🔒 Requires Level {dungeon['min_level']} and {dungeon['min_rank']}-Rank"
                color = "🔴"
            
            special_tag = f" ({is_special} Special)" if is_special else ""
            dungeon_info = (f"{color} **{dungeon_name}**{special_tag}\n"
                          f"Floors: {dungeon['floors']} (Boss on floor {dungeon['boss_floor']})\n"
                          f"Difficulty: {dungeon['base_difficulty']}\n"
                          f"Requirements: Level {dungeon['min_level']}, {dungeon['min_rank']}-Rank\n"
                          f"Status: {status}\n")
            
            embed.add_field(name=f"🏰 {dungeon_name}", value=dungeon_info, inline=False)
        
        embed.set_footer(text="Use `.raid <dungeon name>` to start a dungeon raid")
        await ctx.send(embed=embed)
    
    @commands.command(name='raid')
    async def start_raid(self, ctx, *, dungeon_name):
        """Start a dungeon raid"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        
        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use `.start`")
            return
        
        hunter = hunters_data[user_id]
        
        # Check if hunter is already in any type of battle or exploration
        if hunter.get('battle') or hunter.get('gate_battle') or hunter.get('dungeon_battle') or user_id in self.active_raids:
            await ctx.send("You're already in battle or raid! Finish your current activity first.")
            return
        
        # Find the dungeon
        selected_dungeon = None
        dungeon_key = None
        for name, dungeon in self.dungeon_data["dungeons"].items():
            if name.lower() == dungeon_name.lower():
                selected_dungeon = dungeon
                dungeon_key = name
                break
        
        if not selected_dungeon:
            await ctx.send(f"Dungeon '{dungeon_name}' not found! Use `.dungeons` to see available raids.")
            return
        
        # Check requirements
        if hunter['level'] < selected_dungeon["min_level"]:
            await ctx.send(f"You need to be level {selected_dungeon['min_level']} to raid this dungeon!")
            return
        
        hunter_rank_value = self.get_rank_value(hunter['rank'])
        min_rank_value = self.get_rank_value(selected_dungeon["min_rank"])
        
        if hunter_rank_value < min_rank_value:
            await ctx.send(f"You need to be at least {selected_dungeon['min_rank']}-Rank to raid this dungeon!")
            return
        
        # Check special dungeon access
        if selected_dungeon.get("special_access"):
            special_access = hunter.get('special_access', {})
            special_dungeons = special_access.get('special_dungeons', [])
            required_access = selected_dungeon["special_access"]
            
            if required_access not in special_dungeons:
                await ctx.send(f"🔒 **Access Denied!** You need a {required_access} Dungeon Key to access this special dungeon.\nUse a {required_access} Dungeon Key with `.use Dungeon Key ({required_access})` to unlock access.")
                return
        
        # Start the raid
        raid_data = {
            "dungeon_name": dungeon_key,
            "current_floor": 1,
            "max_floors": selected_dungeon["floors"],
            "boss_floor": selected_dungeon["boss_floor"],
            "difficulty": selected_dungeon["base_difficulty"],
            "rewards": selected_dungeon["rewards"],
            "total_exp": 0,
            "total_gold": 0,
            "hunter_hp": hunter['hp'],
            "hunter_max_hp": hunter.get('max_hp', 100)
        }
        
        self.active_raids[user_id] = raid_data
        
        embed = discord.Embed(
            title=f"🏰 Entering {dungeon_key}",
            description=f"You step into the dark corridors of {dungeon_key}...",
            color=discord.Color.dark_red()
        )
        
        embed.add_field(
            name="Dungeon Info",
            value=f"Floors: {raid_data['max_floors']}\nBoss Floor: {raid_data['boss_floor']}\nDifficulty: {raid_data['difficulty']}",
            inline=True
        )
        
        embed.add_field(
            name="Your Status",
            value=f"HP: {raid_data['hunter_hp']}/{raid_data['hunter_max_hp']}\nLevel: {hunter['level']}",
            inline=True
        )
        
        await ctx.send(embed=embed)
        await asyncio.sleep(2)
        await self.process_floor(ctx, user_id)
    
    async def process_floor(self, ctx, user_id):
        """Process a single floor of the dungeon with interactive combat"""
        if user_id not in self.active_raids:
            return
        
        raid = self.active_raids[user_id]
        hunters_data = self.load_hunters_data()
        hunter = hunters_data[user_id]
        
        current_floor = raid["current_floor"]
        boss_floor = raid.get("boss_floor", raid.get("max_floors", 1))
        
        # Check if raid is complete
        if current_floor > boss_floor:
            await self.complete_raid(ctx, user_id, True)
            return
            
        is_boss_floor = current_floor == boss_floor
        dungeon_data = self.dungeon_data["dungeons"][raid["dungeon_name"]]
        
        # Generate floor monster with proper scaling and variety
        if is_boss_floor:
            # Boss monster with special abilities
            base_hp = dungeon_data["base_difficulty"] + (current_floor * 20)
            base_attack = 15 + (current_floor * 4)
            boss_names = [
                f"{raid['dungeon_name']} Lord",
                f"{raid['dungeon_name']} King", 
                f"{raid['dungeon_name']} Overlord",
                f"Ancient {raid['dungeon_name']} Guardian"
            ]
            monster_name = boss_names[hash(raid['dungeon_name']) % len(boss_names)]
            
            monster = {
                "name": monster_name,
                "hp": base_hp,
                "attack": base_attack,
                "defense": 5 + (current_floor // 2),
                "exp_reward": dungeon_data["rewards"]["boss_exp"],
                "gold_reward": dungeon_data["rewards"]["boss_gold"],
                "level": current_floor + 10,
                "abilities": ["Devastating Strike", "Fury", "Regeneration"],
                "rarity": "boss"
            }
        else:
            # Regular floor monster with scaling difficulty
            floor_multiplier = 1.15 ** (current_floor - 1)
            base_hp = int((20 + (dungeon_data["base_difficulty"] // 4)) * floor_multiplier)
            base_attack = int((6 + (current_floor * 1.5)) * floor_multiplier)
            
            monster_types = [
                "Skeleton Warrior", "Orc Berserker", "Shadow Beast", 
                "Stone Golem", "Fire Elemental", "Ice Wraith",
                "Demon Scout", "Undead Knight", "Crystal Spider"
            ]
            monster_name = f"{monster_types[(current_floor - 1) % len(monster_types)]} Lv.{current_floor + 5}"
            
            monster = {
                "name": monster_name,
                "hp": base_hp,
                "attack": base_attack,
                "defense": 2 + (current_floor // 3),
                "exp_reward": int(dungeon_data["rewards"]["exp_per_floor"] * (1 + current_floor * 0.1)),
                "gold_reward": int(dungeon_data["rewards"]["gold_per_floor"] * (1 + current_floor * 0.1)),
                "level": current_floor + 5,
                "abilities": ["Strike", "Guard"],
                "rarity": "elite" if current_floor > dungeon_data["floors"] // 2 else "common"
            }
        
        if is_boss_floor:
            # Boss encounter - ask player if they want to fight or flee
            embed = discord.Embed(
                title=f"👑 Floor {current_floor} - Boss Chamber",
                description=f"You stand before the chamber of **{monster['name']}**\n\nA powerful presence emanates from within. This is your final challenge!",
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
                    # Player chose to flee - complete raid
                    await self.complete_raid(ctx, user_id, True)
                    return
                else:
                    # Player chose to fight - start boss battle
                    hunter['dungeon_battle'] = {
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
                await ctx.send("You hesitated too long! The dungeon raid has been cancelled.")
                if user_id in self.active_raids:
                    del self.active_raids[user_id]
                return
        else:
            # Regular floor exploration - automatically proceed
            await self.explore_dungeon_floor(ctx, user_id, current_floor, raid)
            return
        
        # Create battle embed for boss fights
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        embed = discord.Embed(
            title=f"🏰 Floor {current_floor} - {monster['name']}",
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
            value=f"👹 {monster['name']}\n❤️ HP: {monster['hp']}/{monster['hp']}\n{monster_bar}\n🏷️ Level: {monster['level']} ({monster['rarity'].title()})",
            inline=True
        )
        
        embed.add_field(
            name="Combat Commands",
            value="`.attack` - Attack the enemy\n`.defend` - Reduce incoming damage\n`.flee` - Escape from battle",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def explore_dungeon_floor(self, ctx, user_id, current_floor, raid):
        """Automatically explore a regular dungeon floor"""
        hunters_data = self.load_hunters_data()
        hunter = hunters_data[user_id]
        
        import random
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        dungeon_data = self.dungeon_data["dungeons"][raid["dungeon_name"]]
        
        # Calculate exploration success chance
        hunter_power = hunter['strength'] + hunter['agility'] + hunter['intelligence'] + (hunter['level'] * 2)
        floor_difficulty = dungeon_data["base_difficulty"] + (current_floor * 5)
        success_chance = 0.65 + ((hunter_power - floor_difficulty) * 0.01)
        success_chance = max(0.25, min(0.85, success_chance))
        
        embed = discord.Embed(
            title=f"🏰 Floor {current_floor} Exploration",
            color=discord.Color(colors['accent'])
        )
        
        if random.random() < success_chance:
            # Successful exploration
            exp_gained = dungeon_data["rewards"]["exp_per_floor"] + (current_floor * 5)
            gold_gained = dungeon_data["rewards"]["gold_per_floor"] + (current_floor * 8)
            
            raid['total_exp'] = raid.get('total_exp', 0) + exp_gained
            raid['total_gold'] = raid.get('total_gold', 0) + gold_gained
            
            embed.description = f"You successfully explore floor {current_floor} of {raid['dungeon_name']}!"
            embed.color = discord.Color.green()
            embed.add_field(
                name="Floor Cleared",
                value=f"💰 {gold_gained} Gold\n⭐ {exp_gained} EXP\nAdvancing to next floor...",
                inline=False
            )
            
            # Advance to next floor
            raid['current_floor'] += 1
            await ctx.send(embed=embed)
            await asyncio.sleep(2)
            await self.process_floor(ctx, user_id)
        else:
            # Failed exploration - player takes damage
            damage = random.randint(20, 40)
            hunter['hp'] = max(0, hunter['hp'] - damage)
            
            embed.description = f"Floor {current_floor} proves treacherous!"
            embed.color = discord.Color.orange()
            embed.add_field(
                name="Exploration Result",
                value=f"💔 You took {damage} damage\n❤️ HP: {hunter['hp']}/{hunter.get('max_hp', 100)}",
                inline=False
            )
            
            if hunter['hp'] <= 0:
                # Player died - implement death penalty
                await self.handle_death(ctx, user_id, hunter, hunters_data, "dungeon exploration")
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
                        # Player chooses to retreat completely from dungeon
                        await self.complete_raid(ctx, user_id, True)
                    else:
                        # Continue exploring
                        raid['current_floor'] += 1
                        self.save_hunters_data(hunters_data)
                        await asyncio.sleep(1)
                        await self.process_floor(ctx, user_id)
                        
                except asyncio.TimeoutError:
                    await ctx.send("No response received. Retreating from dungeon...")
                    await self.complete_raid(ctx, user_id, True)
    
    async def handle_death(self, ctx, user_id, hunter, hunters_data, death_cause):
        """Handle player death with 3-minute respawn timer"""
        import time
        
        # Set death timer (3 minutes)
        death_time = time.time() + 180  # 3 minutes
        hunter['death_timer'] = death_time
        hunter['hp'] = hunter.get('max_hp', 100)  # Respawn with full health
        
        # Clear any active battles
        if 'dungeon_battle' in hunter:
            del hunter['dungeon_battle']
        
        # Remove from active raid
        if hasattr(self, 'active_raids') and user_id in self.active_raids:
            del self.active_raids[user_id]
        
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
    
    async def complete_raid(self, ctx, user_id, success):
        """Complete the dungeon raid and award rewards"""
        if user_id not in self.active_raids:
            return
        
        raid = self.active_raids[user_id]
        
        # Prevent duplicate completion calls
        if raid.get('completed', False):
            return
        raid['completed'] = True
        hunters_data = self.load_hunters_data()
        hunter = hunters_data[user_id]
        
        # Clear dungeon battle state
        if 'dungeon_battle' in hunter:
            del hunter['dungeon_battle']
        
        # Award accumulated rewards
        total_exp = raid["total_exp"]
        total_gold = raid["total_gold"]
        
        dropped_key = None
        level_ups = 0
        level_up_data = None
        
        if success and total_exp > 0:
            # Award EXP using new leveling system
            from utils.leveling_system import award_exp, send_level_up_notification
            level_up_data = await award_exp(user_id, total_exp, self.bot, "dungeon_clear")
            
            hunter['gold'] = hunter.get('gold', 0) + total_gold
            
            # Track dungeon completion for rank progression
            hunter['dungeons_cleared'] = hunter.get('dungeons_cleared', 0) + 1
            
            # Check for rare dungeon key drops
            from daily_quest_system import add_dungeon_key_drop
            dropped_key = add_dungeon_key_drop(hunter, hunter.get('rank', 'E'))
            
            # Handle level up notifications
            if level_up_data.get("levels_gained", 0) > 0:
                level_ups = level_up_data["levels_gained"]
                await send_level_up_notification(ctx.author, level_up_data)
            
            # Restore some HP
            hunter['hp'] = min(hunter.get('max_hp', 100), hunter['hp'] + 50)
        
        # Clean up raid
        del self.active_raids[user_id]
        self.save_hunters_data(hunters_data)
        
        if success:
            key_message = ""
            if dropped_key:
                key_message = f"\n🗝️ **RARE DROP:** {dropped_key}!"
            
            embed = discord.Embed(
                title="🏆 Dungeon Raid Completed!",
                description=f"You have successfully raided {raid['dungeon_name']}!{key_message}",
                color=discord.Color.gold()
            )
            
            rewards_text = f"💰 {total_gold} Gold\n⭐ {total_exp} EXP"
            if level_ups > 0:
                rewards_text += f"\n🎉 Level Up! (+{level_ups} levels)"
            
            embed.add_field(name="Total Rewards", value=rewards_text, inline=True)
            embed.add_field(
                name="Floors Cleared",
                value=f"{raid['current_floor'] - 1}/{raid['max_floors']}",
                inline=True
            )
        else:
            embed = discord.Embed(
                title="💀 Raid Failed",
                description=f"You were defeated in {raid['dungeon_name']}.",
                color=discord.Color.red()
            )
            embed.add_field(name="No rewards gained", value="Better luck next time!", inline=False)
        
        await ctx.send(embed=embed)
        
        # Send detailed victory screen to private channel
        if success:
            # Import the completion function
            import main
            victory_data = {
                'monster_name': f"{raid['dungeon_name']} (Dungeon Raid)",
                'gold_gained': total_gold,
                'exp_gained': total_exp,
                'level_up_data': level_up_data if level_ups > 0 else None,
                'hunter_stats': {
                    'level': hunter['level'],
                    'hp': hunter['hp'],
                    'max_hp': hunter.get('max_hp', 100),
                    'gold': hunter['gold']
                },
                'additional_info': f"Floors Cleared: {raid['current_floor'] - 1}/{raid['max_floors']}" + (f"\n🗝️ Rare Drop: {dropped_key}" if dropped_key else "")
            }
            await main.send_combat_completion_message(user_id, victory_data)

async def setup(bot):
    await bot.add_cog(DungeonRaids(bot))
