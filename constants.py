"""Game-wide constants for Whack-a-Zombie.

Screen dimensions, colors, font sizes, tuning knobs for spawn/lifetime and
leveling, asset paths, and logging configuration.
"""
import os

WIDTH, HEIGHT = 960, 540           # 16:9 playfield
FPS = 60                           # target frame rate
BG_COLOR = (25, 28, 33)            # dark background
TEXT_COLOR = (235, 235, 235)       # light text
HOLE_COLOR = (60, 65, 75)          # spawn point "hole"
HOLE_RING = (30, 33, 40)           # subtle ring for holes
FLASH_COLOR = (255, 235, 90)       # hit flash accent
HUD_PADDING = 12
FONT_NAME = "freesansbold.ttf"

# Font Size Constants
FONT_SIZE_SMALL = 14
FONT_SIZE_MEDIUM = 16
FONT_SIZE_LARGE = 22

# Game Settings
INITIAL_LIVES = 3                 
MAX_LIVES = 10                      
ATTACK_ANIM_MS = 300               # Zombie attack animation duration
LIFE_LOSS_FLASH_MS = 300           # Screen flash when losing life

# Brain pickup system
BRAIN_SPAWN_CHECK_INTERVAL_MS = 4000
BRAIN_SPAWN_PROBABILITY = 0.25     
BRAIN_LIFETIME_MS = 1000

MAX_LIFETIME_MS = 2000
MIN_LIFETIME_MS = 800

SPAWN_INTERVAL_MS = 1000           

# Level System Settings
MAX_LEVEL = 10                     # Maximum game level
ZOMBIES_PER_LEVEL = 10             # Zombies killed to level up
LEVEL_SPAWN_DECREASE = 50          # Decrease spawn interval per level (ms)
LEVEL_LIFETIME_DECREASE = 100      # Decrease zombie lifetime per level (ms)
MIN_SPAWN_INTERVAL = 500           # Minimum spawn interval
MIN_ZOMBIE_LIFETIME = 500          # Minimum zombie lifetime

# Log file settings
LOG_FILE = os.path.join(os.path.dirname(__file__), "log.md")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
MUSIC_PATH = os.path.join(ASSETS_DIR, "bg_music.mp3")    # optional
HIT_SFX_PATH = os.path.join(ASSETS_DIR, "hit.mp3")       # optional
LEVEL_UP_SFX_PATH = os.path.join(ASSETS_DIR, "level_up.wav")  # level up sound effect
HAMMER_PATH = os.path.join(ASSETS_DIR, "hammer.png")     # optional hammer cursor
ZOMBIE_SPRITE_PATH = os.path.join(ASSETS_DIR, "ZombieSprite_166x144.png")  # zombie sprite sheet
BRAIN_PATH = os.path.join(ASSETS_DIR, "brain.png")       # brain pickup sprite
BACKGROUND_PATH = os.path.join(ASSETS_DIR, "game_background.png")  # main game background
