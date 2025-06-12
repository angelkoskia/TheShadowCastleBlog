import discord
from discord.ext import commands
import json
import random
import time
from datetime import datetime, timedelta

class Training(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.training_sessions = {}  # Track active training sessions

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

    def get_training_cost(self, stat_level, training_type):
        """Calculate training cost based on current stat level"""
        base_costs = {
            "strength": 100,
            "agility": 100,
            "intelligence": 100,
            "endurance": 150,
            "luck": 200
        }
        base_cost = base_costs.get(training_type, 100)
        # Cost increases exponentially with stat level
        return int(base_cost * (1.5 ** (stat_level // 10)))

    def get_training_duration(self, training_type):
        """Get training duration in seconds"""
        durations = {
            "strength": 180,      # 3 minutes
            "agility": 150,       # 2.5 minutes
            "intelligence": 210,  # 3.5 minutes
            "endurance": 240,     # 4 minutes
            "luck": 300          # 5 minutes
        }
        return durations.get(training_type, 180)

    def get_stat_gain(self, hunter_level, training_type):
        """Calculate stat gain based on hunter level and training type"""
        base_gains = {
            "strength": (1, 3),
            "agility": (1, 3),
            "intelligence": (1, 3),
            "endurance": (2, 5),  # Higher gains for endurance
            "luck": (1, 2)        # Lower gains for luck
        }
        
        min_gain, max_gain = base_gains.get(training_type, (1, 2))
        
        # Higher level hunters get slightly better gains
        level_bonus = min(hunter_level // 20, 2)
        return random.randint(min_gain, max_gain + level_bonus)

    @commands.command(name='train')
    async def start_training(self, ctx, training_type: str = ""):
        """Start a training session to boost stats"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        
        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use `.start`")
            return

        # Check if already training
        if user_id in self.training_sessions:
            session = self.training_sessions[user_id]
            remaining = session['end_time'] - time.time()
            if remaining > 0:
                minutes, seconds = divmod(int(remaining), 60)
                await ctx.send(f"You're already training **{session['type']}**! Time remaining: {minutes}m {seconds}s")
                return
            else:
                # Training session completed, remove it
                del self.training_sessions[user_id]

        valid_types = ["strength", "agility", "intelligence", "endurance", "luck"]
        
        if not training_type:
            from utils.theme_utils import get_user_theme_colors
            colors = get_user_theme_colors(ctx.author.id)
            
            embed = discord.Embed(
                title="🏋️ Training Facility",
                description="Choose your training focus to improve your stats",
                color=discord.Color(colors['accent'])
            )
            
            hunter = hunters_data[user_id]
            gold = hunter.get('gold', 0)
            
            embed.add_field(name="💰 Your Gold", value=f"{gold}", inline=False)
            
            for stat in valid_types:
                current_stat = hunter.get(stat, 10)
                cost = self.get_training_cost(current_stat, stat)
                duration = self.get_training_duration(stat) // 60
                
                stat_emojis = {
                    "strength": "💪",
                    "agility": "⚡",
                    "intelligence": "🧠",
                    "endurance": "❤️",
                    "luck": "🍀"
                }
                
                embed.add_field(
                    name=f"{stat_emojis[stat]} {stat.title()}",
                    value=f"Current: {current_stat}\nCost: {cost} gold\nDuration: {duration//60}m {duration%60}s",
                    inline=True
                )
            
            embed.add_field(
                name="Usage",
                value="Use `.train <type>` to start training\nExample: `.train strength`",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return

        if training_type.lower() not in valid_types:
            await ctx.send(f"Invalid training type! Choose from: {', '.join(valid_types)}")
            return

        training_type = training_type.lower()
        hunter = hunters_data[user_id]
        
        current_stat = hunter.get(training_type, 10)
        cost = self.get_training_cost(current_stat, training_type)
        duration = self.get_training_duration(training_type)
        
        if hunter.get('gold', 0) < cost:
            await ctx.send(f"Not enough gold! Training {training_type} costs {cost} gold.")
            return

        # Deduct cost and start training
        hunter['gold'] = hunter.get('gold', 0) - cost
        
        # Add training session
        self.training_sessions[user_id] = {
            'type': training_type,
            'end_time': time.time() + duration,
            'hunter_level': hunter['level']
        }
        
        self.save_hunters_data(hunters_data)
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        embed = discord.Embed(
            title="🏋️ Training Started!",
            description=f"You're now training **{training_type.title()}**",
            color=discord.Color(colors['success'])
        )
        
        minutes, seconds = divmod(duration, 60)
        embed.add_field(name="Duration", value=f"{minutes}m {seconds}s", inline=True)
        embed.add_field(name="Cost", value=f"{cost} gold", inline=True)
        embed.add_field(name="Current Stat", value=f"{current_stat}", inline=True)
        embed.add_field(
            name="Training Info",
            value="Use `.training` to check your progress\nTraining will complete automatically!",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='training')
    async def check_training(self, ctx):
        """Check current training progress"""
        user_id = str(ctx.author.id)
        
        if user_id not in self.training_sessions:
            await ctx.send("You're not currently training. Use `.train` to start!")
            return

        session = self.training_sessions[user_id]
        remaining = session['end_time'] - time.time()
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        if remaining <= 0:
            # Training completed, award stats
            hunters_data = self.load_hunters_data()
            hunter = hunters_data[user_id]
            
            stat_gain = self.get_stat_gain(session['hunter_level'], session['type'])
            old_stat = hunter.get(session['type'], 10)
            hunter[session['type']] = old_stat + stat_gain
            
            # Update total stats for power calculation
            if 'total_stats_gained' not in hunter:
                hunter['total_stats_gained'] = 0
            hunter['total_stats_gained'] += stat_gain
            
            self.save_hunters_data(hunters_data)
            del self.training_sessions[user_id]
            
            embed = discord.Embed(
                title="🎉 Training Complete!",
                description=f"Your **{session['type'].title()}** training is finished!",
                color=discord.Color(colors['success'])
            )
            
            embed.add_field(name="Stat Gained", value=f"+{stat_gain} {session['type'].title()}", inline=True)
            embed.add_field(name="New Total", value=f"{hunter[session['type']]}", inline=True)
            embed.add_field(name="Training Again", value="You can start a new training session!", inline=False)
            
            await ctx.send(embed=embed)
        else:
            # Training in progress
            minutes, seconds = divmod(int(remaining), 60)
            total_duration = self.get_training_duration(session['type'])
            progress = ((total_duration - remaining) / total_duration) * 100
            
            embed = discord.Embed(
                title="🏋️ Training in Progress",
                description=f"Training **{session['type'].title()}**",
                color=discord.Color(colors['accent'])
            )
            
            # Create progress bar
            bar_length = 10
            filled = int((progress / 100) * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            embed.add_field(name="Progress", value=f"{bar} {progress:.1f}%", inline=False)
            embed.add_field(name="Time Remaining", value=f"{minutes}m {seconds}s", inline=True)
            embed.add_field(name="Training Type", value=session['type'].title(), inline=True)
            
            await ctx.send(embed=embed)

    @commands.command(name='training_stats', aliases=['tstats'])
    async def show_training_stats(self, ctx):
        """Show detailed training statistics"""
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        
        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use `.start`")
            return

        hunter = hunters_data[user_id]
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        embed = discord.Embed(
            title="📊 Training Statistics",
            description="Your current training capabilities and costs",
            color=discord.Color(colors['accent'])
        )
        
        stats = ["strength", "agility", "intelligence", "endurance", "luck"]
        stat_emojis = {
            "strength": "💪",
            "agility": "⚡", 
            "intelligence": "🧠",
            "endurance": "❤️",
            "luck": "🍀"
        }
        
        for stat in stats:
            current = hunter.get(stat, 10)
            cost = self.get_training_cost(current, stat)
            duration = self.get_training_duration(stat) // 60
            
            embed.add_field(
                name=f"{stat_emojis[stat]} {stat.title()}",
                value=f"Level: {current}\nNext Cost: {cost}g\nDuration: {duration}m",
                inline=True
            )
        
        total_gained = hunter.get('total_stats_gained', 0)
        embed.add_field(
            name="🏆 Training Summary",
            value=f"Total Stats Gained: {total_gained}\nGold Available: {hunter.get('gold', 0)}",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Training(bot))