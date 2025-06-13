import discord
from discord.ext import commands
import json
from datetime import datetime

class SpecialQuests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
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
    
    @commands.command(name='special_quests', aliases=['special'])
    async def show_special_quests(self, ctx):
        """Display special quests based on owned keys"""
        user_id = str(ctx.author.id)
        
        # Check if player is resting
        from main import check_if_resting
        is_resting, rest_message = check_if_resting(user_id)
        if is_resting:
            from utils.theme_utils import get_error_embed
            embed = get_error_embed(ctx.author.id, rest_message)
            await ctx.send(embed=embed)
            return
        
        hunters_data = self.load_hunters_data()
        
        if user_id not in hunters_data:
            from utils.theme_utils import get_error_embed
            embed = get_error_embed(ctx.author.id, "You need to start your journey first! Use `.start`")
            await ctx.send(embed=embed)
            return
        
        hunter = hunters_data[user_id]
        inventory = hunter.get('inventory', {})
        
        # Get available keys
        special_keys = ["Shadow Realm Key", "Demon Castle Key", "Ice Monarch Key"]
        owned_keys = [key for key in special_keys if inventory.get(key, 0) > 0]
        
        # Get available special quests from templates
        from daily_quest_system import get_available_special_quests
        available_quest_templates = get_available_special_quests(owned_keys)
        
        # Get completed special quests from hunter data
        quests = hunter.get('quests', {})
        completed_special_quests = quests.get('special', {})
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        embed = discord.Embed(
            title="🌟 Special Grade Quests",
            description="Legendary quests that require rare keys to unlock",
            color=discord.Color(colors['accent'])
        )
        
        if not owned_keys:
            embed.add_field(
                name="🔐 No Keys Available",
                value="You need special keys to access these legendary quests.\n\n**Required Keys:**\n• Shadow Realm Key\n• Demon Castle Key\n• Ice Monarch Key\n\n*Keys can be obtained from high-level dungeon raids*",
                inline=False
            )
        else:
            # Show owned keys
            embed.add_field(
                name="🗝️ Your Keys",
                value="\n".join([f"• {key} ({inventory[key]})" for key in owned_keys]),
                inline=False
            )
            
            # Show available quests
            if available_quest_templates:
                for quest_id, quest_template in available_quest_templates.items():
                    # Check if this quest is already completed
                    completed_quest = completed_special_quests.get(quest_id, {})
                    is_completed = completed_quest.get('completed', False)
                    is_claimed = completed_quest.get('claimed', False)
                    
                    status_emoji = "✅" if is_completed else "🌟"
                    claimed_text = " (Claimed)" if is_claimed else ""
                    
                    quest_info = (f"{status_emoji} **{quest_template['name']}**{claimed_text}\n"
                                 f"{quest_template['description']}\n"
                                 f"Required: {quest_template['required_key']}\n"
                                 f"Rewards: {quest_template['reward_gold']} Gold, {quest_template['reward_exp']} EXP, {quest_template['special_reward']}")
                    
                    if is_completed:
                        quest_info += "\n**COMPLETED!**"
                    
                    embed.add_field(name=f"Quest {quest_id.replace('_', ' ').title()}", value=quest_info, inline=False)
            else:
                embed.add_field(
                    name="No Available Quests",
                    value="All special quests for your keys have been completed!",
                    inline=False
                )
        
        # Add navigation info
        embed.add_field(
            name="Other Quest Types",
            value="📋 Use `.daily_quests` for daily objectives\n📅 Use `.weekly_quests` for weekly challenges",
            inline=False
        )
        
        embed.set_footer(text="Use `.start_special_quest <name>` to begin a special quest")
        await ctx.send(embed=embed)
    
    @commands.command(name='start_special_quest')
    async def start_special_quest(self, ctx, *, quest_name: str = ""):
        """Start a special quest using a rare key"""
        user_id = str(ctx.author.id)
        
        if not quest_name:
            from utils.theme_utils import get_error_embed
            embed = get_error_embed(ctx.author.id, "Please specify a quest name!\nExample: `.start_special_quest Shadow Realm Conqueror`")
            await ctx.send(embed=embed)
            return
        
        # Check if player is resting
        from main import check_if_resting
        is_resting, rest_message = check_if_resting(user_id)
        if is_resting:
            from utils.theme_utils import get_error_embed
            embed = get_error_embed(ctx.author.id, rest_message)
            await ctx.send(embed=embed)
            return
        
        hunters_data = self.load_hunters_data()
        
        if user_id not in hunters_data:
            from utils.theme_utils import get_error_embed
            embed = get_error_embed(ctx.author.id, "You need to start your journey first! Use `.start`")
            await ctx.send(embed=embed)
            return
        
        hunter = hunters_data[user_id]
        inventory = hunter.get('inventory', {})
        
        # Get available keys
        special_keys = ["Shadow Realm Key", "Demon Castle Key", "Ice Monarch Key"]
        owned_keys = [key for key in special_keys if inventory.get(key, 0) > 0]
        
        # Get available special quests
        from daily_quest_system import get_available_special_quests
        available_quests = get_available_special_quests(owned_keys)
        
        # Find the quest by name
        target_quest = None
        quest_id = None
        for qid, quest in available_quests.items():
            if quest['name'].lower() == quest_name.lower():
                target_quest = quest
                quest_id = qid
                break
        
        if not target_quest:
            from utils.theme_utils import get_error_embed
            embed = get_error_embed(ctx.author.id, f"Quest '{quest_name}' not found or you don't have the required key!")
            await ctx.send(embed=embed)
            return
        
        # Check if already completed
        quests = hunter.get('quests', {})
        special_quests = quests.get('special', {})
        
        if quest_id in special_quests and special_quests[quest_id].get('completed', False):
            from utils.theme_utils import get_error_embed
            embed = get_error_embed(ctx.author.id, "You have already completed this special quest!")
            await ctx.send(embed=embed)
            return
        
        # Consume the key
        required_key = target_quest['required_key']
        inventory[required_key] = inventory.get(required_key, 0) - 1
        if inventory[required_key] <= 0:
            del inventory[required_key]
        
        # Complete the quest automatically (special quests are instant completion)
        special_quests[quest_id] = {
            'name': target_quest['name'],
            'description': target_quest['description'],
            'type': target_quest['type'],
            'reward_gold': target_quest['reward_gold'],
            'reward_exp': target_quest['reward_exp'],
            'special_reward': target_quest['special_reward'],
            'completed': True,
            'claimed': False
        }
        
        # Update hunter data
        if 'quests' not in hunter:
            hunter['quests'] = {}
        hunter['quests']['special'] = special_quests
        hunter['inventory'] = inventory
        
        self.save_hunters_data(hunters_data)
        
        # Create success embed
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        embed = discord.Embed(
            title=f"🌟 {target_quest['name']} Completed!",
            description="You have successfully completed the legendary quest!",
            color=discord.Color(colors['accent'])
        )
        
        embed.add_field(
            name="Quest Complete",
            value=f"{target_quest['description']}\n\n**Rewards Available:**\n• {target_quest['reward_gold']} Gold\n• {target_quest['reward_exp']} EXP\n• {target_quest['special_reward']}",
            inline=False
        )
        
        embed.add_field(
            name="Key Consumed",
            value=f"Used: {required_key}",
            inline=False
        )
        
        embed.set_footer(text="Use `.claim` to collect your rewards!")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(SpecialQuests(bot))