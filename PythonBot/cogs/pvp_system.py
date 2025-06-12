import discord
from discord.ext import commands
import json
import random
import asyncio

class PvPSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_battles = {}  # Store active PvP battles
    
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
    
    def calculate_power_level(self, hunter):
        """Calculate hunter's power level for PvP"""
        base_power = hunter.get('strength', 10) + hunter.get('agility', 10) + hunter.get('intelligence', 10)
        level_bonus = hunter.get('level', 1) * 5
        
        # Equipment bonuses
        equipment_bonus = 0
        equipment = hunter.get('equipment', {})
        # Note: Equipment stats would need to be calculated from items data
        # This is a simplified version
        
        return base_power + level_bonus + equipment_bonus
    
    def get_rank_from_wins(self, wins):
        """Determine PvP rank based on wins"""
        if wins >= 100:
            return "Monarch"
        elif wins >= 50:
            return "National Level"
        elif wins >= 30:
            return "S-Rank Fighter"
        elif wins >= 20:
            return "A-Rank Fighter"
        elif wins >= 10:
            return "B-Rank Fighter"
        elif wins >= 5:
            return "C-Rank Fighter"
        elif wins >= 1:
            return "D-Rank Fighter"
        else:
            return "Unranked"
    
    @commands.command(name='pvp')
    async def challenge_player(self, ctx, target: discord.Member):
        """Challenge another player to PvP"""
        hunters_data = self.load_hunters_data()
        challenger_id = str(ctx.author.id)
        target_id = str(target.id)
        
        # Check if challenger is registered
        if challenger_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use `.start`")
            return
        
        # Check if target is registered
        if target_id not in hunters_data:
            await ctx.send(f"{target.name} hasn't started their hunter journey yet!")
            return
        
        # Check if challenger can PvP (C-Rank required)
        challenger = hunters_data[challenger_id]
        if challenger.get('level', 1) < 20:
            await ctx.send("You need to be at least level 20 (C-Rank) to participate in PvP!")
            return
        
        # Check if target can PvP
        target_hunter = hunters_data[target_id]
        if target_hunter.get('level', 1) < 20:
            await ctx.send(f"{target.name} needs to be at least level 20 to participate in PvP!")
            return
        
        # Check if either player is already in battle
        if challenger.get('battle') or target_hunter.get('battle'):
            await ctx.send("One of the players is already in battle!")
            return
        
        # Check if there's already an active PvP battle
        battle_key = f"{challenger_id}_{target_id}"
        reverse_battle_key = f"{target_id}_{challenger_id}"
        
        if battle_key in self.active_battles or reverse_battle_key in self.active_battles:
            await ctx.send("There's already an active battle between these players!")
            return
        
        # Send challenge
        embed = discord.Embed(
            title="⚔️ PvP Challenge!",
            description=f"{ctx.author.mention} has challenged {target.mention} to a duel!",
            color=discord.Color.red()
        )
        
        challenger_power = self.calculate_power_level(challenger)
        target_power = self.calculate_power_level(target_hunter)
        
        embed.add_field(
            name=f"{ctx.author.name} (Level {challenger['level']})",
            value=f"Power Level: {challenger_power}\nRank: {challenger.get('rank', 'E')}",
            inline=True
        )
        
        embed.add_field(
            name=f"{target.name} (Level {target_hunter['level']})",
            value=f"Power Level: {target_power}\nRank: {target_hunter.get('rank', 'E')}",
            inline=True
        )
        
        embed.set_footer(text=f"{target.name}, react with ⚔️ to accept or ❌ to decline (30s)")
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("⚔️")
        await message.add_reaction("❌")
        
        # Wait for target's response
        def check(reaction, user):
            return (user == target and str(reaction.emoji) in ["⚔️", "❌"] and 
                   reaction.message.id == message.id)
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == "❌":
                await ctx.send(f"{target.name} declined the challenge!")
                return
            
            # Start PvP battle
            await self.start_pvp_battle(ctx, challenger_id, target_id, hunters_data)
            
        except asyncio.TimeoutError:
            await ctx.send("Challenge timed out!")
    
    async def start_pvp_battle(self, ctx, challenger_id, target_id, hunters_data):
        """Start a PvP battle between two players"""
        challenger = hunters_data[challenger_id]
        target = hunters_data[target_id]
        
        challenger_user = self.bot.get_user(int(challenger_id))
        target_user = self.bot.get_user(int(target_id))
        
        # Initialize battle state
        battle_key = f"{challenger_id}_{target_id}"
        self.active_battles[battle_key] = {
            "challenger": {
                "id": challenger_id,
                "hp": challenger.get('hp', 100),
                "max_hp": challenger.get('max_hp', 100),
                "mp": challenger.get('mp', 50),
                "max_mp": challenger.get('max_mp', 50),
                "power": self.calculate_power_level(challenger)
            },
            "target": {
                "id": target_id,
                "hp": target.get('hp', 100),
                "max_hp": target.get('max_hp', 100),
                "mp": target.get('mp', 50),
                "max_mp": target.get('max_mp', 50),
                "power": self.calculate_power_level(target)
            },
            "turn": "challenger",
            "round": 1
        }
        
        embed = discord.Embed(
            title="⚔️ PvP Battle Started!",
            description=f"{challenger_user.name} vs {target_user.name}",
            color=discord.Color.dark_red()
        )
        
        await self.update_battle_embed(ctx, battle_key, embed)
    
    async def update_battle_embed(self, ctx, battle_key, embed=None):
        """Update the battle display"""
        if battle_key not in self.active_battles:
            return
        
        battle = self.active_battles[battle_key]
        challenger_data = battle["challenger"]
        target_data = battle["target"]
        
        challenger_user = self.bot.get_user(int(challenger_data["id"]))
        target_user = self.bot.get_user(int(target_data["id"]))
        
        if not embed:
            embed = discord.Embed(
                title="⚔️ PvP Battle",
                description=f"Round {battle['round']}",
                color=discord.Color.dark_red()
            )
        
        # Health bars
        def create_health_bar(current, maximum):
            if maximum == 0:
                return "░" * 10
            percentage = current / maximum
            filled = int(percentage * 10)
            return "█" * filled + "░" * (10 - filled)
        
        challenger_hp_bar = create_health_bar(challenger_data["hp"], challenger_data["max_hp"])
        target_hp_bar = create_health_bar(target_data["hp"], target_data["max_hp"])
        
        embed.add_field(
            name=f"🔴 {challenger_user.name}",
            value=f"❤️ {challenger_hp_bar} {challenger_data['hp']}/{challenger_data['max_hp']}\n💠 MP: {challenger_data['mp']}/{challenger_data['max_mp']}",
            inline=True
        )
        
        embed.add_field(
            name=f"🔵 {target_user.name}",
            value=f"❤️ {target_hp_bar} {target_data['hp']}/{target_data['max_hp']}\n💠 MP: {target_data['mp']}/{target_data['max_mp']}",
            inline=True
        )
        
        # Determine whose turn it is
        current_player = challenger_user if battle["turn"] == "challenger" else target_user
        embed.add_field(
            name="Current Turn",
            value=f"⏰ {current_player.name}'s turn",
            inline=False
        )
        
        embed.set_footer(text="Use `.attack`, `.defend`, or `.special` for your turn")
        
        message = await ctx.send(embed=embed)
        
        # Check for winner
        if challenger_data["hp"] <= 0:
            await self.end_pvp_battle(ctx, battle_key, target_data["id"])
        elif target_data["hp"] <= 0:
            await self.end_pvp_battle(ctx, battle_key, challenger_data["id"])
    
    async def end_pvp_battle(self, ctx, battle_key, winner_id):
        """End a PvP battle and award rewards"""
        if battle_key not in self.active_battles:
            return
        
        battle = self.active_battles[battle_key]
        challenger_id = battle["challenger"]["id"]
        target_id = battle["target"]["id"]
        
        loser_id = challenger_id if winner_id == target_id else target_id
        
        # Load current data
        hunters_data = self.load_hunters_data()
        
        winner = hunters_data[winner_id]
        loser = hunters_data[loser_id]
        
        # Update PvP stats
        if 'pvp_stats' not in winner:
            winner['pvp_stats'] = {'wins': 0, 'losses': 0, 'rank': 'Unranked'}
        if 'pvp_stats' not in loser:
            loser['pvp_stats'] = {'wins': 0, 'losses': 0, 'rank': 'Unranked'}
        
        winner['pvp_stats']['wins'] += 1
        loser['pvp_stats']['losses'] += 1
        
        # Track PvP wins for hunter rank progression
        winner['pvp_wins'] = winner.get('pvp_wins', 0) + 1
        
        # Update PvP ranks
        winner['pvp_stats']['rank'] = self.get_rank_from_wins(winner['pvp_stats']['wins'])
        loser['pvp_stats']['rank'] = self.get_rank_from_wins(loser['pvp_stats']['wins'])
        
        # Award rewards
        gold_reward = random.randint(100, 300)
        exp_reward = random.randint(50, 150)
        
        winner['gold'] = winner.get('gold', 0) + gold_reward
        winner['exp'] += exp_reward
        
        self.save_hunters_data(hunters_data)
        
        # Clean up battle
        del self.active_battles[battle_key]
        
        winner_user = self.bot.get_user(int(winner_id))
        loser_user = self.bot.get_user(int(loser_id))
        
        embed = discord.Embed(
            title="🏆 PvP Battle Concluded!",
            description=f"{winner_user.name} has defeated {loser_user.name}!",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="🏆 Winner",
            value=f"{winner_user.name}\nNew Rank: {winner['pvp_stats']['rank']}\nWins: {winner['pvp_stats']['wins']}",
            inline=True
        )
        
        embed.add_field(
            name="💀 Defeated",
            value=f"{loser_user.name}\nRank: {loser['pvp_stats']['rank']}\nWins: {loser['pvp_stats']['wins']}",
            inline=True
        )
        
        embed.add_field(
            name="🎁 Rewards",
            value=f"💰 {gold_reward} Gold\n⭐ {exp_reward} EXP",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='rankings')
    async def show_rankings(self, ctx):
        """Show PvP leaderboard"""
        hunters_data = self.load_hunters_data()
        
        # Get all hunters with PvP stats
        pvp_hunters = []
        for user_id, hunter in hunters_data.items():
            if 'pvp_stats' in hunter and hunter['pvp_stats']['wins'] > 0:
                user = self.bot.get_user(int(user_id))
                if user:
                    pvp_hunters.append({
                        'name': user.name,
                        'wins': hunter['pvp_stats']['wins'],
                        'losses': hunter['pvp_stats']['losses'],
                        'rank': hunter['pvp_stats']['rank'],
                        'level': hunter.get('level', 1)
                    })
        
        # Sort by wins
        pvp_hunters.sort(key=lambda x: x['wins'], reverse=True)
        
        embed = discord.Embed(
            title="🏆 PvP Rankings",
            description="Top hunters in the PvP arena",
            color=discord.Color.gold()
        )
        
        if not pvp_hunters:
            embed.add_field(name="No Rankings", value="No hunters have participated in PvP yet!", inline=False)
        else:
            rankings_text = ""
            for i, hunter in enumerate(pvp_hunters[:10], 1):
                win_rate = (hunter['wins'] / (hunter['wins'] + hunter['losses'])) * 100
                rankings_text += f"`{i}.` **{hunter['name']}** ({hunter['rank']})\n"
                rankings_text += f"    Wins: {hunter['wins']} | Losses: {hunter['losses']} | Win Rate: {win_rate:.1f}%\n\n"
            
            embed.add_field(name="Top 10 Hunters", value=rankings_text[:1024], inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PvPSystem(bot))
