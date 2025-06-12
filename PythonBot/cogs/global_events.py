import discord
from discord.ext import commands
import asyncio
import json
import random
import time

COMBAT_CATEGORY_ID = 1382589016393650248

# Solo Leveling Boss Definitions
SOLO_LEVELING_BOSSES = {
    "mini_bosses": [
        {
            "name": "Steel Fang Beast",
            "level": 15,
            "hp": 1200,
            "max_hp": 1200,
            "attack": 80,
            "defense": 40,
            "abilities": ["Savage Claw", "Pack Howl"],
            "drops": ["Steel Fang Claw", "Beast Hide"],
            "exp_reward": 800,
            "gold_reward": 500,
            "description": "A massive steel-fanged wolf with razor-sharp claws and an insatiable hunger for battle.",
            "color": discord.Color.dark_red()
        },
        {
            "name": "Corrupted Orc Shaman",
            "level": 18,
            "hp": 1000,
            "max_hp": 1000,
            "attack": 70,
            "defense": 30,
            "abilities": ["Hexbolt", "Healing Totem"],
            "drops": ["Dark Totem Fragment", "Shaman Staff"],
            "exp_reward": 1000,
            "gold_reward": 600,
            "description": "An orc shaman corrupted by dark magic, wielding forbidden hexes and totems.",
            "color": discord.Color.dark_purple()
        }
    ],
    "country_threat_bosses": [
        {
            "name": "Frost King",
            "level": 55,
            "hp": 15000,
            "max_hp": 15000,
            "attack": 500,
            "defense": 250,
            "abilities": ["Frozen Domain", "Icicle Barrage", "Cryo Nova"],
            "drops": ["Frost Crown", "Glacial Shard", "Icebound Cloak"],
            "exp_reward": 5000,
            "gold_reward": 3000,
            "description": "An ancient ice elemental king whose presence freezes the very air around him.",
            "color": discord.Color.blue()
        },
        {
            "name": "Abyssal Serpent",
            "level": 60,
            "hp": 18000,
            "max_hp": 18000,
            "attack": 580,
            "defense": 270,
            "abilities": ["Dark Coil", "Venom Rain"],
            "drops": ["Abyss Scale", "Tainted Fang"],
            "exp_reward": 6000,
            "gold_reward": 3500,
            "description": "A massive serpent from the depths of the abyss, dripping with corrosive venom.",
            "color": discord.Color.dark_green()
        }
    ],
    "continent_threat_bosses": [
        {
            "name": "Dragon Emperor Vargros",
            "level": 95,
            "hp": 50000,
            "max_hp": 50000,
            "attack": 1300,
            "defense": 700,
            "abilities": ["Eternal Flame", "Sky Ruin", "Draconic Descent"],
            "drops": ["Emperor's Scale", "Vargros's Heart", "Ancient Flame Core"],
            "exp_reward": 15000,
            "gold_reward": 10000,
            "description": "The most powerful dragon emperor, ruler of the ancient flame and sky itself.",
            "color": discord.Color.orange()
        },
        {
            "name": "Titan of the End",
            "level": 100,
            "hp": 75000,
            "max_hp": 75000,
            "attack": 1500,
            "defense": 800,
            "abilities": ["World Slam", "Endquake", "Cosmic Roar"],
            "drops": ["Titan's Core", "Endbreaker", "Colossus Hide"],
            "exp_reward": 20000,
            "gold_reward": 15000,
            "description": "A colossal titan that brings the end of worlds with each step.",
            "color": discord.Color.dark_magenta()
        }
    ],
    "red_gate_bosses": [
        {
            "name": "Bloodshade Reaper",
            "level": 75,
            "hp": 25000,
            "max_hp": 25000,
            "attack": 850,
            "defense": 450,
            "abilities": ["Shadow Step", "Blood Cleave", "Soul Drain"],
            "drops": ["Reaper's Blade", "Bloodshade Cloak"],
            "exp_reward": 8000,
            "gold_reward": 5000,
            "description": "A dark reaper that feeds on the souls of fallen hunters.",
            "color": discord.Color.dark_red()
        },
        {
            "name": "Gate Keeper of Madness",
            "level": 80,
            "hp": 30000,
            "max_hp": 30000,
            "attack": 900,
            "defense": 500,
            "abilities": ["Mad Howl", "Insanity Chains", "Warped Strike"],
            "drops": ["Madstone", "Keeper's Shackles"],
            "exp_reward": 10000,
            "gold_reward": 6000,
            "description": "A twisted gate keeper driven to madness by cosmic horrors.",
            "color": discord.Color.purple()
        }
    ]
}

class GlobalEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_event = None
        self.event_participants = set()
        self.event_start_time = None
        self.participant_channels = {}
        self.event_battles = {}
        self.rank_announcements = []

    def load_hunters_data(self):
        try:
            with open('hunters_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_hunters_data(self, data):
        try:
            with open('hunters_data.json', 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save hunters data: {e}")

    async def create_event_combat_channel(self, user, boss_data):
        """Create individual event combat channel for participant"""
        guild = user.guild
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        
        # Add moderator permissions
        for role in guild.roles:
            if any(perm_name in role.name.lower() for perm_name in ['mod', 'admin', 'staff']):
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        
        category = discord.utils.get(guild.categories, id=COMBAT_CATEGORY_ID)
        if category is None:
            try:
                fetched = await self.bot.fetch_channel(COMBAT_CATEGORY_ID)
                if isinstance(fetched, discord.CategoryChannel):
                    category = fetched
            except Exception as e:
                print(f"[ERROR] Failed to fetch category: {e}")
                return None

        try:
            # Clean username for channel name
            username = user.display_name
            import re
            username = re.sub(r'[^\w\s\-]', '', username)
            if len(username) > 20:
                username = username[:20]
            channel_name = f"{username}'s Event Battle"
            
            print(f"[DEBUG] Creating event channel for {user.display_name}")
            
            event_channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                category=category,
                topic=f"Global Event Battle - {boss_data['name']}",
                reason="Global event combat channel"
            )
            
            self.participant_channels[str(user.id)] = event_channel.id
            
            # Initialize battle state for this user
            boss_copy = boss_data.copy()
            boss_copy['current_hp'] = boss_copy['hp']
            # Remove the discord.Color object for JSON serialization
            if 'color' in boss_copy:
                del boss_copy['color']
            
            self.event_battles[str(user.id)] = {
                'boss': boss_copy,
                'channel_id': event_channel.id,
                'event_type': 'global_event'
            }
            
            # Update hunter data with event battle state
            hunters_data = self.load_hunters_data()
            if str(user.id) in hunters_data:
                hunters_data[str(user.id)]['event_battle'] = {
                    'boss': boss_copy,
                    'channel_id': event_channel.id,
                    'event_type': 'global_event'
                }
                self.save_hunters_data(hunters_data)
            
            # Send welcome message to event channel
            welcome_embed = discord.Embed(
                title=f"⚔️ {boss_data['name']} Battle",
                description=f"Welcome {user.mention}! You face the mighty **{boss_data['name']}**!\n\n{boss_data['description']}",
                color=boss_data['color']
            )
            
            welcome_embed.add_field(
                name="Boss Stats",
                value=f"❤️ HP: {boss_data['hp']:,}/{boss_data['max_hp']:,}\n⚔️ Attack: {boss_data['attack']}\n🛡️ Defense: {boss_data['defense']}",
                inline=True
            )
            
            welcome_embed.add_field(
                name="Combat Commands",
                value="`.attack` - Attack the boss\n`.defend` - Defend against attacks\n`.flee` - Escape from battle",
                inline=True
            )
            
            welcome_embed.set_footer(text="Use combat commands to defeat this boss and claim rewards!")
            
            await event_channel.send(embed=welcome_embed)
            
            return event_channel
            
        except Exception as e:
            print(f"[ERROR] Failed to create event combat channel: {e}")
            return None

    async def event_loop(self):
        """Automated event loop that triggers random events"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Skip if there's already an active event
                if self.active_event:
                    continue
                
                # 60% chance to trigger an event
                if random.random() < 0.6:
                    await self.trigger_random_event()
                    
            except Exception as e:
                print(f"[ERROR] Event loop error: {e}")
                await asyncio.sleep(60)

    async def trigger_random_event(self):
        """Trigger a random global event"""
        if self.active_event:
            return
        
        # Get system channel for announcements
        try:
            SYSTEM_CHANNEL_ID = 1382575686506975323
            system_channel = self.bot.get_channel(SYSTEM_CHANNEL_ID)
            if not system_channel:
                return
        except:
            return

        event_types = ['mini_boss', 'country_boss', 'continent_boss', 'red_gate']
        weights = [40, 30, 20, 10]  # Higher chance for easier events
        event_type = random.choices(event_types, weights=weights)[0]

        event_names = {
            'mini_boss': '⚔️ Mini Boss Has Appeared!',
            'country_boss': '🌍 Country-Level Threat!',
            'continent_boss': '🌐 Continent-Level Threat!',
            'red_gate': '🩸 ??? Red Gate Has Opened!'
        }

        event_colors = {
            'mini_boss': discord.Color.orange(),
            'country_boss': discord.Color.red(),
            'continent_boss': discord.Color.dark_red(),
            'red_gate': discord.Color.purple()
        }

        embed = discord.Embed(
            title=event_names[event_type],
            description="🚨 **A dangerous entity has appeared!** 🚨\n\nReact with ✅ to join the battle or ❌ to stay safe.\n⏰ **Event starts in 2 minutes!**",
            color=event_colors[event_type]
        )
        
        embed.add_field(
            name="⚠️ Warning",
            value="Only experienced hunters should participate in high-level threats!",
            inline=False
        )
        
        embed.set_footer(text="Prepare yourself, hunter. Death is permanent.")

        try:
            message = await system_channel.send("@everyone", embed=embed)
            await message.add_reaction("✅")
            await message.add_reaction("❌")

            self.active_event = {
                'type': event_type,
                'message': message,
                'channel': system_channel,
                'data': None
            }

            # Wait for participants
            await self.wait_for_event_join(message, event_type)

        except Exception as e:
            print(f"[ERROR] Failed to trigger event: {e}")
            self.active_event = None

    async def wait_for_event_join(self, message, event_type):
        """Wait for users to join the event with real-time updates"""
        try:
            await asyncio.sleep(120)  # 2 minutes for joining
            
            if not self.active_event:
                return
                
            # Fetch updated message
            message = await message.channel.fetch_message(message.id)
            reaction = discord.utils.get(message.reactions, emoji="✅")
            
            if reaction:
                users = [u async for u in reaction.users() if not u.bot]
                participants = []
                
                hunters_data = self.load_hunters_data()
                
                for user in users:
                    hunter = hunters_data.get(str(user.id))
                    if not hunter:
                        continue
                    
                    # Rank requirements for different events
                    if event_type == "mini_boss":
                        participants.append(user)
                    elif event_type == "country_boss" and hunter['rank'] in ['C', 'B', 'A', 'S', 'National Level Hunter', 'Monarch']:
                        participants.append(user)
                    elif event_type == "continent_boss" and hunter['rank'] in ['A', 'S', 'National Level Hunter', 'Monarch']:
                        participants.append(user)
                    elif event_type == "red_gate" and hunter['rank'] in ['B', 'A', 'S', 'National Level Hunter', 'Monarch']:
                        participants.append(user)

                # Check minimum participants for harder events
                min_participants = {
                    'mini_boss': 1,
                    'country_boss': 3,
                    'continent_boss': 5,
                    'red_gate': 2
                }

                if len(participants) < min_participants[event_type]:
                    cancel_embed = discord.Embed(
                        title="❌ Event Cancelled",
                        description=f"Not enough qualified hunters joined! Need at least {min_participants[event_type]} participants.",
                        color=discord.Color.red()
                    )
                    await message.channel.send(embed=cancel_embed)
                    self.active_event = None
                    return

                self.event_participants = set(participants)
                
                # Select boss for the event
                bosses_key = f"{event_type}_bosses" if event_type != "mini_boss" else "mini_bosses"
                bosses = SOLO_LEVELING_BOSSES.get(bosses_key, [])
                
                if not bosses:
                    await message.channel.send("⚠️ No bosses available for this event type.")
                    self.active_event = None
                    return

                boss_data = random.choice(bosses)
                self.active_event['data'] = boss_data

                await self.start_event_for_participants()
                
        except Exception as e:
            print(f"[ERROR] Error waiting for event join: {e}")
            await self.cancel_event("An error occurred during event setup.")

    async def start_event_for_participants(self):
        """Start the event for all participants"""
        try:
            if not self.active_event:
                return
                
            participants = list(self.event_participants)
            boss_data = self.active_event['data']
            channel = self.active_event['channel']
            
            # Send success message
            success_embed = discord.Embed(
                title="✅ Event Channels Created!",
                description=f"Individual battle channels have been created for {len(participants)} hunters.\n\nGood luck in your battles!",
                color=discord.Color.green()
            )
            await channel.send(embed=success_embed)
            
            # Create individual combat channels for each participant
            for participant in participants:
                try:
                    await self.create_event_combat_channel(participant, boss_data)
                except Exception as e:
                    print(f"Error creating channel for {participant.display_name}: {e}")
            
            # Set event start time for duration tracking
            self.event_start_time = time.time()
            
            # Schedule event end
            asyncio.create_task(self.schedule_event_end())
            
        except Exception as e:
            print(f"[ERROR] Error starting event: {e}")
            await self.cancel_event("Failed to start event properly.")

    async def schedule_event_end(self):
        """Schedule the end of the current event"""
        await asyncio.sleep(3600)  # 1 hour event duration
        await self.end_event()

    async def end_event(self):
        """End the current event"""
        if not self.active_event:
            return
            
        try:
            # Clear event data
            self.active_event = None
            self.event_participants.clear()
            self.participant_channels.clear()
            self.event_battles.clear()
            
            # Clean up hunter data
            hunters_data = self.load_hunters_data()
            for user_id in hunters_data:
                if 'event_battle' in hunters_data[user_id]:
                    del hunters_data[user_id]['event_battle']
            self.save_hunters_data(hunters_data)
            
            print("[INFO] Global event ended successfully")
            
        except Exception as e:
            print(f"[ERROR] Error ending event: {e}")

    async def cancel_event(self, reason):
        """Cancel the current event"""
        if self.active_event:
            try:
                channel = self.active_event['channel']
                cancel_embed = discord.Embed(
                    title="❌ Event Cancelled",
                    description=reason,
                    color=discord.Color.red()
                )
                await channel.send(embed=cancel_embed)
            except:
                pass
            
            await self.end_event()

    def add_rank_announcement(self, hunter_name, new_rank, level, progress_info):
        """Add a rank announcement to be displayed"""
        self.rank_announcements.append({
            'hunter_name': hunter_name,
            'new_rank': new_rank,
            'level': level,
            'progress_info': progress_info,
            'timestamp': time.time()
        })

    @commands.command(name='summon_event')
    @commands.has_permissions(administrator=True)
    async def summon_event_command(self, ctx, event_type: str):
        """Manually trigger a global event"""
        if self.active_event:
            await ctx.send("❌ There's already an active event!")
            return
            
        event_types = ['mini_boss', 'country_boss', 'continent_boss', 'red_gate']
        if event_type not in event_types:
            await ctx.send(f"❌ Invalid event type! Use: {', '.join(event_types)}")
            return

        event_names = {
            'mini_boss': '⚔️ Mini Boss Has Appeared!',
            'country_boss': '🌍 Country-Level Threat!',
            'continent_boss': '🌐 Continent-Level Threat!',
            'red_gate': '🩸 ??? Red Gate Has Opened!'
        }

        embed = discord.Embed(
            title=event_names[event_type],
            description="React with ✅ to join or ❌ to skip. Event starts in 60 seconds.",
            color=discord.Color.red()
        )
        embed.set_footer(text="Be prepared, hunter.")

        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")

        self.active_event = {
            'type': event_type,
            'message': message,
            'channel': ctx.channel,
            'data': None
        }

        await self.wait_for_event_join(message, event_type)

    @commands.command(name='end_event')
    @commands.has_permissions(administrator=True)
    async def end_event_command(self, ctx):
        """Manually end the current event"""
        if not self.active_event:
            await ctx.send("❌ No active event to end!")
            return
            
        await self.end_event()
        await ctx.send("✅ Event ended successfully!")

    async def before_event_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    cog = GlobalEvents(bot)
    await bot.add_cog(cog)
    # Start the event loop
    bot.loop.create_task(cog.event_loop())