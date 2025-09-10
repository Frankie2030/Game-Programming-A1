# Whack-a-Zombie — Assignment 1

A Python-based whack-a-mole style game built with Pygame, featuring zombies that emerge from tombstones in a spooky graveyard setting.

## Features
- Whack zombies before they attack you. You start with 3 brains (lives).
- Level up by killing zombies to gain extra lives. Brain pickups also appear for bonus lives.
- Toggle F for FPS display, B for hitbox visualization.
- Audio controls available in main menu with volume sliders.

## Controls
- Left Click: Whack zombies/collect brains
- P: Pause/Resume
- M: Toggle mute
- F: Toggle FPS display
- B: Toggle hitbox display
- R: Reset game
- ESC: Quit

## How to Run
```bash
pip install pygame
python main.py
```

# Rubric-based Features

## Required Features

### Background with multiple zombie spawn locations - 2 pts
The game features 20 spawn points (4 rows × 5 columns) positioned to align with tombstones in the background image.

```python
# main.py
def make_spawn_points(self) -> list[SpawnPoint]:
    """20 spawn points (4 rows x 5 columns) positioned to align with tombs."""
    cols, rows = 5, 4
    start_x, start_y = 160, 75
    x_gap, y_gap = 155, 115
    base_positions = [
        (start_x + col * x_gap, start_y + row * y_gap)
        for row in range(rows)
        for col in range(cols)
    ]
    
    spawn_points = []
    for pos in spawn_positions:
        spawn_points.append(SpawnPoint(pos, radius=SPAWN_RADIUS))
    return spawn_points
```

```python
# src/constants.py
BACKGROUND_PATH = os.path.join(ASSETS_DIR, "game_background.png")
```

### Zombie design (sprite/art) - 1 pt
Zombies use a sprite sheet with multiple animation frames for idle, attack, and death states.

```python
# src/zombie.py
@classmethod
def load_sprites(cls):
    if os.path.exists(ZOMBIE_SPRITE_PATH):
        cls.sprite_sheet = pygame.image.load(ZOMBIE_SPRITE_PATH).convert_alpha()
        # Extract normal, attack, and death frames from sprite sheet
        normal_positions = [(0, 0), (1, 0), (2, 0), (3, 0), (0, 1), (1, 1), (2, 1), (3, 1)]
        attack_positions = [(4, 2), (5, 2), (6, 2), (7, 2)]
        death_positions = [(0, 10), (1, 10), (2, 10), (3, 10)]
```

### Zombie head display and lifetime - 2 pts
Zombies have configurable lifetimes and automatically attack (dealing damage) after their timer expires.

```python
# src/zombie.py
def update(self, now_ms: int) -> bool:
    attack_occurred = False
    
    # Auto-attack when lifetime expires
    if not self.hit and not self.attacking and (now_ms - self.born_at >= self.lifetime):
        self.start_attack(now_ms)
    
    # Deal damage after attack animation completes
    if self.attacking and now_ms - self.attack_start >= ATTACK_ANIM_MS:
        attack_occurred = True
        self.has_dealt_damage = True
        self.despawn_start = now_ms
    
    return attack_occurred
```

```python
# src/constants.py
MAX_LIFETIME_MS = 2000
MIN_LIFETIME_MS = 800
ATTACK_ANIM_MS = 300
```

### Mouse interaction / hit detection - 3 pts
Comprehensive click handling with rectangle-based hit detection and priority system.

```python
# main.py
def handle_click(self, pos: tuple[int, int], now_ms: int) -> None:
    # Check brain pickups first (higher priority)
    for brain in reversed(self.brains):
        if not brain.picked_up and not brain.dead and brain.contains_point(pos):
            brain.mark_picked_up(now_ms)
            self.lives = min(MAX_LIVES, self.lives + 1)
            return
    
    # Check zombie hits
    for z in reversed(self.zombies):
        if not z.hit and not z.attacking and z.contains_point(pos, now_ms):
            z.mark_hit(now_ms)
            self.hits += 1
            return
    
    # No hit registered
    self.misses += 1
```

```python
# src/zombie.py
def contains_point(self, point: tuple[int, int], now_ms: int) -> bool:
    if self.attacking:  # Prevent hits during attack animation
        return False
    hitbox_rect = self.get_hitbox_rect(now_ms)
    return hitbox_rect.collidepoint(point)

def get_hitbox_rect(self, now_ms: int) -> pygame.Rect:
    sprite_width, sprite_height = self._scaled_size()
    hitbox_rect = pygame.Rect(0, 0, int(sprite_width * 0.5), int(sprite_height * 0.9))
    hitbox_rect.centerx = center[0]
    hitbox_rect.centery = center[1] + vertical_offset
    return hitbox_rect
```

### Score output (HUD) - 2 pts
Comprehensive HUD displaying hits, misses, accuracy percentage, level, and lives.

```python
# ui.py
def draw(self, surf: pygame.Surface, hits: int, misses: int, lives: int, level: int):
    total = hits + misses
    acc = (hits / total * 100.0) if total > 0 else 0.0
    
    # Right side stats
    right_stats = [
        f"Hits: {hits}",
        f"Misses: {misses}",
        f"Accuracy: {acc:.1f}%",
    ]
    
    # Left side level/lives display
    level_text = self.font.render(f"Level: {level}", True, TEXT_COLOR)
    # Brain icon + lives count display
```

## Bonus Features

### Audio
Background music, hit sound effects, and level-up sounds with volume controls.

```python
# main.py
def init_audio(self) -> None:
    if os.path.exists(MUSIC_PATH):
        pygame.mixer.music.load(MUSIC_PATH)
        pygame.mixer.music.play(-1)  # Loop indefinitely
    
    if os.path.exists(HIT_SFX_PATH):
        self.snd_hit = pygame.mixer.Sound(HIT_SFX_PATH)
    
    if os.path.exists(LEVEL_UP_SFX_PATH):
        self.snd_level_up = pygame.mixer.Sound(LEVEL_UP_SFX_PATH)
```

### Hit Effects
Particle effects for both zombie hits and hammer strikes with color-coded feedback.

```python
# src/zombie.py
def create_hit_effects(self, hit_pos: tuple[int, int]) -> None:
    for _ in range(12):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1, 3)
        particle = {
            'x': hit_pos[0], 'y': hit_pos[1],
            'dx': math.cos(angle) * speed,
            'dy': math.sin(angle) * speed,
            'life': random.randint(80, 120),
            'alpha': 255
        }
        self.hit_particles.append(particle)
```

### Spawn/Despawn Animation
Smooth scale-based animations for zombie appearance and disappearance.

```python
# src/zombie.py
def get_scale_factor(self, now_ms: int) -> float:
    spawn_elapsed = now_ms - self.born_at
    
    # Spawn animation (scale up)
    if spawn_elapsed < self.SPAWN_ANIM_MS:
        progress = spawn_elapsed / self.SPAWN_ANIM_MS
        return progress * 0.8 + 0.2  # Scale from 20% to 100%
    
    # Despawn animation (scale down)
    if self.despawn_start is not None:
        despawn_elapsed = now_ms - self.despawn_start
        if despawn_elapsed < self.DESPAWN_ANIM_MS:
            progress = despawn_elapsed / self.DESPAWN_ANIM_MS
            return (1.0 - progress) * 0.8 + 0.2  # Scale from 100% to 20%
    
    return 1.0  # Normal size
```

## Technical Features
- **Responsive Design**: Window resizing support with scaled UI elements
- **Pause System**: Pause-aware timing that excludes paused time from game logic
- **Level Progression**: Difficulty scaling with faster spawns and shorter zombie lifetimes
- **Brain Pickup System**: Collectible items that grant extra lives
- **Debug Visualization**: Toggleable hitbox and FPS display
