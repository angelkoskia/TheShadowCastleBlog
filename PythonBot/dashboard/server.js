const express = require('express');
const path = require('path');
const fs = require('fs');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));

// Set EJS as template engine
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Helper function to load hunters data
function loadHuntersData() {
    try {
        const data = fs.readFileSync(path.join(__dirname, '..', 'hunters_data.json'), 'utf8');
        return JSON.parse(data);
    } catch (error) {
        console.error('Error loading hunters data:', error);
        return {};
    }
}

// Helper function to save hunters data
function saveHuntersData(data) {
    try {
        fs.writeFileSync(
            path.join(__dirname, '..', 'hunters_data.json'),
            JSON.stringify(data, null, 4)
        );
        return true;
    } catch (error) {
        console.error('Error saving hunters data:', error);
        return false;
    }
}

// Helper function to load game data files
function loadGameData(filename) {
    try {
        const data = fs.readFileSync(path.join(__dirname, '..', 'data', filename), 'utf8');
        return JSON.parse(data);
    } catch (error) {
        console.error(`Error loading ${filename}:`, error);
        return {};
    }
}

// Calculate hunter statistics
function calculateStats(huntersData) {
    const hunters = Object.values(huntersData);
    
    const stats = {
        totalHunters: hunters.length,
        averageLevel: hunters.length > 0 ? Math.round(hunters.reduce((sum, h) => sum + h.level, 0) / hunters.length) : 0,
        totalGold: hunters.reduce((sum, h) => sum + (h.gold || 0), 0),
        totalShadows: hunters.reduce((sum, h) => sum + (h.shadows ? h.shadows.length : 0), 0),
        rankDistribution: {},
        topHunters: hunters
            .sort((a, b) => b.level - a.level)
            .slice(0, 10)
            .map(h => ({
                level: h.level,
                rank: h.rank,
                gold: h.gold || 0,
                shadows: h.shadows ? h.shadows.length : 0
            })),
        pvpStats: {
            totalBattles: hunters.reduce((sum, h) => sum + (h.pvp_stats ? h.pvp_stats.wins + h.pvp_stats.losses : 0), 0),
            topPvPHunters: hunters
                .filter(h => h.pvp_stats && h.pvp_stats.wins > 0)
                .sort((a, b) => b.pvp_stats.wins - a.pvp_stats.wins)
                .slice(0, 5)
                .map(h => ({
                    wins: h.pvp_stats.wins,
                    losses: h.pvp_stats.losses,
                    rank: h.pvp_stats.rank,
                    level: h.level
                }))
        }
    };
    
    // Calculate rank distribution
    hunters.forEach(hunter => {
        const rank = hunter.rank || 'E';
        stats.rankDistribution[rank] = (stats.rankDistribution[rank] || 0) + 1;
    });
    
    return stats;
}

// Routes
app.get('/', (req, res) => {
    try {
        const huntersData = loadHuntersData();
        const stats = calculateStats(huntersData);
        
        // Load game configuration data
        const monstersData = loadGameData('monsters.json');
        const gatesData = loadGameData('gates.json');
        const itemsData = loadGameData('items.json');
        
        res.render('dashboard', {
            title: 'Solo Leveling RPG Dashboard',
            stats: stats,
            huntersData: huntersData,
            gameData: {
                monsters: monstersData,
                gates: gatesData,
                items: itemsData
            }
        });
    } catch (error) {
        console.error('Dashboard error:', error);
        res.status(500).render('dashboard', {
            title: 'Solo Leveling RPG Dashboard - Error',
            stats: {
                totalHunters: 0,
                averageLevel: 0,
                totalGold: 0,
                totalShadows: 0,
                rankDistribution: {},
                topHunters: [],
                pvpStats: { totalBattles: 0, topPvPHunters: [] }
            },
            huntersData: {},
            gameData: { monsters: {}, gates: {}, items: {} },
            error: 'Failed to load dashboard data'
        });
    }
});

// API endpoint to get hunter data
app.get('/api/hunters', (req, res) => {
    try {
        const huntersData = loadHuntersData();
        res.json(huntersData);
    } catch (error) {
        res.status(500).json({ error: 'Failed to load hunters data' });
    }
});

// API endpoint to get specific hunter data
app.get('/api/hunters/:userId', (req, res) => {
    try {
        const huntersData = loadHuntersData();
        const hunter = huntersData[req.params.userId];
        
        if (!hunter) {
            return res.status(404).json({ error: 'Hunter not found' });
        }
        
        res.json(hunter);
    } catch (error) {
        res.status(500).json({ error: 'Failed to load hunter data' });
    }
});

// API endpoint to get server statistics
app.get('/api/stats', (req, res) => {
    try {
        const huntersData = loadHuntersData();
        const stats = calculateStats(huntersData);
        res.json(stats);
    } catch (error) {
        res.status(500).json({ error: 'Failed to calculate statistics' });
    }
});

// API endpoint to update hunter data (admin only)
app.put('/api/hunters/:userId', (req, res) => {
    try {
        const huntersData = loadHuntersData();
        const userId = req.params.userId;
        
        if (!huntersData[userId]) {
            return res.status(404).json({ error: 'Hunter not found' });
        }
        
        // Update hunter data with provided fields
        const updatedHunter = { ...huntersData[userId], ...req.body };
        huntersData[userId] = updatedHunter;
        
        if (saveHuntersData(huntersData)) {
            res.json({ success: true, hunter: updatedHunter });
        } else {
            res.status(500).json({ error: 'Failed to save hunter data' });
        }
    } catch (error) {
        res.status(500).json({ error: 'Failed to update hunter data' });
    }
});

// API endpoint to reset hunter data (admin only)
app.delete('/api/hunters/:userId', (req, res) => {
    try {
        const huntersData = loadHuntersData();
        const userId = req.params.userId;
        
        if (!huntersData[userId]) {
            return res.status(404).json({ error: 'Hunter not found' });
        }
        
        delete huntersData[userId];
        
        if (saveHuntersData(huntersData)) {
            res.json({ success: true, message: 'Hunter data deleted' });
        } else {
            res.status(500).json({ error: 'Failed to save changes' });
        }
    } catch (error) {
        res.status(500).json({ error: 'Failed to delete hunter data' });
    }
});

// API endpoint to get game configuration
app.get('/api/config/:type', (req, res) => {
    try {
        const configType = req.params.type;
        let filename;
        
        switch (configType) {
            case 'monsters':
                filename = 'monsters.json';
                break;
            case 'gates':
                filename = 'gates.json';
                break;
            case 'items':
                filename = 'items.json';
                break;
            case 'quests':
                filename = 'quests.json';
                break;
            case 'shadows':
                filename = 'shadow_grades.json';
                break;
            default:
                return res.status(400).json({ error: 'Invalid configuration type' });
        }
        
        const data = loadGameData(filename);
        res.json(data);
    } catch (error) {
        res.status(500).json({ error: 'Failed to load configuration data' });
    }
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ 
        status: 'healthy', 
        timestamp: new Date().toISOString(),
        service: 'Solo Leveling RPG Dashboard'
    });
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error('Server error:', err);
    res.status(500).json({ error: 'Internal server error' });
});

// 404 handler
app.use((req, res) => {
    res.status(404).json({ error: 'Endpoint not found' });
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
    console.log(`Solo Leveling RPG Dashboard running on port ${PORT}`);
    console.log(`Dashboard URL: http://localhost:${PORT}`);
});

module.exports = app;
