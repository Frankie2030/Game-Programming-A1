"""
Screen dimensions, colors, font sizes, tuning knobs for spawn/lifetime and
leveling, asset paths, and logging configuration.
"""

import os

WIDTH, HEIGHT = 960, 540
FPS = 60
BG_COLOR = (25, 28, 33)
TEXT_COLOR = (235, 235, 235)
HOLE_COLOR = (60, 65, 75)
HOLE_RING = (30, 33, 40)           # subtle ring for holes
FLASH_COLOR = (255, 235, 90)
HUD_PADDING = 12
FONT_NAME = "freesansbold.ttf"

# Font Size Constants
FONT_SIZE_SMALL = 14
FONT_SIZE_MEDIUM = 16
FONT_SIZE_LARGE = 22

# Game Settings
INITIAL_LIVES = 3                 
MAX_LIVES = 10                      
ATTACK_ANIM_MS = 300               # Zombie attack animation
LIFE_LOSS_FLASH_MS = 300

# Brain pickup system
BRAIN_SPAWN_CHECK_INTERVAL_MS = 4000
BRAIN_SPAWN_PROBABILITY = 0.25     
BRAIN_LIFETIME_MS = 1000

MAX_LIFETIME_MS = 2000
MIN_LIFETIME_MS = 800

SPAWN_INTERVAL_MS = 1000           

# Level System Settings
MAX_LEVEL = 10
ZOMBIES_PER_LEVEL = 10             # Zombies killed to level up
LEVEL_SPAWN_DECREASE = 50
LEVEL_LIFETIME_DECREASE = 100
MIN_SPAWN_INTERVAL = 500
MIN_ZOMBIE_LIFETIME = 500

# Log file settings
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "log.md")
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
MUSIC_PATH = os.path.join(ASSETS_DIR, "bg_music.mp3")
HIT_SFX_PATH = os.path.join(ASSETS_DIR, "hit.mp3")
LEVEL_UP_SFX_PATH = os.path.join(ASSETS_DIR, "level_up.wav")
HAMMER_PATH = os.path.join(ASSETS_DIR, "hammer.png")
ZOMBIE_SPRITE_PATH = os.path.join(ASSETS_DIR, "ZombieSprite_166x144.png")
BRAIN_PATH = os.path.join(ASSETS_DIR, "brain.png")
BACKGROUND_PATH = os.path.join(ASSETS_DIR, "game_background.png")
