"""Theme utility functions for the Solo Leveling RPG bot"""

import discord

# Centralized color palette for the bot
THEME_COLORS = {
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

RANK_COLORS = {
    'E': 0x6B7280,    # Gray
    'D': 0x84CC16,    # Lime
    'C': 0x3B82F6,    # Blue
    'B': 0x8B5CF6,    # Violet
    'A': 0xF59E0B,    # Amber
    'S': 0xEF4444,    # Red
    'National': 0x1F2937  # Nearly black
}

RARITY_COLORS = {
    'common': 0x6B7280,     # Gray
    'uncommon': 0x84CC16,   # Lime
    'rare': 0x3B82F6,       # Blue
    'epic': 0x8B5CF6,       # Violet
    'legendary': 0xF59E0B,  # Amber
    'mythic': 0xEF4444      # Red
}

def get_user_theme_colors(user_id):
    """Get theme colors for a user (expandable for user preferences)."""
    return THEME_COLORS

def get_rank_color(rank):
    """Get color based on hunter rank."""
    return RANK_COLORS.get(rank, RANK_COLORS['E'])

def get_difficulty_color(difficulty):
    """Get color based on gate/dungeon difficulty (uses rank colors)."""
    return get_rank_color(difficulty)

def get_rarity_color(rarity):
    """Get color based on item rarity."""
    return RARITY_COLORS.get(rarity.lower(), RARITY_COLORS['common'])

def get_error_embed(title, description):
    """Create error embed with consistent styling."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=THEME_COLORS['error']
    )
    return embed

def get_info_embed(title, description):
    """Create info embed with consistent styling."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=THEME_COLORS['info']
    )
    return embed

def create_progress_bar(current, maximum, length=10):
    """Create a text-based progress bar for Discord messages."""
    filled_length = int(length * current // maximum)
    bar = '█' * filled_length + '-' * (length - filled_length)
    return f"[{bar}] {current}/{maximum}"
