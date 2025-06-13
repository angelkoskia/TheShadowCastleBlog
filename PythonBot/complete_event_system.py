# Complete Weekend Double EXP Event System
# File: cogs/event_management.py

import discord
from discord.ext import commands, tasks
import json
import asyncio
import random
import time
from datetime import datetime, timedelta

class EventManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_event = None
        self.event_participants = set()
        self.event_start_time = None
        self.double_exp_active = False
        
        # Event configuration
        self.EVENT_JOIN_TIMEOUT = 60
        self.MIN_PARTICIPANTS = 1
        self.EVENT_DURATION = 900
        self.SYSTEM_CHANNEL_ID = 1381439963656355849
        self.PRIVATE_EVENT_CATEGORY_ID = 1382529024022155274
        
        # Weekend double EXP configuration
        self.weekend_exp_multiplier = 2.0
        self.weekend_days = [5, 6]  # Saturday and Sunday
        
        # Exclusive equipment only from weekend special bosses
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
            ],
            "legendary_armor": [
                {
                    "name": "Shadow Sovereign's Cloak",
                    "type": "armor",
                    "rarity": "legendary", 
                    "defense": 200,
                    "description": "The mantle of the Shadow Monarch",
                    "special_effects": ["Shadow Regeneration: Heal 10% HP per turn", "Death Immunity"]
                }
            ],
            "mythic_accessories": [
                {
                    "name": "System Administrator's Ring",
                    "type": "accessory",
                    "rarity": "mythic",
                    "description": "Grants limited access to System functions",
                    "special_effects": ["Double EXP permanently", "Item duplication (1/day)"]
                }
            ]
        }
        
        # Start the event loop
        self.event_loop.start()

    def is_weekend(self):
        """Check if current day is weekend (Saturday or Sunday)"""
        current_day = datetime.now().weekday()
        return current_day in self.weekend_days

    def get_exp_multiplier(self):
        """Get current EXP multiplier based on weekend status"""
        multiplier = 1.0
        
        if self.is_weekend():
            multiplier *= self.weekend_exp_multiplier
            self.double_exp_active = True
        else:
            self.double_exp_active = False
            
        return multiplier

    def get_random_exclusive_equipment(self):
        """Get random exclusive equipment item for special events"""
        all_equipment = []
        all_equipment.extend(self.exclusive_equipment["legendary_weapons"])
        all_equipment.extend(self.exclusive_equipment["legendary_armor"])
        all_equipment.extend(self.exclusive_equipment["mythic_accessories"])
        
        if all_equipment:
            return random.choice(all_equipment)
        return None

    async def announce_weekend_event(self):
        """Announce weekend double EXP event"""
        try:
            system_channel = self.bot.get_channel(self.SYSTEM_CHANNEL_ID)
            if not system_channel:
                return

            embed = discord.Embed(
                title="🎉 WEEKEND DOUBLE EXP EVENT! 🎉",
                description="The System has detected increased magical activity! All hunters gain **double EXP** from all activities!",
                color=discord.Color.gold()
            )

            embed.add_field(
                name="📈 Event Benefits",
                value="• **2x EXP** from all combat\n• **2x EXP** from quest completion\n• **2x EXP** from dungeon exploration\n• **2x EXP** from training",
                inline=False
            )

            embed.add_field(
                name="⏰ Duration",
                value="Active all weekend (Saturday & Sunday)",
                inline=True
            )

            embed.add_field(
                name="🎯 Special Weekend Bosses",
                value="Legendary bosses may spawn with exclusive equipment!",
                inline=True
            )

            embed.set_footer(text="Take advantage of this weekend boost to level up faster!")
            await system_channel.send(embed=embed)

        except Exception as e:
            print(f"Error announcing weekend event: {e}")

    @tasks.loop(minutes=30)
    async def event_loop(self):
        """Main event scheduling loop"""
        try:
            # Check for weekend status changes and announce if needed
            if self.is_weekend() and not self.double_exp_active:
                await self.announce_weekend_event()
            
            # Don't run events if one is already active
            if self.active_event:
                return
                
            # Higher chance for special events on weekends
            base_chance = 0.15 if self.is_weekend() else 0.05  # 15% on weekends, 5% on weekdays
            
            if random.random() < base_chance:
                if self.is_weekend():
                    # Weekend: chance for special boss with exclusive equipment
                    await self.trigger_weekend_special_event()
                else:
                    # Weekday: regular event
                    await self.trigger_random_event()
                
        except Exception as e:
            print(f"Error in event loop: {e}")

    async def trigger_weekend_special_event(self):
        """Trigger special weekend boss event with exclusive equipment"""
        try:
            # Special weekend bosses with exclusive equipment rewards
            weekend_bosses = {
                "Shadow Monarch's Champion": {
                    "name": "Shadow Monarch's Champion",
                    "description": "A legendary shadow warrior blessed by Ashborn himself. Only appears during times of heightened magical energy.",
                    "hp": 8000,
                    "max_hp": 8000,
                    "attack": 300,
                    "defense": 150,
                    "level_req": 20,
                    "color": discord.Color.dark_purple(),
                    "rewards": {
                        "exp": 2500,
                        "gold": 2000,
                        "special_items": ["Weekend Champion Bonus"],
                        "exclusive_equipment": True
                    }
                },
                "Kamish's Heir": {
                    "name": "Kamish's Heir", 
                    "description": "A young dragon carrying the bloodline of the legendary Kamish. Only the strongest hunters dare face this descendant.",
                    "hp": 12000,
                    "max_hp": 12000,
                    "attack": 400,
                    "defense": 200,
                    "level_req": 25,
                    "color": discord.Color.dark_red(),
                    "rewards": {
                        "exp": 4000,
                        "gold": 3500,
                        "special_items": ["Dragon Heritage", "Weekend Champion Bonus"],
                        "exclusive_equipment": True
                    }
                },
                "Architect's Guardian": {
                    "name": "Architect's Guardian",
                    "description": "A powerful construct created by the System's Architect to test the worthiest hunters.",
                    "hp": 15000,
                    "max_hp": 15000,
                    "attack": 500,
                    "defense": 250,
                    "level_req": 30,
                    "color": discord.Color.from_rgb(128, 0, 255),
                    "rewards": {
                        "exp": 6000,
                        "gold": 5000,
                        "special_items": ["System Fragment", "Administrative Token"],
                        "exclusive_equipment": True
                    }
                }
            }

            # Select random weekend boss
            boss_name = random.choice(list(weekend_bosses.keys()))
            boss_data = weekend_bosses[boss_name]

            # Announce special weekend event
            system_channel = self.bot.get_channel(self.SYSTEM_CHANNEL_ID)
            if not system_channel:
                return

            embed = discord.Embed(
                title="🌟 WEEKEND SPECIAL EVENT! 🌟",
                description=f"**{boss_data['name']}** has emerged!\n\n{boss_data['description']}\n\n⚠️ **This boss drops EXCLUSIVE EQUIPMENT that cannot be obtained anywhere else!**",
                color=boss_data['color']
            )

            embed.add_field(
                name="🎁 Special Rewards",
                value=f"• **{boss_data['rewards']['exp']:,} EXP** (2x weekend bonus!)\n• **{boss_data['rewards']['gold']:,} Gold**\n• **Exclusive Legendary Equipment**\n• **Mythic Accessories**",
                inline=False
            )

            embed.add_field(
                name="⚔️ Boss Power",
                value=f"**HP:** {boss_data['hp']:,}\n**Attack:** {boss_data['attack']}\n**Defense:** {boss_data['defense']}\n**Min Level:** {boss_data['level_req']}",
                inline=True
            )

            embed.add_field(
                name="🏆 Exclusive Equipment Pool",
                value="• Jinwoo's Shadow Blade\n• Kamish's Wrath\n• Ruler's Authority\n• Shadow Sovereign's Cloak\n• System Administrator's Ring\n• And more...",
                inline=True
            )

            embed.set_footer(text="Weekend Special Event • Exclusive equipment only available from special bosses!")

            # Start the special event
            self.active_event = {
                'data': boss_data,
                'channel': system_channel,
                'type': 'weekend_special'
            }

            message = await system_channel.send(embed=embed)
            await message.add_reaction("✅")

            # Wait for participants
            await self.wait_for_event_join(message)

        except Exception as e:
            print(f"Error triggering weekend special event: {e}")

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
                name="Active Until",
                value="Sunday 11:59 PM",
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
            
        if self.active_event:
            await ctx.send("❌ There is already an active event!")
            return
            
        await self.trigger_weekend_special_event()
        await ctx.send("✅ Weekend special boss event triggered!")

    @event_loop.before_loop
    async def before_event_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(EventManagement(bot))


# File: cogs/event_bosses.py

import discord
from discord.ext import commands
import json
import random
import asyncio
from datetime import datetime, timedelta

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
            
            embed.add_field(
                name="🏆 Challenge Rating",
                value=boss_data.get('rarity', 'legendary').title(),
                inline=True
            )
            
            embed.add_field(
                name="💪 Boss HP",
                value=f"{boss_data['hp']} HP",
                inline=True
            )
            
            embed.add_field(
                name="🎁 Rewards", 
                value=f"**EXP:** {boss_data.get('exp_reward', 500)}\n**Gold:** {boss_data.get('gold_reward', 300)}",
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

async def setup(bot):
    await bot.add_cog(EventBosses(bot))


# How to Use the Event System:

# 1. Weekend Double EXP automatically activates on Saturday and Sunday
# 2. Use .weekend_exp to check current status
# 3. Admin commands:
#    - .weekend_boss (triggers weekend special boss with exclusive equipment)
#    - .event_boss <id> (spawns specific event boss)
#    - .list_bosses (shows all available bosses)

# 4. Private Channel System:
#    - Events create "Event Chambers" category
#    - Only participants gain channel access via "Join Event" button
#    - Channels auto-delete on victory, defeat, timeout, or boss escape

# 5. Exclusive Equipment:
#    - Only available from weekend special bosses
#    - Includes Jinwoo's Shadow Blade, Kamish's Wrath, Ruler's Authority
#    - 30% drop chance from special weekend bosses

# 6. Auto-Deletion Conditions:
#    - Victory: 10 seconds after boss defeat
#    - Defeat: When all participants die
#    - Timeout: 5 minutes of combat inactivity  
#    - Boss Escape: 10 minutes total event time