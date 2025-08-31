# Whack-a-Zombie — Assignment 1

A Python-based whack-a-mole style game built with Pygame, featuring zombies that emerge from tombstones in a spooky graveyard setting.

## 🎮 Game Overview

Whack-a-Zombie is an arcade-style game where players must click on zombie heads as they emerge from tombstones. The game features:
- **20 spawn points** arranged in a 4x5 grid matching background tombstones
- **Progressive difficulty** with level-based scaling
- **Brain pickups** that grant extra lives
- **Comprehensive HUD** showing score, accuracy, and progress
- **Audio support** with background music and sound effects

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Pygame library

### Installation
1. Clone or download the project files
2. Navigate to the project directory
3. Add environment & Install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
```

### Running the Game
```bash
python3 main.py
```

### Build the executable file .exe
```bash
python3 -m pip install pyinstaller
pyinstaller --onefile --windowed --name "WhackZombie" --add-data "assets:assets" main.py 
```

## 🎯 Game Controls

| Key | Action |
|-----|--------|
| **Left Mouse Button** | Whack zombies / Collect brains |
| **P** | Pause / Resume game |
| **F** | Toggle FPS display |
| **R** | Reset current run |
| **M** | Mute / Unmute audio |
| **ESC** | Quit game |
| **SPACE/ENTER** | Start game (from start screen) |

## 🎨 Game Features

### Core Gameplay
- **Zombie Spawning**: Zombies emerge from 20 tombstone locations in a 4x5 grid
- **Timing System**: Each zombie has a countdown timer before attacking
- **Life System**: Start with 3 lives, lose lives when zombies attack
- **Brain Pickups**: Collect brains to gain extra lives (max 5)

### Difficulty Progression
- **Level System**: Progress through 10 levels
- **Dynamic Scaling**: 
  - Spawn rate increases with level
  - Zombie lifetime decreases with level
  - Bonus life awarded every 10 zombies killed

### Visual & Audio
- **Graveyard Background**: Atmospheric graveyard scene with tombstones
- **Zombie Animations**: Spawn, idle, attack, and death animations
- **Sound Effects**: Hit sounds, level-up audio, background music
- **Visual Feedback**: Hit flashes, life-loss screen effects

## 🏗️ Technical Architecture

### File Structure
```
A1/
├── main.py          # Main game loop and controller
├── constants.py     # Game configuration and constants
├── models.py        # Data structures (SpawnPoint)
├── spawner.py       # Zombie and brain spawning logic
├── zombie.py        # Zombie entity and behavior
├── brain.py         # Brain pickup entity
├── ui.py           # HUD and game over screen
├── logger.py       # Game event logging
├── assets/         # Game assets (sprites, audio, backgrounds)
└── README.md       # This file
```

### Key Components

#### Game Controller (`main.py`)
- Manages game state and main loop
- Handles input events and rendering
- Coordinates all subsystems

#### Spawner (`spawner.py`)
- Manages zombie and brain spawning timing
- Implements level-based difficulty scaling
- Prevents overlapping spawns

#### Zombie Entity (`zombie.py`)
- Handles zombie lifecycle (spawn → idle → attack → despawn)
- Manages animations and hit detection
- Implements timer-based behavior

#### UI System (`ui.py`)
- **HUD**: Left side shows level/progress/lives, right side shows stats
- **Game Over Screen**: Final score and restart options
- **Start Screen**: Volume controls and instructions

## ⚙️ Configuration

### Game Settings (`constants.py`)
```python
# Screen dimensions
WIDTH, HEIGHT = 960, 540  # 16:9 aspect ratio

# Game balance
INITIAL_LIVES = 3
MAX_LIVES = 5
SPAWN_INTERVAL_MS = 1000
MAX_LIFETIME_MS = 2000
MIN_LIFETIME_MS = 800

# Level progression
MAX_LEVEL = 10
ZOMBIES_PER_LEVEL = 10
LEVEL_SPAWN_DECREASE = 50  # ms per level
LEVEL_LIFETIME_DECREASE = 100  # ms per level
```

### Spawn Point Configuration
The game uses **hardcoded pixel coordinates** to align with the background image:
- **Grid**: 4 rows × 5 columns = 20 spawn points
- **First tombstone**: Position (210, 155)
- **Horizontal spacing**: 140 pixels between columns
- **Vertical spacing**: 95 pixels between rows
- **Spawn radius**: 30 pixels for hit detection

## 🎯 Assignment Requirements Coverage

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| **Background with multiple spawn locations** | ✅ Complete | 20 tombstone positions in 4×5 grid |
| **Zombie design (sprite/art)** | ✅ Complete | Animated zombie sprites with multiple states |
| **Zombie head display and lifetime** | ✅ Complete | Timer-based spawning with 800-2000ms lifetime |
| **Mouse interaction / hit detection** | ✅ Complete | Precise hitbox detection with click coordinates |
| **Score output (HUD)** | ✅ Complete | Hits, misses, accuracy, zombies killed, lives, level |
| **Audio (Bonus)** | ✅ Complete | Background music, hit sounds, level-up audio |
| **Hit Effects (Bonus)** | ✅ Complete | Visual flashes and screen effects |
| **Spawn/Despawn Animation (Bonus)** | ✅ Complete | Rise/sink animations with easing |

## 🔧 Troubleshooting

### Common Issues

**Zombies not spawning at tombstones:**
- Check that `game_background.png` is in the `assets/` folder
- Verify spawn point coordinates in `make_spawn_points()`

**Audio not working:**
- Ensure audio files are in `assets/` folder
- Check system audio settings
- Pygame mixer may need initialization

**Performance issues:**
- Press F to toggle FPS display
- Check if frame rate is stable at 60 FPS
- Reduce spawn rate in `constants.py` if needed

### Debug Features
- **FPS Display**: Press F to show current frame rate
- **Console Output**: Spawn point positions and game events logged
- **Log File**: Detailed click events saved to `log.md`

## 📝 Development Notes

### Spawn Point Alignment
The current implementation uses **hardcoded pixel coordinates** to align with the background image. This approach was chosen because:
1. The background image is square but stretched to fit the 960×540 window
2. Visual alignment requires precise positioning
3. Grid-based calculations don't account for image stretching

### Future Improvements
- **Dynamic positioning**: Calculate spawn points based on background image analysis
- **Configurable layouts**: Support different background images
- **Editor tools**: Visual spawn point placement tool

## 📄 License

This project is created for educational purposes as part of Assignment 1.

## 🤝 Contributing

This is an academic project, but suggestions for improvements are welcome!

---

**Happy Zombie Whacking! 🧟‍♂️🔨**

