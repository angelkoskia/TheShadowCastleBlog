import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
import json
import asyncio
import random
import time
from datetime import datetime, timedelta

def load_boss_dialogues():
    """Load boss dialogue data from JSON file"""
    try:
        with open('data/boss_dialogues.json', 'r') as f:
            return json.load(f).get('boss_dialogues', {})
    except FileNotFoundError:
        return {}

def load_event_bosses():
    """Load event boss data from JSON file"""
    try:
        with open('data/event_bosses.json', 'r') as f:
            return json.load(f).get('event_bosses', [])
    except FileNotFoundError:
        return []

class EventJoinView(discord.ui.View):
    """Advanced UI system for joining event boss encounters"""
    
    def __init__(self, event_cog, event_id):
        super().__init__(timeout=120.0)  # 2 minutes to join
        self.event_cog = event_cog
        self.event_id = event_id
        
    @discord.ui.button(label="🚀 Join Event Battle", style=discord.ButtonStyle.success, emoji="⚔️")
    async def join_event_battle(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle joining the event battle with comprehensive validation"""
        print(f"DEBUG: Join event button clicked by {interaction.user.name} ({interaction.user.id})")
        
        try:
            print(f"DEBUG: About to defer interaction...")
            await interaction.response.defer(ephemeral=True)
            print(f"DEBUG: Interaction deferred successfully")
            
            user_id = str(interaction.user.id)
            user = interaction.user
            
            # Load hunter data
            print(f"DEBUG: Loading hunter data for user {user_id}")
            hunters_data = self.event_cog.load_hunters_data()
            print(f"DEBUG: Hunter data loaded, total hunters: {len(hunters_data)}")
            
            if user_id not in hunters_data:
                print(f"DEBUG: User {user_id} not found in hunter data")
                await interaction.followup.send("❌ You need to start your journey first! Use `.start` to begin.", ephemeral=True)
                return
                
            hunter = hunters_data[user_id]
            print(f"DEBUG: Hunter found - Level: {hunter.get('level', 1)}, HP: {hunter.get('hp', 0)}")
            
            # Check if hunter is already in any battle or event
            if hunter.get('in_battle', False):
                print(f"DEBUG: User {user_id} is already in battle")
                await interaction.followup.send("❌ You are already in combat! Finish your current battle first.", ephemeral=True)
                return
            
            # Get event state
            print(f"DEBUG: Getting event state for event {self.event_id}")
            event_state = self.event_cog.bot.active_event_battles.get(self.event_id)
            if not event_state:
                print(f"ERROR: Event state not found for {self.event_id}")
                await interaction.followup.send("❌ This event is no longer active!", ephemeral=True)
                return
            
            boss_data = event_state['boss_data']
            print(f"DEBUG: Boss data retrieved: {boss_data['name']}, Level req: {boss_data.get('level_req', 0)}")
            
            # Check level requirement if exists
            if boss_data.get('level_req', 0) > hunter.get('level', 1):
                print(f"DEBUG: User level {hunter.get('level', 1)} too low for boss requirement {boss_data.get('level_req', 0)}")
                await interaction.followup.send(f"❌ You need to be level {boss_data['level_req']} or higher to challenge this boss!", ephemeral=True)
                return
            
            # Check if already participant
            if user_id in event_state['participants']:
                print(f"DEBUG: User {user_id} already participating in event {self.event_id}")
                event_channel = self.event_cog.bot.get_channel(event_state['event_channel_id'])
                await interaction.followup.send(f"✅ You are already participating in this event! Check {event_channel.mention}", ephemeral=True)
                return
            
            print(f"DEBUG: All validation checks passed, proceeding with event join")
            
            # Create private event channel if not exists
            if 'event_channel_id' not in event_state:
                print(f"DEBUG: Creating new private event channel")
                event_channel = await self.event_cog.create_private_event_channel(interaction.guild, boss_data, user)
                if not event_channel:
                    print(f"ERROR: Failed to create private event channel")
                    await interaction.followup.send("❌ Failed to create event channel. Please try again.", ephemeral=True)
                    return
                event_state['event_channel_id'] = event_channel.id
                print(f"DEBUG: Event channel created: {event_channel.name} ({event_channel.id})")
            else:
                print(f"DEBUG: Using existing event channel: {event_state['event_channel_id']}")
                event_channel = self.event_cog.bot.get_channel(event_state['event_channel_id'])
                if not event_channel:
                    print(f"ERROR: Existing event channel not found, creating new one")
                    event_channel = await self.event_cog.create_private_event_channel(interaction.guild, boss_data, user)
                    if not event_channel:
                        await interaction.followup.send("❌ Failed to create event channel. Please try again.", ephemeral=True)
                        return
                    event_state['event_channel_id'] = event_channel.id
            
            # Grant access to private event channel
            print(f"DEBUG: Granting permissions to {user.name} for channel {event_channel.name}")
            try:
                await event_channel.set_permissions(
                    user, 
                    read_messages=True, 
                    send_messages=True,
                    view_channel=True
                )
                print(f"DEBUG: Permissions granted successfully")
            except Exception as e:
                print(f"ERROR: Failed to grant channel permissions: {e}")
                await interaction.followup.send(f"❌ Failed to grant channel access: {str(e)}", ephemeral=True)
                return
            
            # Add participant to event
            print(f"DEBUG: Adding participant to event")
            event_state['participants'][user_id] = {
                'user': user,
                'hunter_data': hunter.copy(),
                'hp': hunter.get('hp', hunter.get('max_hp', 100)),
                'max_hp': hunter.get('max_hp', 100),
                'mana': hunter.get('mp', hunter.get('max_mp', 50)),
                'max_mana': hunter.get('max_mp', 50),
                'joined_at': datetime.now()
            }
            print(f"DEBUG: Participant added, total participants: {len(event_state['participants'])}")
            
            # Mark hunter as in event battle
            hunter['in_battle'] = True
            hunter['battle_type'] = 'event_boss'
            hunter['event_id'] = self.event_id
            hunters_data[user_id] = hunter
            self.event_cog.save_hunters_data(hunters_data)
            print(f"DEBUG: Hunter data saved with event battle state")
            
            # Update global event state
            self.event_cog.bot.active_event_battles[self.event_id] = event_state
            print(f"DEBUG: Event state updated")
        
            # Send redirection message to user
            try:
                await interaction.followup.send(
                    f"⚔️ **You have joined the event battle!**\n\n"
                    f"🔗 Go to your private event channel: {event_channel.mention}\n"
                    f"💭 The {boss_data['name']} awaits you there...",
                    ephemeral=True
                )
                print(f"DEBUG: Redirection message sent to user {user.name}")
            except Exception as e:
                print(f"ERROR: Failed to send redirection message: {e}")
            
            # Send welcome message to event channel
            try:
                welcome_embed = discord.Embed(
                    title=f"⚔️ {boss_data['name']} Event Battle",
                    description=f"Welcome {user.mention}! You have entered the battle against **{boss_data['name']}**.",
                    color=discord.Color.gold()
                )
                welcome_embed.add_field(
                    name="Boss Info",
                    value=f"**HP:** {boss_data['hp']:,}\n**Attack:** {boss_data['attack']}\n**Defense:** {boss_data['defense']}",
                    inline=True
                )
                welcome_embed.add_field(
                    name="⚔️ Hunter Status",
                    value=f"**Level:** {hunter.get('level', 1)}\n**HP:** {hunter.get('hp', 100)}/{hunter.get('max_hp', 100)}\n**Attack:** {hunter.get('attack', 25)}",
                    inline=True
                )
                await event_channel.send(embed=welcome_embed)
                print(f"DEBUG: Welcome message sent to event channel {event_channel.id}")
            except Exception as e:
                print(f"ERROR: Failed to send welcome message to event channel: {e}")
            
            # Check if boss has dialogue or goes straight to combat
            dialogue_data = load_boss_dialogues()
            boss_id = boss_data.get('id', boss_data['name'].lower().replace(' ', '_'))
            
            if boss_id in dialogue_data and 'encounter_intro' in dialogue_data[boss_id]:
                # Boss has introductory dialogue - display it before combat
                print(f"DEBUG: Boss {boss_data['name']} has encounter dialogue")
                try:
                    intro_dialogue = random.choice(dialogue_data[boss_id]['encounter_intro'])
                    dialogue_embed = discord.Embed(
                        title=f"💬 {boss_data['name']} speaks...",
                        description=f"\"{intro_dialogue}\"",
                        color=discord.Color.dark_purple()
                    )
                    dialogue_embed.set_footer(text="Combat will begin shortly...")
                    
                    await event_channel.send(embed=dialogue_embed)
                    await asyncio.sleep(3)  # Brief pause for dramatic effect
                    print(f"DEBUG: Intro dialogue sent for {boss_data['name']}")
                    
                    # Send combat start message if available
                    if 'combat_start' in dialogue_data[boss_id]:
                        combat_start_msg = dialogue_data[boss_id]['combat_start']
                        start_embed = discord.Embed(
                            title="⚔️ Combat Begins!",
                            description=f"**{boss_data['name']}:** \"{combat_start_msg}\"",
                            color=discord.Color.red()
                        )
                        await event_channel.send(embed=start_embed)
                        await asyncio.sleep(2)
                    
                    await self.event_cog.start_event_combat(self.event_id)
                    print(f"DEBUG: Combat started after dialogue for {boss_data['name']}")
                except Exception as e:
                    print(f"ERROR: Failed to send boss dialogue: {e}")
                    # Fall back to direct combat if dialogue fails
                    await self.event_cog.start_event_combat(self.event_id)
            else:
                # Start combat immediately if this is the first participant or minimum reached
                if len(event_state['participants']) >= self.event_cog.MIN_PARTICIPANTS and not event_state.get('combat_started', False):
                    print(f"DEBUG: Starting direct combat for {boss_data['name']} (no dialogue)")
                    await self.event_cog.start_event_combat(self.event_id)
                    
        except Exception as e:
            print(f"CRITICAL ERROR in join_event_battle: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.followup.send("❌ An unexpected error occurred while joining the event. Please try again.", ephemeral=True)
            except:
                pass

    async def on_timeout(self):
        """Handle view timeout - disable join button"""
        for item in self.children:
            item.disabled = True
        
        # Update the announcement message to show timeout
        event_state = self.event_cog.bot.active_event_battles.get(self.event_id)
        if event_state and event_state.get('announcement_message'):
            try:
                timeout_embed = discord.Embed(
                    title="⏰ Event Join Period Ended",
                    description="The join period for this event has ended. Combat may still be in progress.",
                    color=discord.Color.orange()
                )
                await event_state['announcement_message'].edit(embed=timeout_embed, view=self)
            except discord.errors.NotFound:
                pass
        self.stop()

class EventCombatView(discord.ui.View):
    """Advanced combat UI for event boss battles"""
    
    def __init__(self, event_cog, event_id):
        super().__init__(timeout=300.0)  # 5 minute combat inactivity timeout
        self.event_cog = event_cog
        self.event_id = event_id
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only participants can interact"""
        event_state = self.event_cog.bot.active_event_battles.get(self.event_id)
        if not event_state:
            return False
        return str(interaction.user.id) in event_state['participants']
    
    def get_combat_embed(self):
        """Generate dynamic combat status embed"""
        event_state = self.event_cog.bot.active_event_battles.get(self.event_id)
        if not event_state:
            return discord.Embed(title="❌ Event Error", description="Event data not found.", color=discord.Color.red())
        
        boss_data = event_state['boss_data']
        current_boss_hp = event_state['current_boss_hp']
        max_boss_hp = boss_data['hp']
        
        # Create HP bar
        hp_percentage = (current_boss_hp / max_boss_hp) * 100
        hp_bar_length = 20
        filled_bars = int((current_boss_hp / max_boss_hp) * hp_bar_length)
        hp_bar = "█" * filled_bars + "░" * (hp_bar_length - filled_bars)
        
        embed = discord.Embed(
            title=f"⚔️ EVENT BOSS: {boss_data['name']}",
            description=f"*{boss_data.get('description', 'A powerful enemy has appeared!')}*",
            color=discord.Color.dark_red()
        )
        
        embed.add_field(
            name="💀 Boss Status",
            value=f"**HP:** {hp_bar}\n`{current_boss_hp:,} / {max_boss_hp:,} HP ({hp_percentage:.1f}%)`",
            inline=False
        )
        
        # Participant status
        participants_info = []
        for user_id, participant in event_state['participants'].items():
            hp_pct = (participant['hp'] / participant['max_hp']) * 100
            status_icon = "💚" if hp_pct > 50 else "💛" if hp_pct > 20 else "❤️"
            participants_info.append(f"{status_icon} <@{user_id}>: {participant['hp']}/{participant['max_hp']} HP")
        
        if participants_info:
            embed.add_field(
                name="👥 Active Hunters",
                value="\n".join(participants_info),
                inline=False
            )
        
        embed.add_field(
            name="🎯 Combat Actions",
            value="Use the buttons below to battle the boss!",
            inline=False
        )
        
        embed.set_footer(text=f"Event ID: {self.event_id} • Timeout: 5 minutes of inactivity")
        
        if boss_data.get('image_url'):
            embed.set_thumbnail(url=boss_data['image_url'])
        
        return embed
    
    @discord.ui.button(label="⚔️ Attack", style=discord.ButtonStyle.danger)
    async def attack_boss(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle attack action"""
        await interaction.response.defer()
        
        user_id = str(interaction.user.id)
        event_state = self.event_cog.bot.active_event_battles.get(self.event_id)
        
        if not event_state:
            await interaction.followup.send("❌ Event no longer active!", ephemeral=True)
            return
        
        participant = event_state['participants'].get(user_id)
        if not participant or participant['hp'] <= 0:
            await interaction.followup.send("❌ You are defeated and cannot attack!", ephemeral=True)
            return
        
        # Load current hunter data
        hunters_data = self.event_cog.load_hunters_data()
        hunter = hunters_data.get(user_id)
        if not hunter:
            await interaction.followup.send("❌ Hunter data not found!", ephemeral=True)
            return
        
        boss_data = event_state['boss_data']
        
        # Calculate damage
        base_damage = hunter.get('attack', 25)
        damage_variance = random.uniform(0.8, 1.2)
        damage_dealt = max(1, int((base_damage * damage_variance) - boss_data.get('defense', 0)))
        
        # Apply damage to boss
        event_state['current_boss_hp'] = max(0, event_state['current_boss_hp'] - damage_dealt)
        
        # Boss counter-attack
        boss_damage = max(1, int((boss_data.get('attack', 30) * random.uniform(0.8, 1.2)) - hunter.get('defense', 15)))
        participant['hp'] = max(0, participant['hp'] - boss_damage)
        
        # Update hunter data
        hunter['hp'] = participant['hp']
        self.event_cog.save_hunters_data(hunters_data)
        
        # Combat feedback with boss dialogue
        feedback = f"⚔️ You dealt **{damage_dealt}** damage to {boss_data['name']}!"
        if participant['hp'] > 0:
            feedback += f"\n💥 {boss_data['name']} retaliated for **{boss_damage}** damage!"
            feedback += f"\n💚 Your HP: **{participant['hp']}/{participant['max_hp']}**"
        else:
            feedback += f"\n💀 You were defeated by {boss_data['name']}'s counter-attack!"
        
        # Add random boss combat dialogue
        dialogue_data = load_boss_dialogues()
        boss_id = boss_data.get('id', boss_data['name'].lower().replace(' ', '_'))
        if boss_id in dialogue_data and 'player_attack' in dialogue_data[boss_id]:
            boss_response = random.choice(dialogue_data[boss_id]['player_attack'])
            feedback += f"\n\n**{boss_data['name']}:** \"{boss_response}\""
        
        await interaction.followup.send(feedback, ephemeral=True)
        
        # Check victory/defeat conditions
        if event_state['current_boss_hp'] <= 0:
            await self.event_cog.end_event_battle(self.event_id, "victory")
        elif all(p['hp'] <= 0 for p in event_state['participants'].values()):
            await self.event_cog.end_event_battle(self.event_id, "defeat")
        else:
            # Update combat display
            await self.update_combat_display()
    
    @discord.ui.button(label="🛡️ Defend", style=discord.ButtonStyle.primary)
    async def defend_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle defend action"""
        await interaction.response.defer()
        
        user_id = str(interaction.user.id)
        event_state = self.event_cog.bot.active_event_battles.get(self.event_id)
        
        if not event_state:
            await interaction.followup.send("❌ Event no longer active!", ephemeral=True)
            return
        
        participant = event_state['participants'].get(user_id)
        if not participant or participant['hp'] <= 0:
            await interaction.followup.send("❌ You are defeated and cannot defend!", ephemeral=True)
            return
        
        # Load current hunter data
        hunters_data = self.event_cog.load_hunters_data()
        hunter = hunters_data.get(user_id)
        
        boss_data = event_state['boss_data']
        
        # Reduced boss damage due to defending
        boss_damage = max(1, int((boss_data.get('attack', 30) * random.uniform(0.4, 0.6)) - hunter.get('defense', 15)))
        participant['hp'] = max(0, participant['hp'] - boss_damage)
        
        # Small HP recovery for successful defense
        heal_amount = max(1, int(participant['max_hp'] * 0.05))
        participant['hp'] = min(participant['max_hp'], participant['hp'] + heal_amount)
        
        # Update hunter data
        hunter['hp'] = participant['hp']
        self.event_cog.save_hunters_data(hunters_data)
        
        feedback = f"🛡️ You successfully defended against {boss_data['name']}!"
        feedback += f"\n💥 Reduced damage taken: **{boss_damage}** damage!"
        feedback += f"\n💚 HP recovered: **+{heal_amount}** | Current HP: **{participant['hp']}/{participant['max_hp']}**"
        
        # Add random boss combat dialogue for defend action
        dialogue_data = load_boss_dialogues()
        boss_id = boss_data.get('id', boss_data['name'].lower().replace(' ', '_'))
        if boss_id in dialogue_data and 'player_defend' in dialogue_data[boss_id]:
            boss_response = random.choice(dialogue_data[boss_id]['player_defend'])
            feedback += f"\n\n**{boss_data['name']}:** \"{boss_response}\""
        
        await interaction.followup.send(feedback, ephemeral=True)
        
        # Check if all participants defeated
        if all(p['hp'] <= 0 for p in event_state['participants'].values()):
            await self.event_cog.end_event_battle(self.event_id, "defeat")
        else:
            await self.update_combat_display()
    
    @discord.ui.button(label="🏃 Flee Event", style=discord.ButtonStyle.secondary)
    async def flee_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle fleeing from event"""
        await interaction.response.defer()
        
        user_id = str(interaction.user.id)
        event_state = self.event_cog.bot.active_event_battles.get(self.event_id)
        
        if not event_state:
            await interaction.followup.send("❌ Event no longer active!", ephemeral=True)
            return
        
        # Remove participant from event
        if user_id in event_state['participants']:
            del event_state['participants'][user_id]
        
        # Reset hunter battle status
        hunters_data = self.event_cog.load_hunters_data()
        hunter = hunters_data.get(user_id)
        if hunter:
            hunter['in_battle'] = False
            hunter.pop('battle_type', None)
            hunter.pop('event_id', None)
            # Apply flee penalty
            hunter['hp'] = max(1, hunter['hp'] - 20)
            self.event_cog.save_hunters_data(hunters_data)
        
        # Create flee feedback with boss dialogue
        boss_data = event_state['boss_data']
        feedback = f"🏃 You fled the event battle and took minor damage as a penalty."
        feedback += f"\n💔 HP reduced to: **{hunter['hp']}/{hunter.get('max_hp', 100)}**"
        
        # Add random boss combat dialogue for flee action
        dialogue_data = load_boss_dialogues()
        boss_id = boss_data.get('id', boss_data['name'].lower().replace(' ', '_'))
        if boss_id in dialogue_data and 'player_flee' in dialogue_data[boss_id]:
            boss_response = random.choice(dialogue_data[boss_id]['player_flee'])
            feedback += f"\n\n**{boss_data['name']}:** \"{boss_response}\""
        
        await interaction.followup.send(feedback, ephemeral=True)
        
        # Check if no participants left
        if not event_state['participants']:
            await self.event_cog.end_event_battle(self.event_id, "timeout")
        else:
            await self.update_combat_display()
    
    async def update_combat_display(self):
        """Update the combat embed and view"""
        event_state = self.event_cog.bot.active_event_battles.get(self.event_id)
        if not event_state or not event_state.get('combat_message'):
            return
        
        try:
            await event_state['combat_message'].edit(embed=self.get_combat_embed(), view=self)
        except discord.errors.NotFound:
            print(f"Combat message for event {self.event_id} not found.")
            self.stop()
    
    async def on_timeout(self):
        """Handle combat timeout"""
        await self.event_cog.end_event_battle(self.event_id, "timeout")
        self.stop()

class EventManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Initialize active event battles tracking
        if not hasattr(bot, 'active_event_battles'):
            bot.active_event_battles = {}
        
        # Event configuration
        self.EVENT_JOIN_TIMEOUT = 120  # 2 minutes for users to join
        self.MIN_PARTICIPANTS = 1  # Minimum participants needed
        self.EVENT_DURATION = 900  # 15 minutes max event duration
        self.SYSTEM_CHANNEL_ID = 1381439963656355849  # announcements channel
        self.PRIVATE_EVENT_CATEGORY_ID = 1382529024022155274  # Private Events category
        
        # Weekend double EXP configuration
        self.weekend_exp_multiplier = 2.0
        self.weekend_days = [5, 6]  # Saturday (5) and Sunday (6) in weekday() format
        self.double_exp_active = False
        
        # Start weekend monitoring
        self.weekend_exp_monitor.start()
        
        # Event boss data
        self.event_bosses = {
            "shadow_monarch": {
                "id": "shadow_monarch",
                "name": "Shadow Monarch's Champion",
                "description": "A legendary shadow warrior blessed by Ashborn himself. Only appears during times of heightened magical energy.",
                "hp": 8000,
                "max_hp": 8000,
                "attack": 300,
                "defense": 150,
                "level_req": 20,
                "exp_reward": 2500,
                "gold_reward": 2000,
                "exclusive_equipment": True,
                "weekend_only": True
            },
            "kamish_heir": {
                "id": "kamish_heir", 
                "name": "Kamish's Heir",
                "description": "A young dragon carrying the bloodline of the legendary Kamish. Only the strongest hunters dare face this descendant.",
                "hp": 12000,
                "max_hp": 12000,
                "attack": 400,
                "defense": 200,
                "level_req": 25,
                "exp_reward": 4000,
                "gold_reward": 3500,
                "exclusive_equipment": True,
                "weekend_only": True
            },
            "architect_guardian": {
                "id": "architect_guardian",
                "name": "Architect's Guardian",
                "description": "A powerful construct created by the System's Architect to test the worthiest hunters.",
                "hp": 15000,
                "max_hp": 15000,
                "attack": 500,
                "defense": 250,
                "level_req": 30,
                "exp_reward": 6000,
                "gold_reward": 5000,
                "exclusive_equipment": True,
                "weekend_only": True
            },
            "crimson_drake": {
                "id": "crimson_drake",
                "name": "Crimson Drake",
                "description": "A fierce dragon consumed by eternal flames, seeking vengeance against all hunters.",
                "hp": 5000,
                "max_hp": 5000,
                "attack": 200,
                "defense": 100,
                "level_req": 15,
                "exp_reward": 1500,
                "gold_reward": 1000,
                "exclusive_equipment": False,
                "weekend_only": False
            },
            "ice_monarch": {
                "id": "ice_monarch",
                "name": "Ice Monarch",
                "description": "An ancient ruler of the frozen realms, wielding the power of eternal winter.",
                "hp": 3000,
                "max_hp": 3000,
                "attack": 150,
                "defense": 75,
                "level_req": 10,
                "exp_reward": 800,
                "gold_reward": 500,
                "exclusive_equipment": False,
                "weekend_only": False,
                "dialogue_trigger": "ice_monarch_encounter"
            },
            "shadow_beast": {
                "id": "shadow_beast",
                "name": "Shadow Beast",
                "description": "A corrupted creature from the shadow realm, perfect for testing new hunters.",
                "hp": 2000,
                "max_hp": 2000,
                "attack": 100,
                "defense": 50,
                "level_req": 5,
                "exp_reward": 400,
                "gold_reward": 300,
                "exclusive_equipment": False,
                "weekend_only": False
            }
        }
        
        # Exclusive equipment that only drops from weekend bosses
        self.exclusive_equipment = {
            "legendary_weapons": [
                {
                    "name": "Jinwoo's Shadow Blade",
                    "type": "weapon",
                    "rarity": "legendary",
                    "attack": 350,
                    "description": "A blade forged from pure shadow energy",
                    "special_effects": ["Shadow Strike: 25% chance for double damage", "Monarch's Blessing: +50% EXP gain"]
                },
                {
                    "name": "Kamish's Wrath",
                    "type": "weapon", 
                    "rarity": "legendary",
                    "attack": 400,
                    "description": "The crystallized fury of the Dragon King",
                    "special_effects": ["Dragon's Breath: Area damage", "Fire Immunity"]
                },
                {
                    "name": "Ruler's Authority",
                    "type": "weapon",
                    "rarity": "mythic",
                    "attack": 500,
                    "description": "A weapon imbued with the power of the Rulers",
                    "special_effects": ["Divine Strike: Ignores all defense", "Reality Manipulation: 10% instant kill"]
                }
            ]
        }

    def load_hunters_data(self):
        """Load hunter data from JSON file"""
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_hunters_data(self, data):
        """Save hunter data to JSON file with custom encoder"""
        try:
            import json
            
            class CustomEncoder(json.JSONEncoder):
                def default(self, o):
                    if hasattr(o, 'value'):  # Discord Color objects
                        return o.value
                    if hasattr(o, '__dict__'):
                        return o.__dict__
                    return str(o)
            
            with open('hunters_data.json', 'w') as f:
                json.dump(data, f, indent=4, cls=CustomEncoder)
        except Exception as e:
            print(f"Error saving hunters data: {e}")

    def is_weekend(self):
        """Check if current day is weekend"""
        current_day = datetime.now().weekday()
        return current_day in self.weekend_days

    def get_exp_multiplier(self):
        """Get current EXP multiplier based on weekend status"""
        if self.is_weekend():
            self.double_exp_active = True
            return self.weekend_exp_multiplier
        else:
            self.double_exp_active = False
            return 1.0

    async def create_private_event_channel(self, guild, boss_data, user):
        """Create private event channel with restricted access and comprehensive debugging"""
        try:
            print(f"DEBUG: create_private_event_channel called for user {user.name} ({user.id})")
            
            # Get or create event category
            event_category = discord.utils.get(guild.categories, id=self.PRIVATE_EVENT_CATEGORY_ID)
            if not event_category:
                print(f"DEBUG: Event category not found, creating new one")
                event_category = await guild.create_category(
                    "Event Chambers",
                    overwrites={
                        guild.default_role: discord.PermissionOverwrite(read_messages=False)
                    }
                )
                print(f"DEBUG: Created event category: {event_category.name} ({event_category.id})")
            else:
                print(f"DEBUG: Found existing event category: {event_category.name} ({event_category.id})")

            # Generate unique channel name
            timestamp = int(time.time())
            channel_name = f"event-{boss_data['name'].lower().replace(' ', '-')}-{user.name.lower().replace(' ', '-')}-{timestamp}"
            print(f"DEBUG: Generated channel name: {channel_name}")

            # Create explicit permission overwrites
            overwrites = {
                # Hide from everyone by default
                guild.default_role: discord.PermissionOverwrite(
                    read_messages=False,
                    send_messages=False,
                    view_channel=False
                ),
                # Give bot full permissions
                guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    embed_links=True,
                    add_reactions=True,
                    view_channel=True,
                    manage_channels=True,
                    manage_permissions=True
                ),
                # Give specific user access
                user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    view_channel=True,
                    embed_links=True,
                    add_reactions=True
                )
            }
            
            print(f"DEBUG: Permission overwrites configured for {len(overwrites)} entities")

            # Create the channel
            print(f"DEBUG: Creating text channel in category {event_category.name}")
            event_channel = await guild.create_text_channel(
                name=channel_name,
                category=event_category,
                overwrites=overwrites,
                topic=f"Private event battle against {boss_data['name']} for {user.name}"
            )
            
            print(f"DEBUG: Successfully created event channel: {event_channel.name} ({event_channel.id})")
            
            # Verify permissions were set correctly
            user_perms = event_channel.permissions_for(user)
            bot_perms = event_channel.permissions_for(guild.me)
            
            print(f"DEBUG: User permissions - read: {user_perms.read_messages}, send: {user_perms.send_messages}, view: {user_perms.view_channel}")
            print(f"DEBUG: Bot permissions - read: {bot_perms.read_messages}, send: {bot_perms.send_messages}, manage: {bot_perms.manage_messages}")

            return event_channel

        except discord.Forbidden as e:
            print(f"ERROR: Bot lacks permissions to create channel: {e}")
            print(f"DEBUG: Bot permissions in guild: {guild.me.guild_permissions}")
            return None
        except Exception as e:
            print(f"ERROR: Unexpected error creating event channel: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def start_event_combat(self, event_id):
        """Initialize combat for an event with comprehensive debugging"""
        print(f"DEBUG: start_event_combat called for event {event_id}")
        
        event_state = self.bot.active_event_battles.get(event_id)
        if not event_state:
            print(f"ERROR: No event state found for {event_id}")
            return
            
        if event_state.get('combat_started', False):
            print(f"DEBUG: Combat already started for event {event_id}")
            return

        event_state['combat_started'] = True
        event_state['combat_start_time'] = datetime.now()

        # Get event channel
        event_channel = self.bot.get_channel(event_state.get('event_channel_id'))
        if not event_channel:
            print(f"ERROR: Event channel not found for event {event_id}, channel_id: {event_state.get('event_channel_id')}")
            return

        print(f"DEBUG: Found event channel: {event_channel.name} ({event_channel.id})")

        try:
            # Create combat view and embed
            combat_view = EventCombatView(self, event_id)
            combat_embed = combat_view.get_combat_embed()
            
            print(f"DEBUG: Created combat view and embed for {event_id}")

            # Send combat message with proper error handling
            combat_message = await event_channel.send(
                "🔥 **EVENT BOSS BATTLE COMMENCING!** 🔥",
                embed=combat_embed,
                view=combat_view
            )
            
            print(f"DEBUG: Combat message sent successfully. Message ID: {combat_message.id}")

            event_state['combat_message'] = combat_message
            self.bot.active_event_battles[event_id] = event_state

            # Start global event timer
            asyncio.create_task(self.event_global_timer(event_id))
            print(f"DEBUG: Global timer started for event {event_id}")
            
        except discord.Forbidden as e:
            print(f"ERROR: Bot lacks permissions to send combat message in channel {event_channel.name}: {e}")
            await event_channel.send("❌ Error: Bot lacks permissions to start combat. Please check channel settings.", delete_after=10)
        except Exception as e:
            print(f"ERROR: Failed to start combat for event {event_id}: {e}")
            await event_channel.send(f"❌ Unexpected error starting combat: {str(e)}", delete_after=10)

    async def event_global_timer(self, event_id):
        """Global timer for event - auto-cleanup after max duration"""
        try:
            await asyncio.sleep(self.EVENT_DURATION)  # 15 minutes max
            
            event_state = self.bot.active_event_battles.get(event_id)
            if event_state:
                await self.end_event_battle(event_id, "timeout")
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error in event global timer: {e}")

    async def end_event_battle(self, event_id, outcome="defeat"):
        """End event battle and cleanup"""
        event_state = self.bot.active_event_battles.pop(event_id, None)
        if not event_state:
            return

        boss_data = event_state['boss_data']
        event_channel = self.bot.get_channel(event_state['event_channel_id'])

        # Create final message based on outcome
        if outcome == "victory":
            await self.handle_victory_rewards(event_state, event_channel)
        elif outcome == "defeat":
            await self.handle_defeat_penalties(event_state, event_channel)
        elif outcome == "timeout":
            await self.handle_timeout_cleanup(event_state, event_channel)

        # Clean up hunter battle states
        await self.cleanup_hunter_states(event_state)

        # Delete channel after delay
        if event_channel:
            await asyncio.sleep(10)
            try:
                await event_channel.delete()
                print(f"Event channel deleted for {boss_data['name']} - outcome: {outcome}")
            except discord.errors.NotFound:
                pass
            except Exception as e:
                print(f"Error deleting event channel: {e}")

    async def handle_victory_rewards(self, event_state, event_channel):
        """Handle victory rewards distribution"""
        boss_data = event_state['boss_data']
        
        # Send victory message
        victory_embed = discord.Embed(
            title="🎉 VICTORY!",
            description=f"**{boss_data['name']}** has been defeated by the combined efforts of all hunters!",
            color=discord.Color.gold()
        )

        # Distribute rewards to all participants
        for user_id, participant in event_state['participants'].items():
            hunters_data = self.load_hunters_data()
            hunter = hunters_data.get(user_id)
            
            if hunter:
                # Calculate rewards
                exp_gained = boss_data['exp_reward']
                gold_gained = boss_data['gold_reward']
                
                # Apply weekend multiplier
                if self.double_exp_active:
                    exp_gained = int(exp_gained * self.weekend_exp_multiplier)
                
                # Apply rewards
                hunter['exp'] = hunter.get('exp', 0) + exp_gained
                hunter['gold'] = hunter.get('gold', 0) + gold_gained
                
                # Check for exclusive equipment drop
                if boss_data.get('exclusive_equipment', False) and random.random() < 0.30:  # 30% chance
                    exclusive_item = self.get_random_exclusive_equipment()
                    if exclusive_item:
                        hunter.setdefault('inventory', []).append(exclusive_item)
                        victory_embed.add_field(
                            name=f"🌟 Exclusive Drop for {participant['user'].display_name}!",
                            value=f"**{exclusive_item['name']}** - {exclusive_item['description']}",
                            inline=False
                        )
                
                # Reset battle state
                hunter['in_battle'] = False
                hunter.pop('battle_type', None)
                hunter.pop('event_id', None)
                hunter['hp'] = hunter.get('max_hp', 100)  # Full heal after victory
                
                # Save data
                hunters_data[user_id] = hunter
                
        self.save_hunters_data(hunters_data)

        # Add reward summary
        victory_embed.add_field(
            name="🏆 Rewards Distributed",
            value=f"**Base EXP:** {boss_data['exp_reward']} {f'(x{self.weekend_exp_multiplier} weekend bonus!)' if self.double_exp_active else ''}\n**Gold:** {boss_data['gold_reward']}\n**Exclusive Equipment:** 30% drop chance",
            inline=False
        )

        await event_channel.send(embed=victory_embed)

    async def handle_defeat_penalties(self, event_state, event_channel):
        """Handle defeat penalties"""
        boss_data = event_state['boss_data']
        
        defeat_embed = discord.Embed(
            title="💀 DEFEAT",
            description=f"All hunters have fallen to **{boss_data['name']}**. The boss escapes to fight another day.",
            color=discord.Color.red()
        )

        # Apply minor penalties and reset states
        hunters_data = self.load_hunters_data()
        for user_id, participant in event_state['participants'].items():
            hunter = hunters_data.get(user_id)
            if hunter:
                # Minor penalty
                hunter['gold'] = max(0, hunter.get('gold', 0) - 25)
                # Reset battle state
                hunter['in_battle'] = False
                hunter.pop('battle_type', None)
                hunter.pop('event_id', None)
                hunter['hp'] = hunter.get('max_hp', 100)  # Revive with full HP

        self.save_hunters_data(hunters_data)

        defeat_embed.add_field(
            name="⚖️ Penalties",
            value="• All hunters revived with full HP\n• Minor gold penalty (-25 gold)\n• Boss remains at large",
            inline=False
        )

        await event_channel.send(embed=defeat_embed)

    async def handle_timeout_cleanup(self, event_state, event_channel):
        """Handle timeout cleanup"""
        boss_data = event_state['boss_data']
        
        timeout_embed = discord.Embed(
            title="⏰ EVENT TIMEOUT",
            description=f"The battle against **{boss_data['name']}** has timed out. The boss has escaped!",
            color=discord.Color.orange()
        )

        # Reset hunter states
        await self.cleanup_hunter_states(event_state)

        await event_channel.send(embed=timeout_embed)

    async def cleanup_hunter_states(self, event_state):
        """Clean up hunter battle states"""
        hunters_data = self.load_hunters_data()
        
        for user_id in event_state['participants']:
            hunter = hunters_data.get(user_id)
            if hunter:
                hunter['in_battle'] = False
                hunter.pop('battle_type', None)
                hunter.pop('event_id', None)
        
        self.save_hunters_data(hunters_data)

    def get_random_exclusive_equipment(self):
        """Get random exclusive equipment item"""
        all_equipment = []
        for category in self.exclusive_equipment.values():
            all_equipment.extend(category)
        
        if all_equipment:
            return random.choice(all_equipment).copy()
        return None

    @tasks.loop(minutes=30)
    async def weekend_exp_monitor(self):
        """Monitor and announce weekend EXP status changes"""
        try:
            is_weekend_now = self.is_weekend()
            
            if is_weekend_now and not self.double_exp_active:
                self.double_exp_active = True
                await self.announce_weekend_start()
            elif not is_weekend_now and self.double_exp_active:
                self.double_exp_active = False
                await self.announce_weekend_end()
                
        except Exception as e:
            print(f"Error in weekend EXP monitor: {e}")

    @weekend_exp_monitor.before_loop
    async def before_weekend_monitor(self):
        await self.bot.wait_until_ready()

    async def announce_weekend_start(self):
        """Announce weekend double EXP event start"""
        try:
            system_channel = self.bot.get_channel(self.SYSTEM_CHANNEL_ID)
            if not system_channel:
                return

            embed = discord.Embed(
                title="🎉 WEEKEND DOUBLE EXP EVENT ACTIVE!",
                description="The System has detected increased magical activity! All hunters gain **2x EXP** from all activities!",
                color=discord.Color.gold()
            )

            embed.add_field(
                name="📈 Event Benefits",
                value="• **2x EXP** from combat\n• **2x EXP** from quest completion\n• **2x EXP** from exploration\n• **Special weekend bosses** with exclusive equipment!",
                inline=False
            )

            embed.add_field(
                name="⏰ Duration",
                value="Active all weekend (Saturday & Sunday)",
                inline=True
            )

            embed.add_field(
                name="🎯 Special Bosses",
                value="Legendary weekend bosses may spawn with exclusive equipment drops!",
                inline=True
            )

            await system_channel.send(embed=embed)

        except Exception as e:
            print(f"Error announcing weekend start: {e}")

    async def announce_weekend_end(self):
        """Announce weekend double EXP event end"""
        try:
            system_channel = self.bot.get_channel(self.SYSTEM_CHANNEL_ID)
            if not system_channel:
                return

            embed = discord.Embed(
                title="✨ WEEKEND DOUBLE EXP EVENT ENDED",
                description="The weekend event has concluded. EXP gains return to normal rates.",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="📊 Until Next Weekend",
                value="Normal EXP rates active until next Saturday",
                inline=False
            )

            await system_channel.send(embed=embed)

        except Exception as e:
            print(f"Error announcing weekend end: {e}")

    # Commands
    @commands.command(name='weekend_exp')
    async def check_weekend_exp(self, ctx):
        """Check current weekend EXP status"""
        is_weekend = self.is_weekend()
        multiplier = self.get_exp_multiplier()
        
        embed = discord.Embed(
            title="📊 Weekend EXP Status",
            color=discord.Color.gold() if is_weekend else discord.Color.blue()
        )
        
        if is_weekend:
            embed.add_field(
                name="🎉 Weekend Active!",
                value=f"**{multiplier}x EXP** from all activities",
                inline=False
            )
            embed.add_field(
                name="⏰ Active Until",
                value="Sunday 11:59 PM",
                inline=True
            )
            embed.add_field(
                name="🌟 Special Features",
                value="• Weekend special bosses\n• Exclusive equipment drops\n• Enhanced event spawn rates",
                inline=True
            )
        else:
            embed.add_field(
                name="⏰ Next Weekend",
                value="Saturday & Sunday: **2x EXP**",
                inline=False
            )
            
        await ctx.send(embed=embed)

    @commands.command(name='weekend_boss')
    @commands.has_permissions(administrator=True)
    async def trigger_weekend_boss(self, ctx):
        """Manually trigger a weekend special boss event"""
        if not self.is_weekend():
            await ctx.send("❌ Weekend special bosses can only be triggered on weekends!")
            return
            
        # Check if event already active
        if self.bot.active_event_battles:
            await ctx.send("❌ An event boss is already active!")
            return
            
        await self.spawn_weekend_special_boss(ctx.guild)
        await ctx.send("✅ Weekend special boss event triggered!")

    @commands.command(name='test_event')
    @commands.has_permissions(administrator=True)
    async def test_event_boss(self, ctx, boss_id: str = "test_boss"):
        """Test event boss system with simple direct combat"""
        # Check if event already active
        if self.bot.active_event_battles:
            await ctx.send("❌ An event boss is already active!")
            return

        # Create simple test boss without dialogue
        test_boss = {
            "id": boss_id,
            "name": "Test Combat Boss",
            "description": "A simple test boss for debugging combat UI",
            "hp": 1000,
            "max_hp": 1000,
            "attack": 50,
            "defense": 10,
            "level_req": 1,
            "exp_reward": 100,
            "gold_reward": 50,
            "exclusive_equipment": False,
            "weekend_only": False,
            "dialogue_trigger": None  # No dialogue - direct combat
        }

        # Generate unique event ID
        event_id = f"test_{boss_id}_{int(time.time())}_{random.randint(100,999)}"
        
        # Create event state
        event_state = {
            'boss_data': test_boss,
            'current_boss_hp': test_boss['hp'],
            'participants': {},
            'created_at': datetime.now(),
            'combat_started': False
        }
        
        # Store event
        self.bot.active_event_battles[event_id] = event_state
        
        # Create announcement
        embed = discord.Embed(
            title="🔧 TEST EVENT BOSS",
            description=f"**{test_boss['name']}** has been spawned for testing!\n\n{test_boss['description']}",
            color=discord.Color.orange()
        )

        embed.add_field(
            name="🎯 Test Purpose",
            value="Testing combat UI and channel creation",
            inline=False
        )

        embed.add_field(
            name="⚔️ Boss Stats",
            value=f"**HP:** {test_boss['hp']:,}\n**Attack:** {test_boss['attack']}\n**Defense:** {test_boss['defense']}",
            inline=True
        )

        embed.set_footer(text="Test Event • Click to join and test combat system")

        # Create join view
        join_view = EventJoinView(self, event_id)
        
        # Send to current channel
        message = await ctx.send(embed=embed, view=join_view)
        event_state['announcement_message'] = message
        self.bot.active_event_battles[event_id] = event_state

        print(f"DEBUG: Test event {event_id} created with boss {boss_id}")

    @commands.command(name='startevent')
    @commands.has_permissions(administrator=True)
    async def start_event_boss(self, ctx, boss_name: str = "ice_monarch"):
        """Start an event boss battle with the specified boss"""
        print(f"DEBUG: startevent command called with boss_name: {boss_name}")
        
        # Check if event already active
        if self.bot.active_event_battles:
            await ctx.send("❌ An event boss is already active!")
            return

        # Get boss data
        boss_data = self.event_bosses.get(boss_name)
        if not boss_data:
            available_bosses = ", ".join(self.event_bosses.keys())
            await ctx.send(f"❌ Unknown boss '{boss_name}'. Available bosses: {available_bosses}")
            return
        
        print(f"DEBUG: Boss data found for {boss_name}: {boss_data['name']}")

        # Generate unique event ID
        event_id = f"event_{boss_name}_{int(time.time())}_{random.randint(100,999)}"
        
        # Create event state
        event_state = {
            'boss_data': boss_data.copy(),
            'current_boss_hp': boss_data['hp'],
            'participants': {},
            'created_at': datetime.now(),
            'combat_started': False
        }
        
        # Store event
        self.bot.active_event_battles[event_id] = event_state
        print(f"DEBUG: Event state created and stored for {event_id}")
        
        # Create announcement embed
        embed = discord.Embed(
            title="⚔️ EVENT BOSS APPEARED!",
            description=f"**{boss_data['name']}** has emerged!\n\n{boss_data['description']}",
            color=discord.Color.red()
        )

        embed.add_field(
            name="⚔️ Boss Stats",
            value=f"**HP:** {boss_data['hp']:,}\n**Attack:** {boss_data['attack']}\n**Defense:** {boss_data['defense']}",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Requirements",
            value=f"**Min Level:** {boss_data.get('level_req', 1)}\n**Participants:** Unlimited",
            inline=True
        )

        if boss_data.get('exclusive_equipment'):
            embed.add_field(
                name="🏆 Special Rewards",
                value="⭐ **EXCLUSIVE EQUIPMENT** drops available!",
                inline=False
            )

        embed.set_footer(text="Click the button below to join the battle!")

        # Create join view
        join_view = EventJoinView(self, event_id)
        
        # Send announcement
        message = await ctx.send(embed=embed, view=join_view)
        event_state['announcement_message'] = message
        self.bot.active_event_battles[event_id] = event_state
        
        print(f"DEBUG: Event announcement sent for {boss_data['name']} with event_id: {event_id}")
        
        # Also send to system channel if available
        system_channel = self.bot.get_channel(self.SYSTEM_CHANNEL_ID)
        if system_channel and system_channel != ctx.channel:
            try:
                await system_channel.send(embed=embed, view=EventJoinView(self, event_id))
                print(f"DEBUG: Event announcement also sent to system channel")
            except Exception as e:
                print(f"ERROR: Failed to send to system channel: {e}")

    async def spawn_weekend_special_boss(self, guild):
        """Spawn a weekend special boss"""
        # Get weekend-only bosses
        weekend_bosses = {k: v for k, v in self.event_bosses.items() if v.get('weekend_only', False)}
        
        if not weekend_bosses:
            return
        
        # Select random weekend boss
        boss_id = random.choice(list(weekend_bosses.keys()))
        boss_data = weekend_bosses[boss_id].copy()
        
        # Generate unique event ID
        event_id = f"weekend_{boss_id}_{int(time.time())}_{random.randint(100,999)}"
        
        # Create event state
        event_state = {
            'boss_data': boss_data,
            'current_boss_hp': boss_data['hp'],
            'participants': {},
            'created_at': datetime.now(),
            'combat_started': False
        }
        
        # Store event
        self.bot.active_event_battles[event_id] = event_state
        
        # Create announcement
        embed = discord.Embed(
            title="🌟 WEEKEND SPECIAL EVENT!",
            description=f"**{boss_data['name']}** has emerged!\n\n{boss_data['description']}\n\n⚠️ **This boss drops EXCLUSIVE EQUIPMENT that cannot be obtained anywhere else!**",
            color=discord.Color.purple()
        )

        embed.add_field(
            name="🎁 Special Rewards",
            value=f"• **{boss_data['exp_reward']:,} EXP** (2x weekend bonus!)\n• **{boss_data['gold_reward']:,} Gold**\n• **Exclusive Legendary Equipment**\n• **30% drop chance for exclusive items**",
            inline=False
        )

        embed.add_field(
            name="⚔️ Boss Stats",
            value=f"**HP:** {boss_data['hp']:,}\n**Attack:** {boss_data['attack']}\n**Defense:** {boss_data['defense']}\n**Min Level:** {boss_data.get('level_req', 1)}",
            inline=True
        )

        embed.add_field(
            name="🏆 Exclusive Equipment",
            value="• Jinwoo's Shadow Blade\n• Kamish's Wrath\n• Ruler's Authority\n• And more legendary items!",
            inline=True
        )

        embed.set_footer(text="Weekend Special Event • Click to join and fight for exclusive rewards!")

        # Create join view
        join_view = EventJoinView(self, event_id)
        
        # Send to system channel
        system_channel = guild.get_channel(self.SYSTEM_CHANNEL_ID)
        if system_channel:
            message = await system_channel.send(embed=embed, view=join_view)
            event_state['announcement_message'] = message
            self.bot.active_event_battles[event_id] = event_state

async def setup(bot):
    await bot.add_cog(EventManagement(bot))
