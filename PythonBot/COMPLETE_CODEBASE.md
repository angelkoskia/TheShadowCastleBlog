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

## 📋 Core Commands & Modern UI

All commands use modern Discord UI components:
- Embeds for all information displays
- Buttons for interactive responses (combat, party, inventory, etc.)
- Select Menus for item/target selection
- Modal Forms for complex input
- Auto-updating messages for real-time battle/status

### Player & System Commands
- `.awaken` - Begin your hunter journey (one-time, at awakening-gate)
- `.status` - View hunter profile and stats
- `.inventory` - Manage and sort through items
- `.use <name>` - Use consumable item
- `.equip <name>` / `.unequip <name>` - Equip/unequip gear
- `.ability <name>` - Use an ability/skill
- `.daily` - Claim daily rewards
- `.dailyquest` - View daily quests
- `.shop` - Visit hunter shop
- `.topserver` - View top players and arena ranks
- `.rank` - View experience progress bar

### Gates, Dungeons, and Combat
- `.viewgates` - View available dimensional gates
- `.viewredgates` - View known red gates
- `.entergate <name>` / `.enterredgate <name>` - Enter a gate
- `.exitgate` - Exit current gate (special rules for red gates)
- `.dungeons` - View dungeon raids
- `.enterdungeon <name>` / `.exitdungeon` - Enter/flee dungeon (party leader only)
- `.hunt` - Start hunting monsters (in gate/dungeon)
- `.attack` / `.defend` / `.dodge` / `.flee` - Combat actions (contextual)

### Party, Co-Op, and Guild
- `.startparty @user ...` - Start a party (interactive invites)
- `.accept` / `.decline` / `.refuse` - Respond to invites or party actions
- `.finished` - Mark turn complete in party/guild combat
- `.guildwar` - Initiate guild vs guild combat
- `.guildraid <name>` - Guild-wide gate/dungeon raid

### PvP & Arena
- `.pvp @user` - Challenge another hunter
- `.accept` / `.decline` - Respond to PvP challenge

### Shadow Army (Restricted)
- `.shadows` - Manage shadow army (only for necromancer class, restricted to SJW)

## 🏗️ Key Features

### Modern UI Implementation
- All systems use Discord embeds, buttons, select menus, and modals
- Real-time, auto-updating messages for battles and status
- Seamless party/guild/coop UI with automatic stat displays and turn tracking

### Party & Co-Op System (Finished)
- Interactive party creation and invites
- Party combat with automatic stats display and turn progression
- All members can prepare actions; turn progresses when all use `.finished`
- Auto-disband after each battle

### Guild System (Finished)
- Guild vs guild combat with member matching
- Guild-wide raids for gates, red gates, and dungeons
- Party formation and turn handling as in co-op

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
- 7-tier grading, extraction, upgrades, and abilities
- Only accessible to necromancer class (SJW only)

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

## ✅ Feature Status
All features listed above are fully implemented and working as of 2025-06-11, including:
- Modern UI for all commands
- Party, co-op, and guild systems
- Gate, dungeon, and combat mechanics
- PvP and leaderboard
- Shadow army (restricted)
- Data persistence and web dashboard

For any issues, consult the FEATURES_DOCUMENTATION.txt or the respective cog/module.
