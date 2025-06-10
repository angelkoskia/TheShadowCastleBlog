# Solo Leveling RPG Discord Bot - Complete Codebase

## 📁 File Structure
```
solo-leveling-rpg-bot/
├── main.py                     # Core bot functionality and commands
├── daily_quest_system.py       # Quest system with progress tracking
├── hunters_data.json          # Player data storage (auto-generated)
├── cogs/                      # Command modules
│   ├── gates.py              # Gate exploration system
│   ├── inventory.py          # Item and equipment management
│   ├── shop.py               # Shopping and trading system
│   ├── pvp_system.py         # Player vs Player combat
│   ├── shadow_army.py        # Shadow extraction and army management
│   └── dungeon_raids.py      # Multi-floor dungeon system
├── data/                     # Game configuration files
│   ├── monsters.json         # Monster database
│   ├── gates.json           # Gate configuration
│   ├── items.json           # Item and equipment data
│   ├── shadow_grades.json   # Shadow grading system
│   └── quests.json          # Quest templates
└── dashboard/               # Web dashboard
    ├── server.js            # Express.js server
    ├── package.json         # Node.js dependencies
    └── views/
        └── dashboard.ejs    # Dashboard template
```

## 🚀 Quick Setup

### Prerequisites
- Python 3.8+
- Node.js 14+
- Discord Bot Token

### Installation
1. Install Python dependencies:
```bash
pip install discord.py
```

2. Install Node.js dependencies:
```bash
cd dashboard
npm install express ejs body-parser cors
```

3. Set environment variable:
```bash
export DISCORD_BOT_TOKEN="your_discord_bot_token"
```

4. Run the bot:
```bash
python main.py
```

5. Run web dashboard (optional):
```bash
cd dashboard && node server.js
```

## 📋 Core Commands

### Player Commands
- `.awaken` - Begin your hunter journey
- `.status` - View hunter profile and stats
- `.hunt` - Start hunting monsters
- `.attack` - Attack current monster
- `.defend` - Defensive battle stance
- `.flee` - Escape from battle

### Advanced Features
- `.gates` - View available dimensional gates
- `.enter_gate <name>` - Enter gate exploration
- `.dungeons` - View dungeon raids
- `.shadows` - Manage shadow army
- `.pvp @user` - Challenge another hunter
- `.daily` - View daily quests
- `.shop` - Visit hunter shop
- `.inventory` - Manage items

## 🏗️ Key Features

### Battle System
- Persistent battle data stored in player profiles
- Real-time combat with strategic choices
- Experience and gold rewards
- Level progression with stat increases

### Quest System
- Daily and weekly quest rotation
- Progress tracking across sessions
- Reward claiming system
- Automatic quest reset

### Shadow Army
- 7-tier shadow grading system (Normal to National Treasure)
- Shadow extraction from defeated monsters
- Army management and upgrades
- Special shadow abilities

### PvP System
- Player vs player combat
- Monarch ranking system
- Tournament brackets
- Leaderboard tracking

### Web Dashboard
- Real-time player statistics
- Administrative controls
- Data visualization
- Player management

## 💾 Data Persistence
All player data is automatically saved to `hunters_data.json` with:
- Battle states persist through bot restarts
- Quest progress tracking
- Inventory and equipment
- Shadow army composition
- PvP statistics and rankings

## 🔧 Configuration
Game balance and content can be modified through JSON files in the `data/` directory without code changes.
