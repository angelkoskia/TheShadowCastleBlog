import discord
from discord.ext import commands
import json
import random
import asyncio
from datetime import datetime, timedelta
from utils.boss_dialogue import (
    get_boss_dialogue,
    format_boss_encounter_text,
    get_boss_status_effects,
    should_trigger_dialogue,
    get_contextual_boss_response
)
from ui_elements_event import EventCombatView, JoinEventView

class EventBossCombatView(discord.ui.View):
    """Interactive combat view for event boss encounters"""
    
    def __init__(self, event_cog, event_id, event_channel):
        super().__init__(timeout=300.0)  # 5 minute combat timeout
        self.event_cog = event_cog
        self.event_id = event_id
        self.event_channel = event_channel
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only participants can interact"""
        event_state = self.event_cog.active_events.get(self.event_id)
        if not event_state:
            return False
            
        return str(interaction.user.id) in event_state['participants']
    
    @discord.ui.button(label="⚔️ Attack", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle attack button press"""
        await interaction.response.defer()
        await self.event_cog.handle_event_attack(interaction.user.id, self.event_id)
    
    @discord.ui.button(label="🛡️ Defend", style=discord.ButtonStyle.primary, emoji="🛡️")
    async def defend_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle defend button press"""
        await interaction.response.defer()
        await self.event_cog.handle_event_defend(interaction.user.id, self.event_id)
    
    @discord.ui.button(label="🏃 Flee", style=discord.ButtonStyle.secondary, emoji="🏃")
    async def flee_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle flee button press"""
        await interaction.response.defer()
        await self.event_cog.handle_event_flee(interaction.user.id, self.event_id)

    async def on_timeout(self):
        """Handle view timeout - boss escapes due to inactivity"""
        try:
            event_state = self.event_cog.active_events.get(self.event_id)
            if event_state:
                # Disable all buttons
                for item in self.children:
                    item.disabled = True
                
                # Update the combat message
                if 'combat_message' in event_state and event_state['combat_message']:
                    timeout_embed = discord.Embed(
                        title="⏰ Combat Timeout!",
                        description=f"**{event_state['boss_data']['name']}** escaped due to hunter inactivity!",
                        color=discord.Color.orange()
                    )
                    timeout_embed.add_field(
                        name="Result",
                        value="The boss vanished before it could be defeated. No penalties applied.",
                        inline=False
                    )
                    
                    await event_state['combat_message'].edit(embed=timeout_embed, view=self)
                
                # End the event battle with timeout
                await self.event_cog.end_event_battle(self.event_id, "timeout")
                
        except Exception as e:
            print(f"Error handling combat timeout: {e}")
        
        self.stop()

class EventJoinView(discord.ui.View):
    """View for joining event boss encounters"""
    
    def __init__(self, event_cog, event_id, event_channel):
        super().__init__(timeout=600.0)
        self.event_cog = event_cog
        self.event_id = event_id
        self.event_channel = event_channel
    
    @discord.ui.button(label="Join Event", style=discord.ButtonStyle.success, emoji="✅")
    async def join_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle joining the event"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            user_id = str(interaction.user.id)
            user = interaction.user
            
            # Load hunter data
            hunters_data = self.event_cog.load_hunters_data()
            
            if user_id not in hunters_data:
                await interaction.followup.send("You need to start your journey first! Use `.start` to begin.", ephemeral=True)
                return
                
            hunter = hunters_data[user_id]
            
            # Check if hunter is already in battle
            if hunter.get('in_battle', False):
                await interaction.followup.send("You are already in combat! Finish your current battle first.", ephemeral=True)
                return
            
            # Get event state
            event_state = self.event_cog.active_events.get(self.event_id)
            if not event_state:
                await interaction.followup.send("This event is no longer active!", ephemeral=True)
                return
            
            boss_data = event_state['boss_data']
                
            # Check level requirement if exists
            if 'level_req' in boss_data and hunter.get('level', 1) < boss_data['level_req']:
                await interaction.followup.send(f"You need to be level {boss_data['level_req']} or higher to challenge this boss!", ephemeral=True)
                return
            
            # Check if already participant
            if user_id in event_state['participants']:
                await interaction.followup.send(f"You are already participating in this event! Check {self.event_channel.mention}", ephemeral=True)
                return
            
            # Grant access to private event channel
            await self.event_channel.set_permissions(
                user, 
                read_messages=True, 
                send_messages=True,
                view_channel=True
            )
            
            # Add participant to event
            event_state['participants'][user_id] = {
                'user': user,
                'hunter_data': hunter,
                'hp': hunter.get('hp', hunter.get('max_hp', 100)),
                'max_hp': hunter.get('max_hp', 100),
                'joined_at': datetime.now()
            }
            
            # Mark hunter as in battle
            hunter['in_battle'] = True
            hunter['battle_type'] = 'event_boss'
            hunter['event_id'] = self.event_id
            self.event_cog.save_hunters_data(hunters_data)
            
            await interaction.followup.send(
                f"You have joined the **{boss_data['name']}** event! You now have access to {self.event_channel.mention}",
                ephemeral=True
            )
            
            # Send welcome message in event channel
            welcome_embed = discord.Embed(
                title=f"🔥 {user.display_name} has joined the battle!",
                description=f"Welcome to the **{boss_data['name']}** encounter!",
                color=discord.Color.green()
            )
            welcome_embed.add_field(
                name="Participant Status",
                value=f"**Level:** {hunter.get('level', 1)}\n**HP:** {hunter.get('hp', 100)}/{hunter.get('max_hp', 100)}",
                inline=True
            )
            
            await self.event_channel.send(embed=welcome_embed)
            
            # Start combat if this is the first participant
            if len(event_state['participants']) == 1 and not event_state['combat_started']:
                await self.event_cog.start_event_combat(self.event_id)
            
        except Exception as e:
            await interaction.followup.send(f"Error joining event: {str(e)}", ephemeral=True)
            print(f"Event join error: {e}")

class EventBosses(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_events = {}  # Track active event boss encounters
        self.event_participants = {}  # Track participants in each event
        self.event_channels = {}  # Track event channels
        
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
    
    def load_event_bosses_data(self):
        """Load event boss data from JSON file"""
        try:
            with open('data/event_bosses.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"event_bosses": []}

    def load_boss_priority_data(self):
        """Load boss priority and spawning configuration"""
        try:
            with open('data/boss_priority.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "boss_priority": {"tier_1_legendary": ["antares", "shadow_monarch", "kamish"]},
                "spawn_weights": {"tier_1_legendary": 5},
                "auto_spawn_settings": {"enabled": False}
            }
    
    def load_monster_data(self):
        """Load monster data from JSON file"""
        try:
            with open('data/monsters.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"monsters": []}

    def select_priority_boss(self):
        """Select a boss based on priority system favoring canon bosses"""
        priority_data = self.load_boss_priority_data()
        event_bosses_data = self.load_event_bosses_data()
        bosses = event_bosses_data.get('event_bosses', [])
        
        if not bosses:
            return None
        
        # Get priority tiers and weights
        boss_priority = priority_data.get('boss_priority', {})
        spawn_weights = priority_data.get('spawn_weights', {})
        
        # Create weighted selection pools
        weighted_bosses = []
        
        for tier, boss_ids in boss_priority.items():
            weight = spawn_weights.get(tier, 1)
            tier_bosses = [boss for boss in bosses if boss['id'] in boss_ids]
            
            # Add each boss multiple times based on weight (higher weight = more likely)
            for boss in tier_bosses:
                weighted_bosses.extend([boss] * weight)
        
        # Add any bosses not in priority tiers with default weight
        categorized_boss_ids = set()
        for tier_bosses in boss_priority.values():
            categorized_boss_ids.update(tier_bosses)
        
        uncategorized_bosses = [boss for boss in bosses if boss['id'] not in categorized_boss_ids]
        weighted_bosses.extend(uncategorized_bosses)
        
        return random.choice(weighted_bosses) if weighted_bosses else random.choice(bosses)

    @commands.command(name="event_boss", aliases=["spawn_boss"])
    @commands.has_permissions(administrator=True)
    async def spawn_event_boss(self, ctx, boss_id: str = None):
        """Admin command to spawn an event boss"""
        event_bosses_data = self.load_event_bosses_data()
        
        if not boss_id:
            # Use priority system to select most iconic Solo Leveling bosses
            boss_data = self.select_priority_boss()
            if not boss_data:
                await ctx.send("❌ No event bosses configured.")
                return
        else:
            # Find the specified boss
            boss_data = None
            for boss in event_bosses_data.get("event_bosses", []):
                if boss['id'] == boss_id:
                    boss_data = boss
                    break
            
            if not boss_data:
                # Show available bosses if invalid ID provided
                embed = discord.Embed(
                    title="📋 Available Event Bosses",
                    color=discord.Color.red()
                )
                
                # Group bosses by priority tier
                priority_data = self.load_boss_priority_data()
                boss_priority = priority_data.get('boss_priority', {})
                
                bosses_list = ""
                
                # Show Legendary tier bosses first
                if 'tier_1_legendary' in boss_priority:
                    bosses_list += "**🌟 Legendary Monarchs:**\n"
                    for boss_id in boss_priority['tier_1_legendary']:
                        boss = next((b for b in event_bosses_data.get("event_bosses", []) if b['id'] == boss_id), None)
                        if boss:
                            bosses_list += f"  `{boss['id']}` - {boss['name']}\n"
                    bosses_list += "\n"
                
                # Show Major tier bosses
                if 'tier_2_major' in boss_priority:
                    bosses_list += "**⚔️ Major Bosses:**\n"
                    for boss_id in boss_priority['tier_2_major']:
                        boss = next((b for b in event_bosses_data.get("event_bosses", []) if b['id'] == boss_id), None)
                        if boss:
                            bosses_list += f"  `{boss['id']}` - {boss['name']}\n"
                    bosses_list += "\n"
                
                # Show other tiers
                if 'tier_3_notable' in boss_priority:
                    bosses_list += "**🔥 Notable Enemies:**\n"
                    for boss_id in boss_priority['tier_3_notable']:
                        boss = next((b for b in event_bosses_data.get("event_bosses", []) if b['id'] == boss_id), None)
                        if boss:
                            bosses_list += f"  `{boss['id']}` - {boss['name']}\n"
                
                embed.description = bosses_list or "No event bosses configured."
                embed.set_footer(text="Use .event_boss <boss_id> to spawn a specific boss, or .event_boss for priority selection")
                
                await ctx.send(f"❌ Event boss '{boss_id}' not found.")
                await ctx.send(embed=embed)
                return
        
        # Check if this boss is already active
        if boss_data['id'] in self.active_events:
            await ctx.send(f"❌ {boss_data['name']} is already active!")
            return
        
        # Start the event boss encounter
        await self.start_event_boss_encounter(ctx, boss_data)

    @commands.command(name="random_boss", aliases=["rb", "spawn_random"])
    @commands.has_permissions(administrator=True)
    async def spawn_random_boss(self, ctx, tier: str = None):
        """Admin command to spawn a random event boss, optionally from a specific tier"""
        priority_data = self.load_boss_priority_data()
        event_bosses_data = self.load_event_bosses_data()
        bosses = event_bosses_data.get('event_bosses', [])
        
        if not bosses:
            await ctx.send("❌ No event bosses configured.")
            return
        
        boss_priority = priority_data.get('boss_priority', {})
        
        if tier:
            # Spawn from specific tier
            tier_key = f"tier_{tier.lower()}" if not tier.lower().startswith('tier_') else tier.lower()
            
            # Check for tier aliases
            tier_aliases = {
                'legendary': 'tier_1_legendary',
                'major': 'tier_2_major', 
                'notable': 'tier_3_notable',
                'standard': 'tier_4_standard',
                'common': 'tier_5_common',
                '1': 'tier_1_legendary',
                '2': 'tier_2_major',
                '3': 'tier_3_notable',
                '4': 'tier_4_standard',
                '5': 'tier_5_common'
            }
            
            if tier_key in tier_aliases:
                tier_key = tier_aliases[tier_key]
            
            if tier_key not in boss_priority:
                available_tiers = list(boss_priority.keys())
                await ctx.send(f"❌ Invalid tier '{tier}'. Available tiers: {', '.join(available_tiers)}")
                return
            
            tier_boss_ids = boss_priority[tier_key]
            tier_bosses = [boss for boss in bosses if boss['id'] in tier_boss_ids]
            
            if not tier_bosses:
                await ctx.send(f"❌ No bosses found in tier '{tier_key}'.")
                return
            
            boss_data = random.choice(tier_bosses)
            tier_name = tier_key.replace('tier_', '').replace('_', ' ').title()
            
            await ctx.send(f"🎲 Randomly selected **{boss_data['name']}** from {tier_name} tier!")
        else:
            # Use priority-weighted selection for all tiers
            boss_data = self.select_priority_boss()
            if not boss_data:
                await ctx.send("❌ Failed to select a random boss.")
                return
            
            await ctx.send(f"🎲 Randomly selected **{boss_data['name']}** using priority system!")
        
        # Check if this boss is already active
        if boss_data['id'] in self.active_events:
            await ctx.send(f"❌ {boss_data['name']} is already active! Selecting another...")
            # Try again with a different selection
            available_bosses = [boss for boss in bosses if boss['id'] not in self.active_events]
            if not available_bosses:
                await ctx.send("❌ All event bosses are currently active!")
                return
            boss_data = random.choice(available_bosses)
            await ctx.send(f"🔄 Selected **{boss_data['name']}** instead!")
        
        # Start the event boss encounter
        await self.start_event_boss_encounter(ctx, boss_data)

    @commands.command(name="boss_list", aliases=["bosses", "event_list"])
    @commands.has_permissions(administrator=True)
    async def list_event_bosses(self, ctx):
        """Admin command to list all available event bosses organized by tier"""
        event_bosses_data = self.load_event_bosses_data()
        priority_data = self.load_boss_priority_data()
        bosses = event_bosses_data.get('event_bosses', [])
        boss_priority = priority_data.get('boss_priority', {})
        
        if not bosses:
            await ctx.send("❌ No event bosses configured.")
            return
        
        embed = discord.Embed(
            title="🏆 Available Event Bosses",
            description="All bosses organized by priority tier",
            color=discord.Color.gold()
        )
        
        # Add tier information
        tier_names = {
            'tier_1_legendary': '🌟 Legendary Monarchs',
            'tier_2_major': '⚔️ Major Bosses', 
            'tier_3_notable': '🔥 Notable Enemies',
            'tier_4_standard': '💪 Standard Bosses',
            'tier_5_common': '🎯 Common Bosses'
        }
        
        for tier_key, tier_display in tier_names.items():
            if tier_key in boss_priority:
                tier_bosses = []
                for boss_id in boss_priority[tier_key]:
                    boss = next((b for b in bosses if b['id'] == boss_id), None)
                    if boss:
                        status = "🔴 ACTIVE" if boss_id in self.active_events else "🟢 Available"
                        tier_bosses.append(f"`{boss['id']}` - {boss['name']} {status}")
                
                if tier_bosses:
                    embed.add_field(
                        name=tier_display,
                        value="\n".join(tier_bosses),
                        inline=False
                    )
        
        # Add uncategorized bosses
        categorized_boss_ids = set()
        for tier_bosses in boss_priority.values():
            categorized_boss_ids.update(tier_bosses)
        
        uncategorized_bosses = [boss for boss in bosses if boss['id'] not in categorized_boss_ids]
        if uncategorized_bosses:
            uncategorized_list = []
            for boss in uncategorized_bosses:
                status = "🔴 ACTIVE" if boss['id'] in self.active_events else "🟢 Available"
                uncategorized_list.append(f"`{boss['id']}` - {boss['name']} {status}")
            
            embed.add_field(
                name="📝 Other Bosses",
                value="\n".join(uncategorized_list),
                inline=False
            )
        
        embed.set_footer(text="Use .random_boss [tier] to spawn random bosses | .event_boss <id> for specific bosses")
        
        await ctx.send(embed=embed)

    async def start_event_boss_encounter(self, ctx, boss_data):
        """Start an event boss encounter with private channels and auto-deletion"""
        try:
            # Generate unique event ID
            event_id = f"event_{boss_data['id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(100,999)}"
            
            # Create private event channel first
            guild = ctx.guild
            event_category = discord.utils.get(guild.categories, name="Event Chambers")
            if not event_category:
                event_category = await guild.create_category("Event Chambers", overwrites={
                    guild.default_role: discord.PermissionOverwrite(read_messages=False)
                })
            
            # Create private event channel with restricted access
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
            
            event_channel = await guild.create_text_channel(
                f"event-{boss_data['name'].lower().replace(' ', '-')}-{random.randint(100,999)}",
                category=event_category,
                overwrites=overwrites,
                topic=f"Private event channel for {boss_data['name']} encounter"
            )
            
            # Store active event with complete data
            self.active_events[event_id] = {
                'boss_data': boss_data,
                'participants': {},
                'event_channel': event_channel,
                'announcement_message': None,
                'start_time': datetime.now(),
                'event_id': event_id,
                'combat_started': False
            }
            
            # Create event announcement with join button
            embed = discord.Embed(
                title=f"🔥 {boss_data['name']} Event!",
                description=boss_data.get('description', 'A powerful enemy has appeared!'),
                color=discord.Color.dark_red()
            )
            
            # Add boss image if available
            if boss_data.get('image_url'):
                embed.set_image(url=boss_data['image_url'])
            
            embed.add_field(
                name="🏆 Challenge Rating",
                value=boss_data.get('rarity', 'legendary').title(),
                inline=True
            )
            
            embed.add_field(
                name="💪 Boss HP",
                value=f"{boss_data['hp']:,} HP",
                inline=True
            )
            
            embed.add_field(
                name="🎁 Rewards", 
                value=f"**EXP:** {boss_data.get('exp_reward', 500):,}\n**Gold:** {boss_data.get('gold_reward', 300):,}",
                inline=True
            )
            
            embed.add_field(
                name="⚔️ Combat Style",
                value="Private event channel with turn-based combat",
                inline=False
            )
            
            embed.add_field(
                name="📍 Event Channel",
                value=f"Participants will gain access to {event_channel.mention}",
                inline=False
            )
            
            # Add exclusive drop information if available
            if boss_data.get('exclusive_drop'):
                embed.add_field(
                    name="💎 Exclusive Drop",
                    value=f"**{boss_data['exclusive_drop']}**",
                    inline=False
                )
            
            embed.set_footer(text="Click 'Join Event' to participate! Channel auto-deletes when event ends.")
            
            # Create join view with event ID
            join_view = EventJoinView(self, event_id, event_channel)
            
            # Send to announcements channel
            system_channel = ctx.channel
            message = await system_channel.send(embed=embed, view=join_view)
            self.active_events[event_id]['announcement_message'] = message
            
            # Start global event timer (10 minutes total)
            asyncio.create_task(self.event_global_timer(event_id))
            
            await ctx.send(f"Event boss **{boss_data['name']}** spawned! Private event channel created: {event_channel.mention}")
            
        except Exception as e:
            await ctx.send(f"Failed to start event boss encounter: {str(e)}")
            print(f"Event boss error: {e}")

    async def event_global_timer(self, event_id):
        """Global timer for event - auto-deletes channel if not completed"""
        try:
            await asyncio.sleep(600)  # 10 minutes total event time
            
            event_state = self.active_events.get(event_id)
            if event_state:
                await self.end_event_battle(event_id, "timeout")
                
        except asyncio.CancelledError:
            # Event was completed successfully, timer cancelled
            pass
        except Exception as e:
            print(f"Error in event global timer: {e}")

    async def end_event_battle(self, event_id, outcome="defeat"):
        """End event battle and clean up channel"""
        try:
            event_state = self.active_events.pop(event_id, None)
            if not event_state:
                return
            
            event_channel = event_state['event_channel']
            boss_data = event_state['boss_data']
            
            # Send final message based on outcome
            if outcome == "victory":
                final_embed = discord.Embed(
                    title="🎉 VICTORY!",
                    description=f"**{boss_data['name']}** has been defeated!",
                    color=discord.Color.gold()
                )
                final_embed.add_field(
                    name="Event Complete",
                    value="Rewards have been distributed to all participants!",
                    inline=False
                )
            elif outcome == "defeat":
                final_embed = discord.Embed(
                    title="💀 DEFEAT",
                    description=f"All participants have fallen to **{boss_data['name']}**",
                    color=discord.Color.red()
                )
                final_embed.add_field(
                    name="Event Failed",
                    value="The boss has escaped, but you can try again next time!",
                    inline=False
                )
            elif outcome == "timeout":
                final_embed = discord.Embed(
                    title="⏰ EVENT TIMEOUT",
                    description=f"The event against **{boss_data['name']}** has timed out",
                    color=discord.Color.orange()
                )
                final_embed.add_field(
                    name="Boss Escaped",
                    value="The boss vanished before it could be defeated!",
                    inline=False
                )
            
            final_embed.set_footer(text="This channel will be deleted in 10 seconds...")
            await event_channel.send(embed=final_embed)
            
            # Delete channel after delay
            await asyncio.sleep(10)
            try:
                await event_channel.delete()
                print(f"Event channel deleted for {boss_data['name']} - outcome: {outcome}")
            except discord.errors.NotFound:
                print(f"Event channel for {boss_data['name']} already deleted")
            except Exception as e:
                print(f"Error deleting event channel: {e}")
                
        except Exception as e:
            print(f"Error ending event battle: {e}")

    async def create_private_combat_channel(self, user, boss_data):
        """Create a private combat channel for turn-based boss encounter"""
        try:
            guild = user.guild
            
            # Set up permissions for private channel
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
            
            # Get events category or create it
            event_category = discord.utils.get(guild.categories, name="Event Chambers")
            if not event_category:
                event_category = await guild.create_category("Event Chambers", overwrites={
                    guild.default_role: discord.PermissionOverwrite(read_messages=False)
                })
            
            # Create private combat channel
            channel_name = f"{boss_data['name'].lower().replace(' ', '-')}-vs-{user.display_name.lower().replace(' ', '-')}"
            combat_channel = await guild.create_text_channel(
                channel_name,
                category=event_category,
                overwrites=overwrites,
                topic=f"Private combat chamber: {user.display_name} vs {boss_data['name']}"
            )
            
            return combat_channel
            
        except Exception as e:
            print(f"Error creating combat channel: {e}")
            return None
                # Fallback: create or find event category
                event_category = None
                for category in ctx.guild.categories:
                    if "event" in category.name.lower():
                        event_category = category
                        break
                if not event_category:
                    event_category = await ctx.guild.create_category("🔥 Event Bosses")

            event_channel = await ctx.guild.create_text_channel(
                f"event-{boss_data['name'].lower().replace(' ', '-')}",
                category=event_category,
                overwrites=overwrites
            )

            # Store event battle state in global dictionary
            active_event_battles[event_id] = {
                'boss_data': boss_data.copy(),
                'current_boss_hp': boss_data['hp'],
                'participants': {},  # user_id: hunter_data
                'combat_message': None,
                'combat_view_instance': None,
                'event_channel_id': event_channel.id,
                'start_time': datetime.now()
            }

            # Create join event view with shared state
            join_view = JoinEventView(event_id, boss_data, event_channel, active_event_battles)
            
            # Send announcement to system channel
            system_channel = ctx.guild.get_channel(1381439963656355849)  # SYSTEM_CHANNEL_ID
            if system_channel:
                embed = discord.Embed(
                    title=f"🚨 EVENT BOSS ALERT! 🚨",
                    description=boss_data.get('event_start_message', f"A powerful {boss_data['name']} has appeared!"),
                    color=discord.Color.red()
                )
                
                embed.add_field(name="Boss Level", value=boss_data.get('level', 'Unknown'), inline=True)
                embed.add_field(name="Estimated HP", value=f"{boss_data['hp']:,}", inline=True)
                embed.add_field(name="Participants", value="0", inline=True)
                
                if boss_data.get('image_url'):
                    embed.set_image(url=boss_data['image_url'])
                
                embed.set_footer(text=f"Event ID: {event_id}")
                
                await system_channel.send(embed=embed, view=join_view)
                
            await ctx.send(f"Event boss **{boss_data['name']}** has been spawned! Check the announcements channel to join!")
            
        except Exception as e:
            await ctx.send(f"Failed to start event boss encounter: {str(e)}")
            print(f"Event boss error: {e}")

    async def add_participant_to_event(self, user, boss_id):
        """Add a participant to an event boss encounter"""
        if boss_id not in self.active_events:
            return False
        
        event_data = self.active_events[boss_id]
        event_channel = event_data['channel']
        
        # Add user to channel
        await event_channel.set_permissions(user, read_messages=True, send_messages=True)
        
        # Load hunter data
        hunters_data = self.load_hunters_data()
        hunter = hunters_data.get(str(user.id), {})
        
        if not hunter:
            await event_channel.send(f"❌ {user.mention}, you need to start your hunter journey first! Use `.start`")
            return False
        
        # Add to participants
        event_data['participants'][str(user.id)] = {
            'user': user,
            'hunter': hunter,
            'joined_at': datetime.now(),
            'status': 'alive'
        }
        
        # Welcome message
        embed = discord.Embed(
            title=f"⚔️ Hunter Joined!",
            description=f"{user.mention} has joined the battle against {event_data['boss_data']['name']}!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="🛡️ Hunter",
            value=f"**{hunter.get('name', 'Hunter')}**\nLevel: {hunter.get('level', 1)}\nRank: {hunter.get('rank', 'E')}",
            inline=True
        )
        
        embed.add_field(
            name="👥 Participants",
            value=len(event_data['participants']),
            inline=True
        )
        
        await event_channel.send(embed=embed)
        
        # Start combat if this is the first participant
        if len(event_data['participants']) == 1 and event_data['status'] == 'waiting':
            await self.start_event_combat(boss_id)
        
        return True

    async def start_event_combat(self, boss_id):
        """Start combat for an event boss"""
        if boss_id not in self.active_events:
            return
        
        event_data = self.active_events[boss_id]
        event_channel = event_data['channel']
        boss_data = event_data['boss_data']
        
        # Update event status
        event_data['status'] = 'combat'
        
        # Create boss monster data
        boss_monster = {
            'id': boss_id,
            'name': boss_data['name'],
            'hp': boss_data.get('hp', 1000),
            'max_hp': boss_data.get('hp', 1000),
            'attack': boss_data.get('attack', 50),
            'defense': boss_data.get('defense', 25),
            'boss': True,
            'description': boss_data.get('description', f'A powerful {boss_data["name"]}')
        }
        
        # Store boss monster data in event
        event_data['boss_monster'] = boss_monster
        
        # Send boss encounter message with dialogue
        encounter_text = format_boss_encounter_text(boss_data['name'], "encounter")
        
        embed = discord.Embed(
            title=f"💀 BOSS ENCOUNTER: {boss_data['name']}",
            description=f"{boss_data.get('description', 'A powerful enemy appears!')}\n\n{encounter_text}",
            color=discord.Color.dark_red()
        )
        
        embed.add_field(
            name="💀 Boss Status",
            value=f"HP: {boss_monster['hp']}/{boss_monster['max_hp']}\nATK: {boss_monster['attack']}",
            inline=True
        )
        
        embed.add_field(
            name="👥 Hunters",
            value=f"{len(event_data['participants'])} participants",
            inline=True
        )
        
        embed.set_footer(text="Use the combat buttons to attack, defend, or flee!")
        
        # Create combat view for the event
        combat_view = EventBossCombatView(self, boss_id, event_channel)
        
        # Send combat interface
        combat_message = await event_channel.send(embed=embed, view=combat_view)
        
        # Store combat message reference
        event_data['combat_message'] = combat_message

    async def handle_event_attack(self, user_id, boss_id):
        """Handle attack action in event boss combat"""
        if boss_id not in self.active_events:
            return
            
        event_data = self.active_events[boss_id]
        event_channel = event_data['channel']
        boss_monster = event_data['boss_monster']
        
        # Get participant data
        participant = event_data['participants'].get(str(user_id))
        if not participant:
            return
            
        hunter = participant['hunter']
        user = participant['user']
        
        # Calculate damage
        base_damage = hunter.get('attack', 10)
        damage = random.randint(int(base_damage * 0.8), int(base_damage * 1.2))
        
        # Apply damage to boss
        boss_monster['hp'] = max(0, boss_monster['hp'] - damage)
        
        # Create combat update embed
        embed = discord.Embed(
            title=f"⚔️ {user.display_name} attacks {boss_monster['name']}!",
            description=f"**{damage}** damage dealt!",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="💀 Boss HP",
            value=f"{boss_monster['hp']}/{boss_monster['max_hp']}",
            inline=True
        )
        
        await event_channel.send(embed=embed)
        
        # Check if boss is defeated
        if boss_monster['hp'] <= 0:
            await self.handle_event_boss_defeat(boss_id)
            return
            
        # Boss counter-attack
        await self.handle_boss_counter_attack(boss_id)
        
        # Update combat interface
        await self.update_event_combat_display(boss_id)

    async def handle_event_defend(self, user_id, boss_id):
        """Handle defend action in event boss combat"""
        if boss_id not in self.active_events:
            return
            
        event_data = self.active_events[boss_id]
        event_channel = event_data['channel']
        
        participant = event_data['participants'].get(str(user_id))
        if not participant:
            return
            
        user = participant['user']
        
        # Send defend message
        embed = discord.Embed(
            title=f"🛡️ {user.display_name} takes a defensive stance!",
            description="Defense increased for the next attack!",
            color=discord.Color.blue()
        )
        
        await event_channel.send(embed=embed)
        
        # Boss attack with reduced damage
        await self.handle_boss_counter_attack(boss_id, defensive_user_id=user_id)
        await self.update_event_combat_display(boss_id)

    async def handle_event_flee(self, user_id, boss_id):
        """Handle flee action in event boss combat"""
        if boss_id not in self.active_events:
            return
            
        event_data = self.active_events[boss_id]
        event_channel = event_data['channel']
        
        participant = event_data['participants'].get(str(user_id))
        if not participant:
            return
            
        user = participant['user']
        
        # Remove participant
        del event_data['participants'][str(user_id)]
        
        # Remove channel permissions
        await event_channel.set_permissions(user, read_messages=False)
        
        # Send flee message
        embed = discord.Embed(
            title=f"🏃 {user.display_name} has fled from battle!",
            description="Sometimes retreat is the wisest choice...",
            color=discord.Color.yellow()
        )
        
        await event_channel.send(embed=embed)
        
        # Check if no participants left
        if not event_data['participants']:
            await self.cleanup_event(boss_id)
        else:
            await self.update_event_combat_display(boss_id)

    async def handle_boss_counter_attack(self, boss_id, defensive_user_id=None):
        """Handle boss counter-attack"""
        event_data = self.active_events[boss_id]
        boss_monster = event_data['boss_monster']
        event_channel = event_data['channel']
        
        # Select random participant as target
        participants = list(event_data['participants'].values())
        if not participants:
            return
            
        target = random.choice(participants)
        target_hunter = target['hunter']
        
        # Calculate boss damage
        boss_damage = random.randint(15, 25)
        
        # Reduce damage if target is defending
        if defensive_user_id and str(target['user'].id) == str(defensive_user_id):
            boss_damage = int(boss_damage * 0.5)
            defense_text = " (reduced by defense)"
        else:
            defense_text = ""
        
        # Apply damage to hunter
        current_hp = target_hunter.get('hp', target_hunter.get('max_hp', 100))
        new_hp = max(0, current_hp - boss_damage)
        target_hunter['hp'] = new_hp
        
        # Update hunter data
        hunters_data = self.load_hunters_data()
        hunters_data[str(target['user'].id)] = target_hunter
        self.save_hunters_data(hunters_data)
        
        # Send counter-attack message
        embed = discord.Embed(
            title=f"💥 {boss_monster['name']} strikes back!",
            description=f"{target['user'].mention} takes **{boss_damage}** damage{defense_text}!",
            color=discord.Color.orange()
        )
        
        await event_channel.send(embed=embed)

    async def handle_event_boss_defeat(self, boss_id):
        """Handle event boss defeat"""
        event_data = self.active_events[boss_id]
        event_channel = event_data['channel']
        boss_data = event_data['boss_data']
        
        # Calculate rewards
        participants = event_data['participants']
        reward_exp = 200
        reward_gold = 500
        
        # Award rewards to all participants
        hunters_data = self.load_hunters_data()
        
        victory_embed = discord.Embed(
            title=f"🎉 VICTORY! {boss_data['name']} Defeated!",
            description=f"The mighty {boss_data['name']} has fallen to your combined efforts!",
            color=discord.Color.gold()
        )
        
        # Add boss image if available
        if boss_data.get('image_url'):
            victory_embed.set_thumbnail(url=boss_data['image_url'])
        
        participant_list = ""
        for user_id, participant in participants.items():
            hunter = hunters_data.get(user_id, {})
            if hunter:
                # Award exp and gold
                hunter['exp'] = hunter.get('exp', 0) + reward_exp
                hunter['gold'] = hunter.get('gold', 0) + reward_gold
                hunters_data[user_id] = hunter
                
                participant_list += f"{participant['user'].mention} - Level {hunter.get('level', 1)}\n"
        
        self.save_hunters_data(hunters_data)
        
        victory_embed.add_field(
            name="🏆 Victorious Hunters",
            value=participant_list or "No participants",
            inline=False
        )
        
        victory_embed.add_field(
            name="💰 Rewards",
            value=f"**{reward_exp}** EXP\n**{reward_gold}** Gold",
            inline=True
        )
        
        await event_channel.send(embed=victory_embed)
        
        # Clean up event after delay
        asyncio.create_task(self.delayed_cleanup(boss_id))

    async def delayed_cleanup(self, boss_id):
        """Clean up event after a delay"""
        await asyncio.sleep(30)  # Wait 30 seconds
        await self.cleanup_event(boss_id)

    async def cleanup_event(self, boss_id):
        """Clean up event boss encounter"""
        if boss_id in self.active_events:
            event_data = self.active_events[boss_id]
            
            try:
                await event_data['channel'].delete()
            except:
                pass  # Channel may already be deleted
                
            # Remove from active events
            del self.active_events[boss_id]
            
            if event_data['channel'].id in self.event_channels:
                del self.event_channels[event_data['channel'].id]

    async def update_event_combat_display(self, boss_id):
        """Update the combat display with current status"""
        event_data = self.active_events[boss_id]
        boss_monster = event_data['boss_monster']
        combat_message = event_data.get('combat_message')
        
        if not combat_message:
            return
            
        # Create updated embed
        boss_data = event_data['boss_data']
        embed = discord.Embed(
            title=f"💀 BOSS BATTLE: {boss_monster['name']}",
            description=f"The battle continues!",
            color=discord.Color.dark_red()
        )
        
        # Add boss image if available
        if boss_data.get('image_url'):
            embed.set_thumbnail(url=boss_data['image_url'])
        
        embed.add_field(
            name="💀 Boss Status",
            value=f"HP: {boss_monster['hp']:,}/{boss_monster['max_hp']:,}\nATK: {boss_monster['attack']:,}",
            inline=True
        )
        
        embed.add_field(
            name="👥 Active Hunters",
            value=f"{len(event_data['participants'])} participants",
            inline=True
        )
        
        embed.set_footer(text="Use the combat buttons to attack, defend, or flee!")
        
        # Create new combat view
        combat_view = EventBossCombatView(self, boss_id, event_data['channel'])
        
        try:
            await combat_message.edit(embed=embed, view=combat_view)
        except:
            # If edit fails, send new message
            new_message = await event_data['channel'].send(embed=embed, view=combat_view)
            event_data['combat_message'] = new_message

async def setup(bot):
    await bot.add_cog(EventBosses(bot))