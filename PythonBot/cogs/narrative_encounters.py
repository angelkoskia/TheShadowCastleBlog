"""
Narrative encounters cog with interactive dialogue system and monster lore progression.
"""

import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import json
import random
from typing import Dict, Any, List
from data.encounter_data import DIALOGUE_NODES, ENCOUNTERS, ENCOUNTER_ITEMS, get_monster_lore, get_encounter_by_chance
from utils.encounter_utils import (
    load_hunters_data, save_hunters_data, check_and_reset_daily_hunts,
    initialize_hunter_encounter_data, update_monster_kill_count, 
    apply_encounter_reward, get_active_encounter_buffs, reduce_encounter_buff_duration
)
from utils.dialogue_generator import generate_boss_conversation, generate_encounter_dialogue, generate_combat_taunts

class DialogueView(View):
    """Interactive dialogue view for narrative encounters"""
    
    def __init__(self, bot, ctx, hunter, current_node_id, adventure_channel):
        super().__init__(timeout=180)
        self.bot = bot
        self.ctx = ctx
        self.hunter = hunter
        self.current_node_id = current_node_id
        self.adventure_channel = adventure_channel
        self.message = None
        self.update_ui()

    async def on_timeout(self):
        """Handle dialogue timeout"""
        if self.message:
            try:
                for item in self.children:
                    item.disabled = True
                
                embed = discord.Embed(
                    title="⏰ Dialogue Timeout",
                    description="The encounter has ended due to inactivity.",
                    color=discord.Color.orange()
                )
                await self.message.edit(embed=embed, view=self)
            except:
                pass
        
        # Clear encounter state
        self.hunter['current_encounter'] = None
        hunters_data = load_hunters_data()
        user_id = str(self.ctx.author.id)
        if user_id in hunters_data:
            hunters_data[user_id] = self.hunter
            save_hunters_data(hunters_data)

    def update_ui(self):
        """Update dialogue buttons based on current node"""
        self.clear_items()
        node = DIALOGUE_NODES.get(self.current_node_id)
        
        if not node or node.get("end_encounter"):
            # End of dialogue
            self.add_item(Button(
                label="End Encounter", 
                style=discord.ButtonStyle.red, 
                custom_id="end_dialogue",
                disabled=True
            ))
            return

        # Add choice buttons
        choices = node.get("choices", [])
        for i, choice in enumerate(choices[:5]):  # Limit to 5 buttons
            style = discord.ButtonStyle.blurple
            emoji = None
            
            # Color code based on outcome type
            if choice.get("outcome_type") == "combat":
                style = discord.ButtonStyle.danger
                emoji = "⚔️"
            elif choice.get("outcome_type") == "reward":
                style = discord.ButtonStyle.success
                emoji = "💰"
            elif choice.get("outcome_type") == "flee":
                style = discord.ButtonStyle.secondary
                emoji = "🏃"
            
            self.add_item(ChoiceButton(
                label=choice["label"],
                choice_data=choice,
                choice_index=i,
                style=style,
                emoji=emoji
            ))

    async def send_dialogue_message(self):
        """Send or update dialogue message"""
        node = DIALOGUE_NODES.get(self.current_node_id)
        if not node:
            await self.adventure_channel.send("❌ Dialogue error: Node not found.")
            return

        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(str(self.ctx.author.id))
        
        embed = discord.Embed(
            title="📜 Narrative Encounter",
            description=node["text"],
            color=discord.Color(colors['primary'])
        )
        
        # Add encounter context
        embed.add_field(
            name="Hunter Status",
            value=f"Level {self.hunter.get('level', 1)} | {self.hunter.get('rank', 'E Rank')}",
            inline=True
        )
        
        # Add active buffs if any
        active_buffs = get_active_encounter_buffs(self.hunter)
        if active_buffs:
            buff_names = list(active_buffs.keys())
            embed.add_field(
                name="Active Buffs",
                value=", ".join(buff_names),
                inline=True
            )
        
        embed.set_footer(text="Choose your response carefully - actions have consequences")
        
        self.update_ui()
        
        if self.message:
            await self.message.edit(embed=embed, view=self)
        else:
            self.message = await self.adventure_channel.send(embed=embed, view=self)

class ChoiceButton(Button):
    """Individual choice button for dialogue options"""
    
    def __init__(self, label: str, choice_data: Dict, choice_index: int, **kwargs):
        super().__init__(label=label, custom_id=f"choice_{choice_index}", **kwargs)
        self.choice_data = choice_data
        self.choice_index = choice_index

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.view.ctx.author:
            await interaction.response.send_message(
                "This isn't your encounter!", 
                ephemeral=True
            )
            return

        await interaction.response.defer()
        await self.process_choice(interaction)

    async def process_choice(self, interaction: discord.Interaction):
        """Process the selected dialogue choice"""
        outcome_type = self.choice_data.get("outcome_type")
        
        # Update hunter data
        hunters_data = load_hunters_data()
        user_id = str(interaction.user.id)
        
        if outcome_type == "dialogue":
            # Continue dialogue
            self.view.current_node_id = self.choice_data["next_node"]
            self.view.hunter['current_encounter'] = {
                'type': 'dialogue', 
                'node_id': self.view.current_node_id
            }
            hunters_data[user_id] = self.view.hunter
            save_hunters_data(hunters_data)
            await self.view.send_dialogue_message()
            
        elif outcome_type == "combat":
            # Start combat encounter
            monster_id = self.choice_data["monster_id"]
            await self.start_narrative_combat(interaction, monster_id)
            
        elif outcome_type == "reward":
            # Apply rewards
            reward_message = apply_encounter_reward(self.view.hunter, self.choice_data)
            
            # Handle EXP separately through leveling system
            if 'exp' in self.choice_data:
                exp_amount = self.choice_data['exp']
                from utils.leveling_system import award_exp
                result = await award_exp(user_id, exp_amount, self.view.bot, "encounter")
                
                if result.get("levels_gained", 0) > 0:
                    reward_message += f" Level up! Now level {result['new_level']}!"
            
            # Send reward notification
            embed = discord.Embed(
                title="✅ Choice Outcome",
                description=f"{self.choice_data.get('text', 'Action completed.')}\n\n{reward_message}",
                color=discord.Color.green()
            )
            await self.view.adventure_channel.send(embed=embed)
            
            # End encounter
            await self.end_encounter(interaction)
            
        elif outcome_type in ["flee", "end"]:
            # End encounter with message
            embed = discord.Embed(
                title="📖 Encounter Ended",
                description=self.choice_data.get('text', 'The encounter has ended.'),
                color=discord.Color.blue()
            )
            await self.view.adventure_channel.send(embed=embed)
            await self.end_encounter(interaction)

    async def start_narrative_combat(self, interaction: discord.Interaction, monster_id: str):
        """Start combat from narrative choice"""
        from data.encounter_data import MONSTERS_LORE
        
        monster_data = MONSTERS_LORE.get(monster_id)
        if not monster_data:
            await interaction.followup.send("❌ Monster data not found!")
            return
        
        # Generate dynamic boss conversation
        player_rank = self.view.hunter.get('rank', 'E Rank')
        conversation = generate_boss_conversation(player_rank)
        
        # Display pre-combat dialogue
        dialogue_embed = discord.Embed(
            title=f"⚔️ Boss Encounter: {monster_data['name']}",
            description="\n".join(conversation),
            color=discord.Color.red()
        )
        await self.view.adventure_channel.send(embed=dialogue_embed)
        
        # Start combat using existing system
        from main import process_interactive_combat
        from ui_elements import CombatView
        
        # Update monster kill count and show lore
        kill_count = update_monster_kill_count(self.view.hunter, monster_id)
        lore = get_monster_lore(monster_id, kill_count)
        
        if lore:
            lore_embed = discord.Embed(
                title="📚 Monster Intelligence",
                description=lore,
                color=discord.Color.purple()
            )
            lore_embed.set_footer(text=f"Encounters with this monster: {kill_count}")
            await self.view.adventure_channel.send(embed=lore_embed)
        
        # Create combat view
        combat_view = CombatView(
            self.view.bot, 
            self.view.ctx, 
            str(interaction.user.id), 
            monster_data, 
            "narrative"
        )
        
        # Start combat
        self.view.hunter['battle'] = {
            'monster': monster_data,
            'monster_hp': monster_data['hp'],
            'turn': 1
        }
        
        # Save updated hunter data
        hunters_data = load_hunters_data()
        hunters_data[str(interaction.user.id)] = self.view.hunter
        save_hunters_data(hunters_data)
        
        # End dialogue and start combat
        await self.end_encounter(interaction)

    async def end_encounter(self, interaction: discord.Interaction):
        """End the current encounter"""
        self.view.hunter['current_encounter'] = None
        
        # Save hunter data
        hunters_data = load_hunters_data()
        user_id = str(interaction.user.id)
        hunters_data[user_id] = self.view.hunter
        save_hunters_data(hunters_data)
        
        # Disable dialogue view
        if self.view.message:
            try:
                for item in self.view.children:
                    item.disabled = True
                await self.view.message.edit(view=self.view)
            except:
                pass
        
        self.view.stop()

class NarrativeEncounters(commands.Cog):
    """Cog for managing narrative encounters and dialogue system"""
    
    def __init__(self, bot):
        self.bot = bot

    def process_encounter(self, hunter: Dict[str, Any]) -> Dict[str, Any]:
        """Process and return a random encounter"""
        # Check and reset daily hunts
        check_and_reset_daily_hunts(hunter)
        
        # Initialize encounter data if needed
        initialize_hunter_encounter_data(hunter)
        
        # Increment daily hunt count
        hunter['hunts_done_today'] = hunter.get('hunts_done_today', 0) + 1
        
        # Get random encounter
        encounter = get_encounter_by_chance()
        
        return encounter

    async def start_dialogue_encounter(self, ctx, hunter: Dict[str, Any], start_node: str, adventure_channel):
        """Start a dialogue encounter"""
        # Set encounter state
        hunter['current_encounter'] = {
            'type': 'dialogue',
            'node_id': start_node
        }
        
        # Create and send dialogue view
        dialogue_view = DialogueView(self.bot, ctx, hunter, start_node, adventure_channel)
        await dialogue_view.send_dialogue_message()
        
        return dialogue_view

    async def start_combat_encounter(self, ctx, hunter: Dict[str, Any], monster_id: str, adventure_channel):
        """Start a combat encounter with lore progression"""
        from data.encounter_data import MONSTERS_LORE
        
        monster_data = MONSTERS_LORE.get(monster_id)
        if not monster_data:
            return None
        
        # Update monster kill count and get lore
        kill_count = update_monster_kill_count(hunter, monster_id)
        lore = get_monster_lore(monster_id, kill_count)
        
        # Display monster lore
        if lore:
            lore_embed = discord.Embed(
                title="📚 Monster Intelligence",
                description=lore,
                color=discord.Color.purple()
            )
            lore_embed.set_footer(text=f"Encounters with this monster: {kill_count}")
            await adventure_channel.send(embed=lore_embed)
        
        # Generate and display boss conversation (30% chance for narrative bosses)
        if random.random() < 0.3:
            player_rank = hunter.get('rank', 'E Rank')
            conversation = generate_boss_conversation(player_rank)
            
            dialogue_embed = discord.Embed(
                title=f"💭 {monster_data['name']} speaks...",
                description="\n".join(conversation),
                color=discord.Color.red()
            )
            await adventure_channel.send(embed=dialogue_embed)
        
        return monster_data

    @commands.command(name='lore')
    async def view_monster_lore(self, ctx, *, monster_name: str = None):
        """View unlocked lore for encountered monsters"""
        user_id = str(ctx.author.id)
        hunters_data = load_hunters_data()
        
        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use `.start`")
            return
        
        hunter = hunters_data[user_id]
        monster_kills = hunter.get('monster_kills', {})
        
        from utils.theme_utils import get_user_theme_colors
        colors = get_user_theme_colors(ctx.author.id)
        
        if not monster_name:
            # Show all encountered monsters
            embed = discord.Embed(
                title="📚 Monster Codex",
                description="Monsters you've encountered and their lore progression",
                color=discord.Color(colors['primary'])
            )
            
            if not monster_kills:
                embed.add_field(
                    name="No Encounters",
                    value="You haven't encountered any monsters yet. Use `.hunt` to begin!",
                    inline=False
                )
            else:
                for monster_id, kill_count in monster_kills.items():
                    from data.encounter_data import MONSTERS_LORE
                    monster_data = MONSTERS_LORE.get(monster_id)
                    if monster_data:
                        lore_unlocked = sum(1 for lore in monster_data['lore'] if kill_count >= lore['hunts_needed'])
                        total_lore = len(monster_data['lore'])
                        
                        embed.add_field(
                            name=f"{monster_data['name']} ({monster_data['rank']} Rank)",
                            value=f"Encounters: {kill_count} | Lore: {lore_unlocked}/{total_lore}",
                            inline=True
                        )
            
            embed.set_footer(text="Use `.lore <monster name>` to view specific monster lore")
            
        else:
            # Show specific monster lore
            from data.encounter_data import MONSTERS_LORE
            
            monster_id = None
            for mid, mdata in MONSTERS_LORE.items():
                if mdata['name'].lower() == monster_name.lower():
                    monster_id = mid
                    break
            
            if not monster_id:
                await ctx.send(f"Monster '{monster_name}' not found in the database.")
                return
            
            monster_data = MONSTERS_LORE[monster_id]
            kill_count = monster_kills.get(monster_id, 0)
            
            embed = discord.Embed(
                title=f"📖 {monster_data['name']} Lore",
                description=f"**Rank:** {monster_data['rank']} | **Encounters:** {kill_count}",
                color=discord.Color(colors['accent'])
            )
            
            # Show unlocked lore entries
            unlocked_lore = []
            for lore_entry in monster_data['lore']:
                if kill_count >= lore_entry['hunts_needed']:
                    unlocked_lore.append(lore_entry)
            
            if unlocked_lore:
                current_lore = unlocked_lore[-1]['description']  # Most recent unlocked
                embed.add_field(
                    name="Current Knowledge",
                    value=current_lore,
                    inline=False
                )
                
                # Show progression
                next_unlock = None
                for lore_entry in monster_data['lore']:
                    if kill_count < lore_entry['hunts_needed']:
                        next_unlock = lore_entry
                        break
                
                if next_unlock:
                    needed = next_unlock['hunts_needed'] - kill_count
                    embed.add_field(
                        name="Next Lore Unlock",
                        value=f"Defeat {needed} more {monster_data['name']}(s)",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="Progress",
                        value="All lore unlocked! 🎉",
                        inline=True
                    )
            else:
                embed.add_field(
                    name="Unknown Monster",
                    value="You haven't encountered this monster yet. Hunt to unlock its secrets!",
                    inline=False
                )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(NarrativeEncounters(bot))