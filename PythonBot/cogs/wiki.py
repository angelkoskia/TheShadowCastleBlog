import discord
from discord.ext import commands
import json
import random
from typing import Dict, List, Optional

class WikiView(discord.ui.View):
    """Interactive wiki navigation view"""
    
    def __init__(self, wiki_data: dict, current_category: str = None, current_entry: str = None):
        super().__init__(timeout=300)
        self.wiki_data = wiki_data
        self.current_category = current_category
        self.current_entry = current_entry
        
        # Add navigation buttons based on current state
        if current_entry:
            self.add_item(BackButton())
            self.add_item(RelatedEntriesSelect(wiki_data, current_entry))
        elif current_category:
            self.add_item(BackToCategoriesButton())
            self.add_item(EntrySelect(wiki_data[current_category]))
        else:
            self.add_item(CategorySelect(wiki_data))
        
        self.add_item(SearchButton())

class CategorySelect(discord.ui.Select):
    """Category selection dropdown"""
    
    def __init__(self, wiki_data: dict):
        options = []
        category_emojis = {
            'hunters': '🏹',
            'monarchs': '👑',
            'dungeons': '🏰',
            'organizations': '🏛️',
            'system': '⚙️',
            'concepts': '📚'
        }
        
        for category in wiki_data.keys():
            emoji = category_emojis.get(category, '📖')
            options.append(discord.SelectOption(
                label=category.replace('_', ' ').title(),
                value=category,
                emoji=emoji,
                description=f"Browse {category.replace('_', ' ')} entries"
            ))
        
        super().__init__(placeholder="Select a category...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        wiki_cog = interaction.client.get_cog('Wiki')
        await wiki_cog.show_category(interaction, self.values[0])

class EntrySelect(discord.ui.Select):
    """Entry selection dropdown for a specific category"""
    
    def __init__(self, category_data: dict):
        options = []
        for entry_key, entry_data in category_data.items():
            options.append(discord.SelectOption(
                label=entry_data['title'],
                value=entry_key,
                description=entry_data.get('category', 'Entry')[:100]
            ))
        
        super().__init__(placeholder="Select an entry...", options=options[:25])  # Discord limit
    
    async def callback(self, interaction: discord.Interaction):
        wiki_cog = interaction.client.get_cog('Wiki')
        await wiki_cog.show_entry(interaction, self.values[0])

class RelatedEntriesSelect(discord.ui.Select):
    """Related entries dropdown"""
    
    def __init__(self, wiki_data: dict, current_entry: str):
        options = []
        
        # Find current entry in all categories
        entry_data = None
        for category_data in wiki_data.values():
            if current_entry in category_data:
                entry_data = category_data[current_entry]
                break
        
        if entry_data and 'related_entries' in entry_data:
            for related_key in entry_data['related_entries'][:20]:  # Limit options
                # Find the related entry
                for category_data in wiki_data.values():
                    if related_key in category_data:
                        related_data = category_data[related_key]
                        options.append(discord.SelectOption(
                            label=related_data['title'],
                            value=related_key,
                            description=related_data.get('category', 'Related')[:100]
                        ))
                        break
        
        if not options:
            options.append(discord.SelectOption(
                label="No related entries",
                value="none",
                description="This entry has no related links"
            ))
        
        super().__init__(placeholder="View related entries...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] != "none":
            wiki_cog = interaction.client.get_cog('Wiki')
            await wiki_cog.show_entry(interaction, self.values[0])

class BackButton(discord.ui.Button):
    """Back navigation button"""
    
    def __init__(self):
        super().__init__(label="Back to Category", style=discord.ButtonStyle.secondary, emoji="⬅️")
    
    async def callback(self, interaction: discord.Interaction):
        wiki_cog = interaction.client.get_cog('Wiki')
        await wiki_cog.show_categories(interaction)

class BackToCategoriesButton(discord.ui.Button):
    """Back to categories button"""
    
    def __init__(self):
        super().__init__(label="All Categories", style=discord.ButtonStyle.secondary, emoji="🏠")
    
    async def callback(self, interaction: discord.Interaction):
        wiki_cog = interaction.client.get_cog('Wiki')
        await wiki_cog.show_categories(interaction)

class SearchButton(discord.ui.Button):
    """Search button"""
    
    def __init__(self):
        super().__init__(label="Search", style=discord.ButtonStyle.primary, emoji="🔍")
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SearchModal())

class SearchModal(discord.ui.Modal):
    """Search modal for wiki entries"""
    
    def __init__(self):
        super().__init__(title="Search Solo Leveling Wiki")
        
        self.search_input = discord.ui.TextInput(
            label="Search Term",
            placeholder="Enter character, location, or concept name...",
            required=True,
            max_length=100
        )
        self.add_item(self.search_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        wiki_cog = interaction.client.get_cog('Wiki')
        await wiki_cog.search_wiki(interaction, self.search_input.value)

class Wiki(commands.Cog):
    """Solo Leveling Wiki system with comprehensive lore information"""
    
    def __init__(self, bot):
        self.bot = bot
        self.wiki_data = self.load_wiki_data()
    
    def load_wiki_data(self) -> dict:
        """Load wiki data from JSON file"""
        try:
            with open('data/wiki_data.json', 'r') as f:
                data = json.load(f)
                return data.get('wiki_entries', {})
        except FileNotFoundError:
            return {}
    
    @commands.command(name='wiki', aliases=['w', 'lore'])
    async def wiki_command(self, ctx, *, search_term: str = None):
        """Access the Solo Leveling wiki
        
        Usage:
        .wiki - Browse all categories
        .wiki <search> - Search for specific entry
        """
        if search_term:
            await self.search_wiki_command(ctx, search_term)
        else:
            await self.show_categories_command(ctx)
    
    async def show_categories_command(self, ctx):
        """Show main wiki categories"""
        embed = discord.Embed(
            title="📖 Solo Leveling Wiki",
            description="Comprehensive database of Solo Leveling lore, characters, and concepts",
            color=discord.Color.gold()
        )
        
        category_info = {
            'hunters': ('🏹 Hunters', 'S-Rank hunters, National Level hunters, and notable awakened beings'),
            'monarchs': ('👑 Monarchs', 'The eight rulers who wage war against humanity and the Rulers'),
            'dungeons': ('🏰 Dungeons & Gates', 'Notable dungeons, gates, and raid locations'),
            'organizations': ('🏛️ Organizations', 'Hunter associations, guilds, and governing bodies'),
            'system': ('⚙️ The System', 'Game mechanics, leveling system, and divine artifacts'),
            'concepts': ('📚 Core Concepts', 'Mana, gates, awakening, and fundamental world mechanics')
        }
        
        for category, (title, desc) in category_info.items():
            if category in self.wiki_data:
                entry_count = len(self.wiki_data[category])
                embed.add_field(
                    name=title,
                    value=f"{desc}\n*{entry_count} entries*",
                    inline=True
                )
        
        embed.set_footer(text="Use the dropdown to browse categories or search for specific entries")
        
        view = WikiView(self.wiki_data)
        await ctx.send(embed=embed, view=view)
    
    async def show_categories(self, interaction: discord.Interaction):
        """Show categories via interaction"""
        embed = discord.Embed(
            title="📖 Solo Leveling Wiki",
            description="Comprehensive database of Solo Leveling lore, characters, and concepts",
            color=discord.Color.gold()
        )
        
        category_info = {
            'hunters': ('🏹 Hunters', 'S-Rank hunters, National Level hunters, and notable awakened beings'),
            'monarchs': ('👑 Monarchs', 'The eight rulers who wage war against humanity and the Rulers'),
            'dungeons': ('🏰 Dungeons & Gates', 'Notable dungeons, gates, and raid locations'),
            'organizations': ('🏛️ Organizations', 'Hunter associations, guilds, and governing bodies'),
            'system': ('⚙️ The System', 'Game mechanics, leveling system, and divine artifacts'),
            'concepts': ('📚 Core Concepts', 'Mana, gates, awakening, and fundamental world mechanics')
        }
        
        for category, (title, desc) in category_info.items():
            if category in self.wiki_data:
                entry_count = len(self.wiki_data[category])
                embed.add_field(
                    name=title,
                    value=f"{desc}\n*{entry_count} entries*",
                    inline=True
                )
        
        view = WikiView(self.wiki_data)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_category(self, interaction: discord.Interaction, category: str):
        """Show entries in a specific category"""
        if category not in self.wiki_data:
            await interaction.response.send_message("Category not found!", ephemeral=True)
            return
        
        category_data = self.wiki_data[category]
        category_name = category.replace('_', ' ').title()
        
        embed = discord.Embed(
            title=f"📚 {category_name}",
            description=f"Browse {len(category_data)} entries in this category",
            color=discord.Color.blue()
        )
        
        # Show up to 10 entries in the embed
        entry_list = []
        for entry_key, entry_data in list(category_data.items())[:10]:
            title = entry_data['title']
            category_label = entry_data.get('category', 'Unknown')
            entry_list.append(f"**{title}** - {category_label}")
        
        if entry_list:
            embed.add_field(
                name="Available Entries",
                value="\n".join(entry_list),
                inline=False
            )
        
        if len(category_data) > 10:
            embed.add_field(
                name="",
                value=f"*...and {len(category_data) - 10} more entries*",
                inline=False
            )
        
        view = WikiView(self.wiki_data, current_category=category)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_entry(self, interaction: discord.Interaction, entry_key: str):
        """Show detailed information about a specific entry"""
        # Find the entry in all categories
        entry_data = None
        entry_category = None
        
        for category, category_data in self.wiki_data.items():
            if entry_key in category_data:
                entry_data = category_data[entry_key]
                entry_category = category
                break
        
        if not entry_data:
            await interaction.response.send_message("Entry not found!", ephemeral=True)
            return
        
        # Create detailed embed
        embed = discord.Embed(
            title=entry_data['title'],
            description=entry_data.get('description', 'No description available'),
            color=discord.Color.purple()
        )
        
        # Add category badge
        if 'category' in entry_data:
            embed.add_field(
                name="Category",
                value=entry_data['category'],
                inline=True
            )
        
        # Add aliases if available
        if 'aliases' in entry_data and entry_data['aliases']:
            embed.add_field(
                name="Also Known As",
                value=", ".join(entry_data['aliases']),
                inline=True
            )
        
        # Add rank if available
        if 'rank' in entry_data:
            embed.add_field(
                name="Rank",
                value=entry_data['rank'],
                inline=True
            )
        
        # Add abilities if available
        if 'abilities' in entry_data and entry_data['abilities']:
            abilities_text = "\n".join([f"• {ability}" for ability in entry_data['abilities'][:5]])
            if len(entry_data['abilities']) > 5:
                abilities_text += f"\n*...and {len(entry_data['abilities']) - 5} more*"
            embed.add_field(
                name="Abilities",
                value=abilities_text,
                inline=False
            )
        
        # Add notable achievements if available
        if 'notable_achievements' in entry_data and entry_data['notable_achievements']:
            achievements_text = "\n".join([f"• {achievement}" for achievement in entry_data['notable_achievements'][:3]])
            if len(entry_data['notable_achievements']) > 3:
                achievements_text += f"\n*...and {len(entry_data['notable_achievements']) - 3} more*"
            embed.add_field(
                name="Notable Achievements",
                value=achievements_text,
                inline=False
            )
        
        # Add other relevant fields dynamically
        skip_fields = {'title', 'description', 'category', 'aliases', 'rank', 'abilities', 'notable_achievements', 'related_entries'}
        for key, value in entry_data.items():
            if key not in skip_fields and value:
                if isinstance(value, list):
                    if len(value) <= 3:
                        field_value = "\n".join([f"• {item}" for item in value])
                    else:
                        field_value = "\n".join([f"• {item}" for item in value[:3]])
                        field_value += f"\n*...and {len(value) - 3} more*"
                else:
                    field_value = str(value)
                
                field_name = key.replace('_', ' ').title()
                embed.add_field(
                    name=field_name,
                    value=field_value[:1024],  # Discord limit
                    inline=len(field_value) < 100
                )
        
        # Add footer with related entries count
        if 'related_entries' in entry_data:
            embed.set_footer(text=f"Related entries: {len(entry_data['related_entries'])}")
        
        view = WikiView(self.wiki_data, current_entry=entry_key)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def search_wiki(self, interaction: discord.Interaction, search_term: str):
        """Search wiki entries"""
        search_term = search_term.lower()
        results = []
        
        # Search through all entries
        for category, category_data in self.wiki_data.items():
            for entry_key, entry_data in category_data.items():
                # Search in title, aliases, and description
                if (search_term in entry_data['title'].lower() or
                    search_term in entry_key.lower() or
                    search_term in entry_data.get('description', '').lower() or
                    any(search_term in alias.lower() for alias in entry_data.get('aliases', []))):
                    
                    results.append((entry_key, entry_data, category))
        
        if not results:
            embed = discord.Embed(
                title="🔍 Search Results",
                description=f"No entries found for '{search_term}'",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create results embed
        embed = discord.Embed(
            title="🔍 Search Results",
            description=f"Found {len(results)} entries for '{search_term}'",
            color=discord.Color.green()
        )
        
        # Show top 10 results
        for entry_key, entry_data, category in results[:10]:
            category_name = category.replace('_', ' ').title()
            description = entry_data.get('description', 'No description')[:100]
            if len(entry_data.get('description', '')) > 100:
                description += "..."
            
            embed.add_field(
                name=f"{entry_data['title']} ({category_name})",
                value=description,
                inline=False
            )
        
        if len(results) > 10:
            embed.add_field(
                name="",
                value=f"*...and {len(results) - 10} more results*",
                inline=False
            )
        
        view = WikiView(self.wiki_data)
        await interaction.response.send_message(embed=embed, view=view)
    
    async def search_wiki_command(self, ctx, search_term: str):
        """Search wiki entries via command"""
        search_term = search_term.lower()
        results = []
        
        # Search through all entries
        for category, category_data in self.wiki_data.items():
            for entry_key, entry_data in category_data.items():
                # Search in title, aliases, and description
                if (search_term in entry_data['title'].lower() or
                    search_term in entry_key.lower() or
                    search_term in entry_data.get('description', '').lower() or
                    any(search_term in alias.lower() for alias in entry_data.get('aliases', []))):
                    
                    results.append((entry_key, entry_data, category))
        
        if not results:
            embed = discord.Embed(
                title="🔍 Search Results",
                description=f"No entries found for '{search_term}'",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Create results embed
        embed = discord.Embed(
            title="🔍 Search Results",
            description=f"Found {len(results)} entries for '{search_term}'",
            color=discord.Color.green()
        )
        
        # Show top 10 results
        for entry_key, entry_data, category in results[:10]:
            category_name = category.replace('_', ' ').title()
            description = entry_data.get('description', 'No description')[:100]
            if len(entry_data.get('description', '')) > 100:
                description += "..."
            
            embed.add_field(
                name=f"{entry_data['title']} ({category_name})",
                value=description,
                inline=False
            )
        
        if len(results) > 10:
            embed.add_field(
                name="",
                value=f"*...and {len(results) - 10} more results*",
                inline=False
            )
        
        view = WikiView(self.wiki_data)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Wiki(bot))