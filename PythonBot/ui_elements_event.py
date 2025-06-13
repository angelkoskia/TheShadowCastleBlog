import discord
from discord.ui import View, Button
import json
import random
import asyncio
from datetime import datetime
from utils.leveling_system import award_exp
from utils.theme_utils import get_user_theme_colors, get_info_embed

class EventCombatView(View):
    """Shared combat view for event boss encounters with multiple participants"""
    
    def __init__(self, ctx, event_id, active_event_battles):
        super().__init__(timeout=300)  # 5 minute timeout for boss battles
        self.ctx = ctx
        self.event_id = event_id
        self.active_event_battles = active_event_battles
        self.combat_message = None
        
        # Add combat buttons
        self.add_combat_buttons()

    def load_hunters_data(self):
        """Load hunter data from JSON file"""
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_hunters_data(self, data):
        """Save hunter data to JSON file"""
        try:
            with open('hunters_data.json', 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving hunters data: {e}")

    async def on_timeout(self):
        """Handle view timeout"""
        event_state = self.active_event_battles.get(self.event_id)
        if event_state and event_state['combat_message']:
            for item in self.children:
                item.disabled = True
            await event_state['combat_message'].edit(content="Event combat timed out.", view=self)
            await self.end_event_battle("timeout")

    def get_combat_embed(self):
        """Generate the shared combat embed showing boss and all participants"""
        event_state = self.active_event_battles.get(self.event_id)
        if not event_state:
            return get_info_embed("Error", "Event not found or ended.", discord.Color.red())

        boss_data = event_state['boss_data']
        current_boss_hp = event_state['current_boss_hp']
        max_boss_hp = boss_data['hp']
        
        # Calculate boss HP bar
        hp_percentage = (current_boss_hp / max_boss_hp) * 100
        hp_bar = "█" * int(hp_percentage / 10) + "░" * (10 - int(hp_percentage / 10))

        embed = discord.Embed(
            title=f"💥 Event Boss: {boss_data['name']} 💥",
            description=f"**Boss HP:** {hp_bar} {current_boss_hp}/{max_boss_hp}",
            color=discord.Color.red()
        )

        # Display participant information
        participants_info = []
        for user_id, hunter in event_state['participants'].items():
            hunter_hp_percentage = (hunter['hp'] / hunter.get('max_hp', 1)) * 100
            hunter_hp_bar = "█" * int(hunter_hp_percentage / 10) + "░" * (10 - int(hunter_hp_percentage / 10))
            status_icon = "💀" if hunter['hp'] <= 0 else "⚔️"
            participants_info.append(f"{status_icon} <@{user_id}>: ❤️ {hunter['hp']}/{hunter.get('max_hp', 100)} ✨ {hunter.get('mana', 0)}/{hunter.get('max_mana', 100)}")
        
        if participants_info:
            embed.add_field(name="Battle Participants", value="\n".join(participants_info), inline=False)
        else:
            embed.add_field(name="Battle Participants", value="No hunters in battle yet!", inline=False)

        # Add boss abilities or status effects
        if boss_data.get('abilities'):
            embed.add_field(name="Boss Abilities", value=", ".join(boss_data['abilities'][:3]), inline=True)

        embed.set_footer(text=f"Event ID: {self.event_id} | Use buttons to take action!")
        return embed

    def add_combat_buttons(self):
        """Add combat action buttons"""
        self.clear_items()
        
        event_state = self.active_event_battles.get(self.event_id)
        if not event_state:
            return

        # Core combat buttons
        attack_button = Button(label="⚔️ Attack", style=discord.ButtonStyle.danger, custom_id="event_attack")
        attack_button.callback = self.attack_callback
        self.add_item(attack_button)

        defend_button = Button(label="🛡️ Defend", style=discord.ButtonStyle.primary, custom_id="event_defend")
        defend_button.callback = self.defend_callback
        self.add_item(defend_button)

        flee_button = Button(label="🏃 Flee Event", style=discord.ButtonStyle.secondary, custom_id="event_flee")
        flee_button.callback = self.flee_callback
        self.add_item(flee_button)

        # Special ability button
        ability_button = Button(label="⚡ Special", style=discord.ButtonStyle.blurple, custom_id="event_ability")
        ability_button.callback = self.ability_callback
        self.add_item(ability_button)

    async def update_combat_ui(self):
        """Update the shared combat interface"""
        event_state = self.active_event_battles.get(self.event_id)
        if not event_state or not event_state['combat_message']:
            return

        self.add_combat_buttons()
        try:
            await event_state['combat_message'].edit(embed=self.get_combat_embed(), view=self)
        except discord.NotFound:
            # Message was deleted, create new one
            new_message = await event_state['combat_message'].channel.send(embed=self.get_combat_embed(), view=self)
            event_state['combat_message'] = new_message
        except Exception as e:
            print(f"Error updating combat UI: {e}")

    async def attack_callback(self, interaction: discord.Interaction):
        """Handle attack button press"""
        user_id = str(interaction.user.id)
        event_state = self.active_event_battles.get(self.event_id)
        
        if not event_state:
            await interaction.response.send_message("This event has ended or is not active.", ephemeral=True)
            return
            
        if user_id not in event_state['participants']:
            await interaction.response.send_message("You are not part of this event!", ephemeral=True)
            return

        hunters_data = self.load_hunters_data()
        hunter = hunters_data.get(user_id, {})
        boss_data = event_state['boss_data']
        
        if hunter.get('hp', 0) <= 0:
            await interaction.response.send_message("You are defeated and cannot attack!", ephemeral=True)
            return

        # Calculate player damage
        base_attack = hunter.get('attack', 10)
        damage_dealt = max(1, random.randint(int(base_attack * 0.8), int(base_attack * 1.2)) - boss_data.get('defense', 0))
        event_state['current_boss_hp'] -= damage_dealt
        event_state['current_boss_hp'] = max(0, event_state['current_boss_hp'])

        # Boss counter-attack on the attacker
        boss_damage = max(1, random.randint(int(boss_data['attack'] * 0.8), int(boss_data['attack'] * 1.2)) - hunter.get('defense', 0))
        hunter['hp'] -= boss_damage
        hunter['hp'] = max(0, hunter['hp'])

        # Update hunter data
        hunters_data[user_id] = hunter
        event_state['participants'][user_id] = hunter
        self.save_hunters_data(hunters_data)

        # Provide individual feedback
        feedback_message = f"You attacked {boss_data['name']} for **{damage_dealt}** damage!"
        if hunter['hp'] > 0:
            feedback_message += f"\n{boss_data['name']} retaliated for **{boss_damage}** damage. Your HP: {hunter['hp']}/{hunter.get('max_hp', 100)}"
        else:
            feedback_message += f"\n{boss_data['name']} retaliated for **{boss_damage}** damage. You were defeated!"

        await interaction.response.send_message(feedback_message, ephemeral=True)

        # Check victory/defeat conditions
        if event_state['current_boss_hp'] <= 0:
            await self.end_event_battle("victory")
        elif all(p.get('hp', 0) <= 0 for p in event_state['participants'].values()):
            await self.end_event_battle("defeat")
        else:
            await self.update_combat_ui()

    async def defend_callback(self, interaction: discord.Interaction):
        """Handle defend button press"""
        user_id = str(interaction.user.id)
        event_state = self.active_event_battles.get(self.event_id)
        
        if not event_state:
            await interaction.response.send_message("This event has ended or is not active.", ephemeral=True)
            return
            
        if user_id not in event_state['participants']:
            await interaction.response.send_message("You are not part of this event!", ephemeral=True)
            return

        hunters_data = self.load_hunters_data()
        hunter = hunters_data.get(user_id, {})
        boss_data = event_state['boss_data']
        
        if hunter.get('hp', 0) <= 0:
            await interaction.response.send_message("You are defeated and cannot defend!", ephemeral=True)
            return

        # Defending reduces incoming damage
        boss_damage = max(1, int((random.randint(int(boss_data['attack'] * 0.8), int(boss_data['attack'] * 1.2)) - hunter.get('defense', 0)) * 0.5))
        hunter['hp'] -= boss_damage
        hunter['hp'] = max(0, hunter['hp'])

        # Small HP recovery when defending
        heal_amount = random.randint(5, 15)
        hunter['hp'] = min(hunter['hp'] + heal_amount, hunter.get('max_hp', 100))

        # Update hunter data
        hunters_data[user_id] = hunter
        event_state['participants'][user_id] = hunter
        self.save_hunters_data(hunters_data)

        feedback_message = f"You took a defensive stance and recovered **{heal_amount}** HP!"
        if boss_damage > 0:
            feedback_message += f"\n{boss_data['name']} attacked but you reduced the damage to **{boss_damage}**. Your HP: {hunter['hp']}/{hunter.get('max_hp', 100)}"

        await interaction.response.send_message(feedback_message, ephemeral=True)

        # Check defeat condition
        if all(p.get('hp', 0) <= 0 for p in event_state['participants'].values()):
            await self.end_event_battle("defeat")
        else:
            await self.update_combat_ui()

    async def flee_callback(self, interaction: discord.Interaction):
        """Handle flee button press"""
        user_id = str(interaction.user.id)
        event_state = self.active_event_battles.get(self.event_id)
        
        if not event_state:
            await interaction.response.send_message("This event has ended or is not active.", ephemeral=True)
            return
            
        if user_id not in event_state['participants']:
            await interaction.response.send_message("You are not part of this event!", ephemeral=True)
            return

        # Remove participant from event
        hunter = event_state['participants'].pop(user_id)
        
        # Apply flee penalty
        hunters_data = self.load_hunters_data()
        if user_id in hunters_data:
            hunters_data[user_id]['hp'] = max(1, hunters_data[user_id].get('hp', 100) - 20)
            self.save_hunters_data(hunters_data)

        # Remove channel permissions
        try:
            await event_state['combat_message'].channel.set_permissions(interaction.user, read_messages=False)
        except:
            pass

        await interaction.response.send_message(f"You fled the event battle and took some damage. Your HP: {hunters_data[user_id]['hp']}/{hunters_data[user_id].get('max_hp', 100)}", ephemeral=True)

        # Send message to event channel
        await event_state['combat_message'].channel.send(f"🏃 {interaction.user.mention} has fled from the battle!")

        # Check if no participants left
        if not event_state['participants']:
            await event_state['combat_message'].channel.send("All participants have fled. The event boss has escaped!")
            await self.end_event_battle("timeout")
        else:
            await self.update_combat_ui()

    async def ability_callback(self, interaction: discord.Interaction):
        """Handle special ability button press"""
        user_id = str(interaction.user.id)
        event_state = self.active_event_battles.get(self.event_id)
        
        if not event_state:
            await interaction.response.send_message("This event has ended or is not active.", ephemeral=True)
            return
            
        if user_id not in event_state['participants']:
            await interaction.response.send_message("You are not part of this event!", ephemeral=True)
            return

        hunters_data = self.load_hunters_data()
        hunter = hunters_data.get(user_id, {})
        boss_data = event_state['boss_data']
        
        if hunter.get('hp', 0) <= 0:
            await interaction.response.send_message("You are defeated and cannot use abilities!", ephemeral=True)
            return

        # Check mana cost
        mana_cost = 30
        if hunter.get('mana', 0) < mana_cost:
            await interaction.response.send_message(f"Not enough mana! You need {mana_cost} mana.", ephemeral=True)
            return

        # Use special ability
        hunter['mana'] -= mana_cost
        damage_multiplier = 2.0
        base_attack = hunter.get('attack', 10)
        damage_dealt = max(1, int((random.randint(int(base_attack * 0.8), int(base_attack * 1.2)) * damage_multiplier) - boss_data.get('defense', 0)))
        
        event_state['current_boss_hp'] -= damage_dealt
        event_state['current_boss_hp'] = max(0, event_state['current_boss_hp'])

        # Boss counter-attack
        boss_damage = max(1, random.randint(int(boss_data['attack'] * 0.8), int(boss_data['attack'] * 1.2)) - hunter.get('defense', 0))
        hunter['hp'] -= boss_damage
        hunter['hp'] = max(0, hunter['hp'])

        # Update hunter data
        hunters_data[user_id] = hunter
        event_state['participants'][user_id] = hunter
        self.save_hunters_data(hunters_data)

        feedback_message = f"You used a special ability on {boss_data['name']} for **{damage_dealt}** damage!"
        feedback_message += f"\n{boss_data['name']} retaliated for **{boss_damage}** damage."
        feedback_message += f"\nYour HP: {hunter['hp']}/{hunter.get('max_hp', 100)} | Mana: {hunter['mana']}/{hunter.get('max_mana', 100)}"

        await interaction.response.send_message(feedback_message, ephemeral=True)

        # Check victory/defeat conditions
        if event_state['current_boss_hp'] <= 0:
            await self.end_event_battle("victory")
        elif all(p.get('hp', 0) <= 0 for p in event_state['participants'].values()):
            await self.end_event_battle("defeat")
        else:
            await self.update_combat_ui()

    async def end_event_battle(self, outcome="defeat"):
        """Handle event battle conclusion"""
        event_state = self.active_event_battles.pop(self.event_id, None)
        if not event_state:
            return

        boss_data = event_state['boss_data']
        event_channel = event_state['combat_message'].channel

        # Disable all buttons
        for item in self.children:
            item.disabled = True
        if event_state['combat_message']:
            try:
                await event_state['combat_message'].edit(view=self)
            except:
                pass

        hunters_data = self.load_hunters_data()

        if outcome == "victory":
            # Victory rewards
            exp_reward = boss_data.get('exp_reward', 200)
            gold_reward = boss_data.get('gold_reward', 500)
            
            victory_embed = discord.Embed(
                title=f"🎉 VICTORY! {boss_data['name']} Defeated!",
                description=f"The mighty {boss_data['name']} has fallen to your combined efforts!",
                color=discord.Color.gold()
            )
            
            participant_rewards = []
            for user_id, participant in event_state['participants'].items():
                if user_id in hunters_data:
                    hunter = hunters_data[user_id]
                    # Award rewards
                    old_exp = hunter.get('exp', 0)
                    award_exp(hunter, exp_reward)
                    hunter['gold'] = hunter.get('gold', 0) + gold_reward
                    
                    participant_rewards.append(f"<@{user_id}>: +{exp_reward} EXP, +{gold_reward} Gold")
            
            if participant_rewards:
                victory_embed.add_field(name="🏆 Rewards", value="\n".join(participant_rewards), inline=False)
            
            await event_channel.send(embed=victory_embed)
            self.save_hunters_data(hunters_data)

        elif outcome == "defeat":
            defeat_embed = discord.Embed(
                title=f"💔 DEFEAT! {boss_data['name']} Victorious!",
                description=f"Your party was defeated by the mighty {boss_data['name']}!",
                color=discord.Color.red()
            )
            
            # Reset HP for defeated participants
            for user_id in event_state['participants'].keys():
                if user_id in hunters_data:
                    hunters_data[user_id]['hp'] = hunters_data[user_id].get('max_hp', 100)
            
            await event_channel.send(embed=defeat_embed)
            self.save_hunters_data(hunters_data)

        elif outcome == "timeout":
            timeout_embed = discord.Embed(
                title=f"⌛ Event Timeout",
                description=f"The battle against {boss_data['name']} timed out. The boss escaped!",
                color=discord.Color.orange()
            )
            await event_channel.send(embed=timeout_embed)

        # Schedule channel deletion
        await asyncio.sleep(30)
        try:
            await event_channel.delete()
        except:
            pass
        
        self.stop()

class JoinEventView(View):
    """View for joining event boss encounters"""
    
    def __init__(self, event_id, boss_data, event_channel, active_event_battles):
        super().__init__(timeout=300)
        self.event_id = event_id
        self.boss_data = boss_data
        self.event_channel = event_channel
        self.active_event_battles = active_event_battles

    def load_hunters_data(self):
        """Load hunter data from JSON file"""
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    @discord.ui.button(label="Join Event", style=discord.ButtonStyle.success, emoji="⚔️")
    async def join_event_callback(self, interaction: discord.Interaction, button: Button):
        """Handle joining the event"""
        user_id = str(interaction.user.id)
        hunters_data = self.load_hunters_data()
        hunter = hunters_data.get(user_id)

        if not hunter:
            await interaction.response.send_message("You are not registered as a hunter! Use `.start` to join the battle for humanity!", ephemeral=True)
            return
            
        if hunter.get('hp', 0) <= 0:
            await interaction.response.send_message("You are defeated and cannot join the event!", ephemeral=True)
            return
            
        event_state = self.active_event_battles.get(self.event_id)
        if not event_state:
            await interaction.response.send_message("This event is no longer active!", ephemeral=True)
            return
            
        if user_id in event_state['participants']:
            await interaction.response.send_message("You have already joined this event!", ephemeral=True)
            return

        # Add user to channel permissions
        await self.event_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        
        # Add to participants
        event_state['participants'][user_id] = hunter.copy()
        
        await interaction.response.send_message(f"You have joined the **{self.boss_data['name']}** event! Check {self.event_channel.mention}", ephemeral=True)

        # Send welcome message to event channel
        welcome_embed = discord.Embed(
            title="⚔️ Hunter Joined!",
            description=f"{interaction.user.mention} has joined the battle against {self.boss_data['name']}!",
            color=discord.Color.green()
        )
        await self.event_channel.send(embed=welcome_embed)

        # Start combat if first participant
        if len(event_state['participants']) == 1 and not event_state.get('combat_message'):
            await self.start_event_combat(interaction)

    async def start_event_combat(self, interaction):
        """Start the event combat interface"""
        event_state = self.active_event_battles.get(self.event_id)
        if not event_state:
            return

        # Create the shared combat view
        combat_view = EventCombatView(interaction, self.event_id, self.active_event_battles)
        
        # Send combat message to event channel
        combat_embed = combat_view.get_combat_embed()
        event_state['combat_message'] = await self.event_channel.send(embed=combat_embed, view=combat_view)
        event_state['combat_view_instance'] = combat_view