# PythonBot: Solo Leveling RPG Discord Bot

A feature-rich Discord bot inspired by the Solo Leveling universe. Includes leveling, ranking, quests, dungeons, and more, with a focus on extensibility and maintainability.

## Features
- Leveling and rank system based on Solo Leveling lore
- Themed embeds and color utilities
- Daily and weekly quests
- Dungeon and encounter management
- Modular cog-based architecture

## Setup
1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   ```
2. **Install dependencies:**
   Ensure you have Python 3.11+ and run:
   ```bash
   pip install -r requirements.txt
   ```
   Or use the dependencies in `pyproject.toml`.
3. **Configure environment:**
   - Create a `.env` file with your Discord bot token and any other required secrets.

4. **Run the bot:**
   ```bash
   python main.py
   ```

## Project Structure
- `main.py` - Entry point for the bot
- `utils/` - Utility modules (leveling, themes, etc.)
- `cogs/` - Modular bot features
- `data/` - Static and dynamic data files
- `attached_assets/` - Images and text assets

## Contributing
Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## License
MIT License

