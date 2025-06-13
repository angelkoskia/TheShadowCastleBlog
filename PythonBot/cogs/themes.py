import discord
from discord.ext import commands
import json

class Themes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.default_themes = self.get_default_themes()
    
    def get_default_themes(self):
        """Default theme configurations"""
        return {
            "dark": {
                "name": "Dark Minimalist",
                "primary": 0x2C2F33,      # Dark gray
                "secondary": 0x23272A,    # Darker gray
                "accent": 0x7289DA,       # Discord blurple
                "success": 0x43B581,      # Green
                "warning": 0xFAA61A,      # Yellow
                "error": 0xF04747,        # Red
                "info": 0x3498DB          # Blue
            },
            "purple": {
                "name": "Purple Dark",
                "primary": 0x2C2F33,
                "secondary": 0x23272A,
                "accent": 0x9B59B6,       # Purple
                "success": 0x27AE60,
                "warning": 0xF39C12,
                "error": 0xE74C3C,
                "info": 0x8E44AD
            },
            "cyan": {
                "name": "Cyan Dark",
                "primary": 0x2C2F33,
                "secondary": 0x23272A,
                "accent": 0x1ABC9C,       # Cyan
                "success": 0x2ECC71,
                "warning": 0xF1C40F,
                "error": 0xE67E22,
                "info": 0x3498DB
            },
            "red": {
                "name": "Red Dark",
                "primary": 0x2C2F33,
                "secondary": 0x23272A,
                "accent": 0xE74C3C,       # Red
                "success": 0x27AE60,
                "warning": 0xF39C12,
                "error": 0xC0392B,
                "info": 0x3498DB
            },
            "gold": {
                "name": "Gold Dark",
                "primary": 0x2C2F33,
                "secondary": 0x23272A,
                "accent": 0xF1C40F,       # Gold
                "success": 0x27AE60,
                "warning": 0xE67E22,
                "error": 0xE74C3C,
                "info": 0x3498DB
            }
        }
    
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
    
    def get_user_theme(self, user_id):
        """Get user's selected theme or default"""
        hunters_data = self.load_hunters_data()
        user_data = hunters_data.get(str(user_id), {})
        theme_name = user_data.get('theme', 'dark')
        return self.default_themes.get(theme_name, self.default_themes['dark'])
    
    def get_themed_color(self, user_id, color_type='accent'):
        """Get themed color for a specific type"""
        theme = self.get_user_theme(user_id)
        return discord.Color(theme.get(color_type, theme['accent']))
    
    @commands.command(name='themes')
    async def show_themes(self, ctx):
        """Display available themes"""
        embed = discord.Embed(
            title="🎨 Available Themes",
            description="Choose your preferred color theme for the bot interface",
            color=self.get_themed_color(ctx.author.id, 'accent')
        )
        
        current_theme = self.get_user_theme(ctx.author.id)['name']
        embed.add_field(
            name="Current Theme",
            value=f"**{current_theme}**",
            inline=False
        )
        
        themes_text = ""
        for theme_id, theme_data in self.default_themes.items():
            indicator = "🔹" if theme_data['name'] == current_theme else "▫️"
            themes_text += f"{indicator} **{theme_id}** - {theme_data['name']}\n"
        
        embed.add_field(
            name="Available Themes",
            value=themes_text,
            inline=False
        )
        
        embed.add_field(
            name="Usage",
            value="Use `.set_theme <theme_name>` to change your theme\nExample: `.set_theme purple`",
            inline=False
        )
        
        embed.set_footer(text="Themes apply to all bot interactions")
        await ctx.send(embed=embed)
    
    @commands.command(name='set_theme')
    async def set_theme(self, ctx, theme_name: str = ""):
        """Set user's preferred theme"""
        if not theme_name:
            await ctx.send("Please specify a theme name! Use `.themes` to see available options.")
            return
        
        theme_name = theme_name.lower()
        if theme_name not in self.default_themes:
            available = ", ".join(self.default_themes.keys())
            await ctx.send(f"Theme '{theme_name}' not found! Available themes: {available}")
            return
        
        hunters_data = self.load_hunters_data()
        user_id = str(ctx.author.id)
        
        if user_id not in hunters_data:
            await ctx.send("You need to start your journey first! Use `.start`")
            return
        
        hunters_data[user_id]['theme'] = theme_name
        self.save_hunters_data(hunters_data)
        
        theme = self.default_themes[theme_name]
        embed = discord.Embed(
            title="🎨 Theme Updated!",
            description=f"Your theme has been changed to **{theme['name']}**",
            color=discord.Color(theme['accent'])
        )
        
        # Show color preview
        color_preview = (
            f"🔹 Primary: #{theme['primary']:06x}\n"
            f"🔸 Accent: #{theme['accent']:06x}\n"
            f"✅ Success: #{theme['success']:06x}\n"
            f"⚠️ Warning: #{theme['warning']:06x}\n"
            f"❌ Error: #{theme['error']:06x}"
        )
        
        embed.add_field(
            name="Color Preview",
            value=color_preview,
            inline=True
        )
        
        embed.set_footer(text="Your new theme will apply to all future bot interactions")
        await ctx.send(embed=embed)
    
    @commands.command(name='preview_theme')
    async def preview_theme(self, ctx, theme_name: str = ""):
        """Preview a theme without setting it"""
        if not theme_name:
            await ctx.send("Please specify a theme name to preview!")
            return
        
        theme_name = theme_name.lower()
        if theme_name not in self.default_themes:
            available = ", ".join(self.default_themes.keys())
            await ctx.send(f"Theme '{theme_name}' not found! Available themes: {available}")
            return
        
        theme = self.default_themes[theme_name]
        
        # Create preview embed with theme colors
        embed = discord.Embed(
            title=f"🎨 Theme Preview: {theme['name']}",
            description="This is how your interface will look with this theme",
            color=discord.Color(theme['accent'])
        )
        
        # Sample content with different color types
        embed.add_field(
            name="🏆 Sample Victory",
            value="You defeated the Goblin Scout!\n💰 25 Gold • ⭐ 50 EXP",
            inline=False
        )
        
        embed.add_field(
            name="⚔️ Sample Battle",
            value="You attack for 45 damage!\nMonster HP: 15/60",
            inline=True
        )
        
        embed.add_field(
            name="💰 Sample Shop",
            value="Health Potion - 50 gold\nIron Sword - 100 gold",
            inline=True
        )
        
        # Color showcase
        color_info = (
            f"**Color Palette:**\n"
            f"Primary: #{theme['primary']:06x}\n"
            f"Accent: #{theme['accent']:06x}\n"
            f"Success: #{theme['success']:06x}\n"
            f"Warning: #{theme['warning']:06x}\n"
            f"Error: #{theme['error']:06x}"
        )
        
        embed.add_field(
            name="🎨 Colors",
            value=color_info,
            inline=False
        )
        
        embed.set_footer(text=f"Use '.set_theme {theme_name}' to apply this theme")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Themes(bot))