"""Theme utility functions for the Solo Leveling RPG bot"""

import discord

def get_user_theme_colors(user_id):
    """Get theme colors for a user (can be expanded for user preferences later)"""
    return {
        'primary': 0x7C3AED,      # Purple
        'secondary': 0x3B82F6,    # Blue  
        'accent': 0xF59E0B,       # Amber
        'success': 0x10B981,      # Emerald
        'error': 0xEF4444,        # Red
        'warning': 0xF59E0B,      # Amber
        'info': 0x3B82F6,         # Blue
        'dark': 0x1F2937,         # Gray-800
        'light': 0xF9FAFB         # Gray-50
    }

def get_rank_color(rank):
    """Get color based on hunter rank"""
    rank_colors = {
        'E': 0x6B7280,    # Gray
        'D': 0x84CC16,    # Lime
        'C': 0x3B82F6,    # Blue
        'B': 0x8B5CF6,    # Violet
        'A': 0xF59E0B,    # Amber
        'S': 0xEF4444,    # Red
        'National': 0x1F2937  # Nearly black
    }
    return rank_colors.get(rank, 0x6B7280)

def get_difficulty_color(difficulty):
    """Get color based on gate/dungeon difficulty"""
    return get_rank_color(difficulty)

def get_rarity_color(rarity):
    """Get color based on item rarity"""
    rarity_colors = {
        'common': 0x6B7280,     # Gray
        'uncommon': 0x84CC16,   # Lime
        'rare': 0x3B82F6,       # Blue
        'epic': 0x8B5CF6,       # Violet
        'legendary': 0xF59E0B,  # Amber
        'mythic': 0xEF4444      # Red
    }
    return rarity_colors.get(rarity.lower(), 0x6B7280)

def get_error_embed(title, description):
    """Create error embed with consistent styling"""
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=0xEF4444  # Red
    )
    return embed

def get_info_embed(title, description):
    """Create info embed with consistent styling"""
    embed = discord.Embed(
        title=f"ℹ️ {title}",
        description=description,
        color=0x3B82F6  # Blue
    )
    return embed

def create_progress_bar(current, maximum, length=10):
    """Create a visual progress bar"""
    if maximum <= 0:
        return "▱" * length
    
    filled = int((current / maximum) * length)
    filled = max(0, min(filled, length))
    empty = length - filled
    
    bar = "▰" * filled + "▱" * empty
    return f"{bar} {current}/{maximum}"