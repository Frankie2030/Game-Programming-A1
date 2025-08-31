"""Game entry point and loop orchestration for Whack-a-Zombie.

Notes
-----
- Uses a capped FPS loop and all timings in milliseconds via
  ``pygame.time.get_ticks()``, keeping spawn timing independent of frame rate.
- Optional assets can be placed in ``assets/``. The game gracefully handles
  missing audio or sprites.
- Includes start screen with volume sliders, HUD, and a restartable game over
  screen.

Run
---
```
pip install -r requirements.txt
python main.py
```
"""

from __future__ import annotations

import os
import pygame
import random
import math

from constants import *
from models import SpawnPoint
from zombie import Zombie
from brain import Brain
from logger import GameLogger
from ui import HUD, GameOverScreen
from spawner import Spawner

class Game:
    """
    Main game controller: initializes subsystems, runs the loop, handles input,
    updates entities, and draws the frame.
    
    Features:
    - Resizable window support with responsive UI
    - Zombie spawn effects with particles and glow
    - Hammer hit effects with impact particles
    - Audio system with volume controls
    - Level progression system
    - Brain pickup mechanics for extra lives
    
    Window Management:
    - Supports window resizing with pygame.RESIZABLE
    - Automatically recalculates spawn points and UI elements
    - Maintains aspect ratio and positioning on resize
    
    Effects System:
    - Spawn effects: dust particles and yellow glow when zombies appear
    - Hit effects: colorful impact particles when zombies are hit
    - Hammer effects: spark and dust particles on every click
    - Life loss flash: red screen flash when losing lives
    """

    def __init__(self) -> None:
        """Initialize the game with all subsystems."""
        pygame.init()
        pygame.display.set_caption("Whack-a-Zombie — Assignment 1")
        # Make window resizable
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.Font(FONT_NAME, FONT_SIZE_MEDIUM)
        self.font_big = pygame.font.Font(FONT_NAME, FONT_SIZE_LARGE)

        # Track current window size
        self.current_width = WIDTH
        self.current_height = HEIGHT

        # Load background image
        self.background_img: pygame.Surface | None = None
        self.load_background()
        
        self.spawn_points: list[SpawnPoint] = self.make_spawn_points()
        self.spawner = Spawner(self.spawn_points)

        # Initialize logging system
        self.logger = GameLogger(LOG_FILE)

        # Game state
        self.reset_game()
        self.game_over = False
        self.paused = False
        self.show_fps = False
        self.fps_samples = []
        self.life_lost_flash = 0  # Timer for life lost screen flash
        
        # Audio volumes
        self.bgm_volume = 0.5
        self.sfx_volume = 0.7
        
        # UI components
        self.hud = HUD(self.font_small)
        self.game_over_screen = GameOverScreen(self.font_big, self.font_small)

        # Mouse cursor
        self.hammer_cursor = None
        self.load_hammer_cursor()
        # Don't hide cursor initially - let start screen handle it
        
        # Hammer hit effects
        self.hammer_hit_effects = []

        # Audio
        self.muted = False
        self.snd_hit: pygame.mixer.Sound | None = None
        self.snd_level_up: pygame.mixer.Sound | None = None
        self.init_audio()

    def reset_game(self) -> None:
        """Reset all game state to initial values."""
        self.zombies: list[Zombie] = []
        self.brains: list[Brain] = []
        self.hits = 0
        self.misses = 0
        self.lives = INITIAL_LIVES
        self.level = 1
        self.zombies_killed = 0
        self.game_over = False
        self.spawner.next_spawn_at = 0  # Reset spawner timing
        self.spawner.next_brain_check_at = 0  # Reset brain spawning timing
        # Set cursor for gameplay
        pygame.mouse.set_visible(False)  # Hide system cursor for hammer display

    def update_level(self) -> None:
        """Update game level based on zombies killed."""
        new_level = min(MAX_LEVEL, (self.zombies_killed // ZOMBIES_PER_LEVEL) + 1)
        if new_level > self.level:
            old_level = self.level
            self.level = new_level
            
            # Award +1 life on level up (capped at MAX_LIVES)
            old_lives = self.lives
            self.lives = min(MAX_LIVES, self.lives + 1)
            lives_gained = self.lives - old_lives
            
            # Play level up sound effect
            if self.snd_level_up and not self.muted:
                self.snd_level_up.play()
            
            # Log and display level up
            self.logger.log_level_up(self.level)
            if lives_gained > 0:
                print(f"Level up! Now level {self.level} - Bonus life granted! ({self.lives}/{MAX_LIVES} lives)")
            else:
                print(f"Level up! Now level {self.level} - Already at max lives ({MAX_LIVES}/{MAX_LIVES})")
            

    # --------------------------------- Setup ----------------------------------------

    def load_hammer_cursor(self) -> None:
        """
        Load hammer cursor or create fallback.
        Tries to load hammer sprite from assets, falls back to procedural drawing.
        """
        if os.path.exists(HAMMER_PATH):
            self.original_hammer = pygame.image.load(HAMMER_PATH).convert_alpha()
            # Store original for responsive scaling
            self.hammer_cursor = pygame.transform.scale(self.original_hammer, (40, 40))
        else:
            self.original_hammer = None
            self.hammer_cursor = None

    def load_background(self) -> None:
        """
        Load and scale the game background image to current window size.
        """
        if os.path.exists(BACKGROUND_PATH):
            try:
                img = pygame.image.load(BACKGROUND_PATH).convert()
                # Use current window size for scaling
                width = getattr(self, 'current_width', WIDTH)
                height = getattr(self, 'current_height', HEIGHT)
                self.background_img = pygame.transform.scale(img, (width, height))
                print(f"Successfully loaded background from: {BACKGROUND_PATH} scaled to {width}x{height}")
            except Exception as e:
                print(f"Failed to load background: {e}")
                self.background_img = None
        else:
            print(f"Background image not found: {BACKGROUND_PATH}")
            self.background_img = None
    
    def make_spawn_points(self) -> list[SpawnPoint]:
        """
        20 spawn points (4 rows x 5 columns) positioned to align with tombs in background image.
        Now responsive to window resizing - calculates positions based on current window dimensions.
        """
        cols, rows = 5, 4  # 5 columns, 4 rows = 20 total spawn points

        # Get current window dimensions (fallback to constants if not set)
        width = getattr(self, 'current_width', WIDTH)
        height = getattr(self, 'current_height', HEIGHT)
        
        # Base positions for 960x540 window (reference size)
        BASE_WIDTH = 960
        BASE_HEIGHT = 540
        
        # Scale factors for current window size
        scale_x = width / BASE_WIDTH
        scale_y = height / BASE_HEIGHT
        
        # Spawn point radius - adjusted to fit zombie base on tombstone
        SPAWN_RADIUS = int(30 * min(scale_x, scale_y))  # Scale radius proportionally

        # Base positions for reference window size (960x540)
        base_positions = [
            # Row 1 (top row)
            (165, 75), (325, 75), (475, 75), (635, 75), (790, 75),
            # Row 2
            (165, 190), (325, 190), (475, 190), (635, 190), (790, 190),
            # Row 3
            (165, 305), (325, 305), (475, 305), (635, 305), (790, 305),
            # Row 4 (bottom row)
            (165, 415), (325, 415), (475, 415), (635, 415), (790, 415)
        ]

        # Scale positions to current window size
        spawn_positions = []
        for base_x, base_y in base_positions:
            scaled_x = int(base_x * scale_x)
            scaled_y = int(base_y * scale_y)
            spawn_positions.append((scaled_x, scaled_y))

        spawn_points = []
        for pos in spawn_positions:
            spawn_points.append(SpawnPoint(pos, radius=SPAWN_RADIUS))

        # Debugging output to verify positions
        print(f"Calculated Spawn Points ({len(spawn_points)}) for {width}x{height}:")
        for idx, sp in enumerate(spawn_points):
            print(f"  {idx}: Pos={sp.pos}, Radius={sp.radius}")

        return spawn_points  # 20 spawn points (4x5 grid)

    def init_audio(self) -> None:
        """
        Try to initialize audio & load assets if available (safe to run without).
        Sets up background music and sound effects with appropriate volumes.
        """
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            
        # Background music (looped) – optional
        if os.path.exists(MUSIC_PATH):
            try:
                pygame.mixer.music.load(MUSIC_PATH)
                pygame.mixer.music.set_volume(self.bgm_volume)
                pygame.mixer.music.play(-1)
                print(f"Background music loaded and playing from: {MUSIC_PATH}")
            except Exception as e:
                print(f"Failed to load background music: {e}")
        else:
            print(f"Background music file not found: {MUSIC_PATH}")
            
        # Hit SFX – optional
        if os.path.exists(HIT_SFX_PATH):
            try:
                self.snd_hit = pygame.mixer.Sound(HIT_SFX_PATH)
                self.snd_hit.set_volume(self.sfx_volume)
                print(f"Hit sound effect loaded from: {HIT_SFX_PATH}")
            except Exception as e:
                print(f"Failed to load hit sound effect: {e}")
                self.snd_hit = None
        else:
            print(f"Hit sound effect file not found: {HIT_SFX_PATH}")
            self.snd_hit = None
            
        # Level Up SFX – optional
        if os.path.exists(LEVEL_UP_SFX_PATH):
            try:
                self.snd_level_up = pygame.mixer.Sound(LEVEL_UP_SFX_PATH)
                self.snd_level_up.set_volume(self.sfx_volume)
                print(f"Level up sound effect loaded from: {LEVEL_UP_SFX_PATH}")
            except Exception as e:
                print(f"Failed to load level up sound effect: {e}")
                self.snd_level_up = None
        else:
            print(f"Level up sound effect file not found: {LEVEL_UP_SFX_PATH}")
            self.snd_level_up = None

    def handle_resize(self, new_width: int, new_height: int) -> None:
        """Handle window resize events and update game elements accordingly."""
        if new_width != self.current_width or new_height != self.current_height:
            self.current_width = new_width
            self.current_height = new_height
            
            # Calculate scale factor for responsive sizing
            base_width, base_height = 960, 540
            scale_factor = min(new_width / base_width, new_height / base_height)
            
            # Clear the screen to prevent visual artifacts
            self.screen.fill(BG_COLOR)
            
            # Reload background with new size
            self.load_background()
            
            # Recalculate spawn points for new dimensions
            self.spawn_points = self.make_spawn_points()
            self.spawner.update_spawn_points(self.spawn_points)
            
            # Update zombie and brain scaling
            self.update_entity_scaling(scale_factor)
            
            # Update font sizes for responsive text
            self.update_font_scaling(scale_factor)
            
            print(f"Window resized to {new_width}x{new_height} with scale factor {scale_factor:.2f}")
            print(f"Screen surface size: {self.screen.get_size()}")
            print(f"Current dimensions: {self.current_width}x{self.current_height}")

    def update_entity_scaling(self, scale_factor: float) -> None:
        """Update scaling for all game entities (zombies, brains, etc.)."""
        # Update zombie scaling
        for zombie in self.zombies:
            zombie.update_scale_factor(scale_factor)
        
        # Update brain scaling (if brain class has scaling)
        for brain in self.brains:
            if hasattr(brain, 'update_scale_factor'):
                brain.update_scale_factor(scale_factor)

    def update_font_scaling(self, scale_factor: float) -> None:
        """Update font sizes for responsive text scaling."""
        # Calculate new font sizes based on scale factor
        new_small_size = max(12, int(FONT_SIZE_SMALL * scale_factor))
        new_medium_size = max(14, int(FONT_SIZE_MEDIUM * scale_factor))
        new_large_size = max(18, int(FONT_SIZE_LARGE * scale_factor))
        
        # Update font objects
        self.font_small = pygame.font.Font(FONT_NAME, new_small_size)
        self.font_big = pygame.font.Font(FONT_NAME, new_large_size)
        
        # Update UI component fonts
        self.hud.update_fonts(self.font_small)
        self.game_over_screen.update_fonts(self.font_big, self.font_small)
        
        # Update HUD brain icon scaling
        self.hud.update_brain_icon_scaling(scale_factor)
        
        # Update hammer cursor scaling
        self.update_hammer_cursor_scaling(scale_factor)

    def update_hammer_cursor_scaling(self, scale_factor: float) -> None:
        """Update hammer cursor size for responsive scaling."""
        if self.original_hammer:
            # Calculate new size based on scale factor
            base_size = 40
            new_size = max(20, int(base_size * scale_factor))
            self.hammer_cursor = pygame.transform.scale(self.original_hammer, (new_size, new_size))

    # --------------------------------- Loop -----------------------------------------
    
    def show_start_screen(self) -> bool:
        """
        Display the start screen with volume controls and instructions.
        
        Returns
        -------
        bool
            True if user wants to start game, False if quit
        """
        clock = pygame.time.Clock()
        
        # Hide system cursor and use hammer cursor throughout
        pygame.mouse.set_visible(False)
        
        while True:
            mouse_pos = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.VIDEORESIZE:
                    self.handle_resize(event.w, event.h)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return False
                    if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                        return True
                    if event.key == pygame.K_m:
                        self.toggle_mute()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.check_start_button_click(mouse_pos):
                    return True
            
            self.draw_start_screen(None, mouse_pos)
            clock.tick(FPS)
    
    def check_start_button_click(self, mouse_pos: tuple[int, int]) -> bool:
        """Check if start button was clicked."""
        button_rect = pygame.Rect(self.current_width//2 - 100, self.current_height//2 + 50, 200, 50)
        return button_rect.collidepoint(mouse_pos)
    
    def handle_volume_slider_interaction(self, mouse_pos: tuple[int, int], mouse_pressed: bool) -> bool:
        """Handle volume slider interactions - both clicks and drags."""
        # BGM Volume slider
        bgm_rect = pygame.Rect(self.current_width // 2 - 100, self.current_height // 2 - 80, 200, 20)
        if bgm_rect.collidepoint(mouse_pos) and mouse_pressed:
            relative_x = mouse_pos[0] - bgm_rect.x
            self.bgm_volume = max(0.0, min(1.0, relative_x / bgm_rect.width))
            try:
                pygame.mixer.music.set_volume(self.bgm_volume)
            except:
                pass
            return True
        
        # SFX Volume slider
        sfx_rect = pygame.Rect(self.current_width//2 - 100, self.current_height//2 - 30, 200, 20)
        if sfx_rect.collidepoint(mouse_pos) and mouse_pressed:
            relative_x = mouse_pos[0] - sfx_rect.x
            self.sfx_volume = max(0.0, min(1.0, relative_x / sfx_rect.width))
            if self.snd_hit:
                self.snd_hit.set_volume(self.sfx_volume)
            if self.snd_level_up:
                self.snd_level_up.set_volume(self.sfx_volume)
            return True
        
        return False
    
    def draw_start_screen(self, background: pygame.Surface, mouse_pos: tuple[int, int]) -> None:
        """Draw the start screen."""
        # Clear the entire screen to prevent visual artifacts
        self.screen.fill(BG_COLOR)

        title_text = self.font_big.render("WHACK-A-ZOMBIE", True, (255, 255, 100))
        title_rect = title_text.get_rect(center=(self.current_width // 2, self.current_height // 2 - 200))
        self.screen.blit(title_text, title_rect)
        
        self.draw_volume_sliders()
        
        # Handle volume slider dragging
        mouse_pressed = pygame.mouse.get_pressed()[0]
        self.handle_volume_slider_interaction(mouse_pos, mouse_pressed)
        
        # Start button
        button_rect = pygame.Rect(self.current_width // 2 - 100, self.current_height // 2 + 50, 200, 50)
        button_hovered = button_rect.collidepoint(mouse_pos)
        
        button_color = (100, 150, 100) if button_hovered else (60, 80, 60)
        pygame.draw.rect(self.screen, button_color, button_rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, button_rect, 2)
        
        start_text = self.font_small.render("START GAME", True, TEXT_COLOR)
        start_rect = start_text.get_rect(center=button_rect.center)
        self.screen.blit(start_text, start_rect)
        
        # Instructions
        instructions = [
            "CONTROLS:",
            "Left Click - Whack zombies",
            "P - Pause/Resume",
            "M - Toggle mute",
            "ESC - Quit"
        ]
        
        y_start = self.current_height//2 + 120
        for i, instruction in enumerate(instructions):
            color = (255, 255, 100) if i == 0 else (180, 180, 180)
            font = self.font_small if i == 0 else pygame.font.Font(FONT_NAME, FONT_SIZE_SMALL)
            text = font.render(instruction, True, color)
            text_rect = text.get_rect(center=(self.current_width//2, y_start + i * 25))
            self.screen.blit(text, text_rect)
        
        # Draw hammer cursor on start screen too
        self.draw_hammer_cursor()
        
        pygame.display.flip()
    
    def draw_volume_sliders(self) -> None:
        """Draw volume control sliders with text labels on the right side."""
        # BGM Volume
        bgm_rect = pygame.Rect(self.current_width//2 - 100, self.current_height//2 - 80, 200, 20)
        pygame.draw.rect(self.screen, (100, 100, 100), bgm_rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, bgm_rect, 2)
        
        # BGM handle - make it more visible and easier to grab
        handle_x = bgm_rect.x + int(self.bgm_volume * bgm_rect.width) - 8
        handle_rect = pygame.Rect(handle_x, bgm_rect.y - 7, 16, 34)
        pygame.draw.rect(self.screen, (255, 100, 100), handle_rect)
        pygame.draw.rect(self.screen, (200, 80, 80), handle_rect, 2)
        
        # BGM label on the right side of the slider
        bgm_percent = int(self.bgm_volume * 100)
        bgm_label = self.font_small.render(f"BGM Volume: {bgm_percent}%", True, TEXT_COLOR)
        bgm_label_pos = (bgm_rect.x + bgm_rect.width + 15, bgm_rect.y + bgm_rect.height // 2 - bgm_label.get_height() // 2)
        self.screen.blit(bgm_label, bgm_label_pos)
        
        # SFX Volume
        sfx_rect = pygame.Rect(self.current_width//2 - 100, self.current_height//2 - 30, 200, 20)
        pygame.draw.rect(self.screen, (100, 100, 100), sfx_rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, sfx_rect, 2)
        
        # SFX handle - make it more visible and easier to grab
        handle_x = sfx_rect.x + int(self.sfx_volume * sfx_rect.width) - 8
        handle_rect = pygame.Rect(handle_x, sfx_rect.y - 7, 16, 34)
        pygame.draw.rect(self.screen, (100, 255, 100), handle_rect)
        pygame.draw.rect(self.screen, (80, 200, 80), handle_rect, 2)
        
        # SFX label on the right side of the slider
        sfx_percent = int(self.sfx_volume * 100)
        sfx_label = self.font_small.render(f"SFX Volume: {sfx_percent}%", True, TEXT_COLOR)
        sfx_label_pos = (sfx_rect.x + sfx_rect.width + 15, sfx_rect.y + sfx_rect.height // 2 - sfx_label.get_height() // 2)
        self.screen.blit(sfx_label, sfx_label_pos)

    def run(self) -> None:
        """Main game entry point: show start screen then run game loop."""
        if not self.show_start_screen():
            pygame.quit()
            return
        self.run_game_loop()
    
    def run_game_loop(self) -> None:
        """Main game loop: process events, update, render; exits on quit request."""
        running = True
        while running:
            now = pygame.time.get_ticks()
            current_fps = self.clock.get_fps()
            
            # Update FPS samples for smoothing
            self.fps_samples.append(current_fps)
            if len(self.fps_samples) > 10:
                self.fps_samples.pop(0)
            avg_fps = sum(self.fps_samples) / len(self.fps_samples) if self.fps_samples else 0
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.handle_resize(event.w, event.h)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        self.reset_game()
                    elif event.key == pygame.K_m:
                        self.toggle_mute()
                    elif event.key == pygame.K_p:
                        self.toggle_pause()
                    elif event.key == pygame.K_f:
                        self.show_fps = not self.show_fps
                    elif event.key == pygame.K_d:
                        self.hud.toggle_debug()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.game_over:
                        self.reset_game()
                    elif not self.paused:
                        self.handle_click(pygame.mouse.get_pos(), now)

            # Update game state (only if not paused and not game over)
            if not self.paused and not self.game_over:
                # Update zombies and check for attacks
                attacks_this_frame = 0
                for z in self.zombies:
                    z.update_spawn_effects(now)  # Update spawn effects
                    z.update_hit_effects(now)    # Update hit effects
                    if z.update(now):  # Returns True if zombie attacked (only once per zombie)
                        attacks_this_frame += 1
                
                # Handle life loss from zombie attacks
                if attacks_this_frame > 0:
                    self.lives -= attacks_this_frame
                    self.life_lost_flash = LIFE_LOSS_FLASH_MS
                    if self.lives <= 0:
                        self.lives = 0
                        self.game_over = True
                
                # Update brains
                for brain in self.brains:
                    brain.update(now)
                
                # Remove dead zombies and brains
                self.zombies = [z for z in self.zombies if z.is_active(now)]
                self.brains = [b for b in self.brains if b.is_active(now)]

                # Spawning
                self.spawner.maybe_spawn(now, self.zombies, self.level, self.brains)
                self.spawner.maybe_spawn_brain(now, self.zombies, self.brains)
            
            # Update hammer hit effects
            self.update_hammer_hit_effects()
            
            # Update screen flash timer
            if self.life_lost_flash > 0:
                self.life_lost_flash = max(0, self.life_lost_flash - self.clock.get_time())

            self.draw(now, avg_fps)

            # Cap frame rate
            self.clock.tick(FPS)

        pygame.quit()

    # --------------------------------- Input ----------------------------------------

    def handle_click(self, pos: tuple[int, int], now_ms: int) -> None:
        """
        Handle left-clicks: check for brain pickup first, then zombies.
        Brain pickups award +1 life (capped at 5 max lives).
        Zombie hits count as normal game progression.
        
        Parameters
        ----------
        pos : Tuple[int, int]
            Mouse click position
        now_ms : int
            Current time in milliseconds
        """
        # Check for brain pickup first (higher priority). Do not play hit SFX for pickups.
        for brain in reversed(self.brains):
            if not brain.picked_up and not brain.dead and brain.contains_point(pos):
                brain.mark_picked_up(now_ms)
                # Award +1 life (capped at MAX_LIVES)
                old_lives = self.lives
                self.lives = min(MAX_LIVES, self.lives + 1)
                
                lives_gained = self.lives - old_lives
                if lives_gained > 0:
                    print(f"Brain collected! +{lives_gained} life (now {self.lives}/{MAX_LIVES})")
                    self.logger.log_click(pos, True, f"Brain pickup at spawn {brain.spawn.pos} - gained {lives_gained} life")
                else:
                    print(f"Brain collected but already at max lives ({MAX_LIVES})")
                    self.logger.log_click(pos, True, f"Brain pickup at spawn {brain.spawn.pos} - no life gained (at max)")
                    
                return
        
        # Check for zombie hit (play hit SFX here)
        for z in reversed(self.zombies):
            if not z.hit and not z.attacking and z.contains_point(pos, now_ms):
                z.mark_hit(now_ms)
                self.hits += 1
                self.zombies_killed += 1
                
                # Create hammer hit effect
                self.create_hammer_hit_effect(pos)
                
                if self.snd_hit and not self.muted:
                    try:
                        self.snd_hit.play()
                    except Exception:
                        pass
                
                # Log the successful hit
                self.logger.log_click(pos, True, f"Zombie at spawn {z.spawn.pos}")
                
                # Update level based on kills
                self.update_level()
                return
                
        # No entity consumed the click → miss
        self.misses += 1
        self.logger.log_click(pos, False, "No target hit")
        
        # Create hammer hit effect for miss too
        self.create_hammer_hit_effect(pos)

    def toggle_pause(self) -> None:
        if not self.game_over:
            self.paused = not self.paused

    def toggle_mute(self) -> None:
        self.muted = not self.muted
        pygame.mixer.music.set_volume(0.0 if self.muted else self.bgm_volume)

    # --------------------------------- Rendering ------------------------------------

    def draw_hammer_cursor(self) -> None:
        """Draw the hammer cursor at mouse position."""
        if self.hammer_cursor:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            # Ensure cursor position is within screen bounds
            if 0 <= mouse_x < self.current_width and 0 <= mouse_y < self.current_height:
                # Offset so the hammer "hits" where the cursor points
                cursor_rect = self.hammer_cursor.get_rect(center=(mouse_x + 5, mouse_y + 5))
                self.screen.blit(self.hammer_cursor, cursor_rect)
    
    def create_hammer_hit_effect(self, hit_pos: tuple[int, int]) -> None:
        """Create hammer hit effect at click position."""
        
        # Create impact particles
        for _ in range(8):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1, 3)  # Reduced speed for better visibility
            dx = math.cos(angle) * speed
            dy = math.sin(angle) * speed
            
            effect = {
                'x': hit_pos[0],
                'y': hit_pos[1],
                'dx': dx,
                'dy': dy,
                'life': random.randint(80, 120),  # Increased lifetime
                'max_life': 120,  # Increased max lifetime
                'alpha': 255,
                'size': random.randint(3, 6),  # Slightly larger particles
                'type': random.choice(['spark', 'dust'])
            }
            self.hammer_hit_effects.append(effect)
    
    def update_hammer_hit_effects(self) -> None:
        """Update hammer hit effect particles."""
        for effect in self.hammer_hit_effects[:]:
            effect['life'] -= 16  # 16ms per frame at 60fps
            if effect['life'] <= 0:
                self.hammer_hit_effects.remove(effect)
            else:
                # Move particles outward
                effect['x'] += effect['dx']
                effect['y'] += effect['dy']
                effect['alpha'] = int(255 * (effect['life'] / effect['max_life']))
                # Add gravity effect
                effect['dy'] += 0.3
    
    def draw_hammer_hit_effects(self) -> None:
        """Draw hammer hit effect particles."""
        for effect in self.hammer_hit_effects:
            if effect['alpha'] > 0:
                # Create particle surface with alpha
                particle_surf = pygame.Surface((effect['size'], effect['size']), pygame.SRCALPHA)
                
                if effect['type'] == 'spark':
                    color = (255, 255, 100, effect['alpha'])  # Yellow spark
                else:
                    color = (139, 69, 19, effect['alpha'])   # Brown dust
                
                pygame.draw.circle(particle_surf, color, (effect['size']//2, effect['size']//2), effect['size']//2)
                self.screen.blit(particle_surf, (effect['x'] - effect['size']//2, effect['y'] - effect['size']//2))

    def draw_life_loss_flash(self) -> None:
        """Draw screen flash when life is lost."""
        if self.life_lost_flash > 0:
            alpha = int(100 * (self.life_lost_flash / LIFE_LOSS_FLASH_MS))
            flash_surface = pygame.Surface((self.current_width, self.current_height), pygame.SRCALPHA)
            flash_surface.fill((255, 0, 0, alpha))
            self.screen.blit(flash_surface, (0, 0))

    def draw_background(self, surf: pygame.Surface) -> None:
        """Draw the game background image."""
        if self.background_img:
            surf.blit(self.background_img, (0, 0))

            # Draw spawn points on top of background image to visualize positioning
            # for sp in self.spawn_points:
            #     x, y = sp.pos
            #     r = sp.radius
            #     # Draw a red circle to show spawn point location
            #     pygame.draw.circle(surf, (255, 0, 0), (x, y), r, 2)
            #     # Draw a small red dot in the center
            #     pygame.draw.circle(surf, (255, 0, 0), (x, y), 3)
        else:
            # Fallback to solid color if background image not available
            surf.fill(BG_COLOR)
            
            # Subtle vignette / gradient rectangles for polish (no perf cost)
            rect = pygame.Rect(0, 0, self.current_width, self.current_height)
            pygame.draw.rect(surf, (20, 22, 27), rect, width=24, border_radius=18)

            # Draw holes as fallback
            for sp in self.spawn_points:
                x, y = sp.pos
                r = sp.radius
                # outer ring
                pygame.draw.circle(surf, HOLE_RING, (x, y), r+6)
                # inner dark hole
                pygame.draw.circle(surf, HOLE_COLOR, (x, y), r)

    def draw(self, now_ms: int, fps: float) -> None:
        """
        Compose the frame: bg → zombies → HUD → effects → cursor.
        
        Parameters
        ----------
        now_ms : int
            Current time in milliseconds
        fps : float
            Current frames per second for display
        """
        self.draw_background(self.screen)

        # Draw active zombies
        for z in self.zombies:
            z.draw(self.screen, now_ms)
            
        # Draw active brains
        for brain in self.brains:
            brain.draw(self.screen, now_ms)

        # HUD
        self.hud.draw(self.screen, self.hits, self.misses, self.lives, 
                      self.level, self.zombies_killed, self.show_fps, fps, self.paused, self.muted)

        # Title / hints - centered at top
        if not self.game_over:
            title = self.font_big.render("Whack-a-Zombie", True, TEXT_COLOR)
            title_rect = title.get_rect(center=(self.current_width//2, HUD_PADDING + title.get_height()//2))
            self.screen.blit(title, title_rect)
            
            hint_text = "[LMB] hit  |  [P] pause  |  [F] fps  |  [D] debug  |  [R] reset  |  [M] mute  |  [ESC] quit"
            hint = self.font_small.render(hint_text, True, (200, 200, 200))
            hint_rect = hint.get_rect(center=(self.current_width//2, HUD_PADDING + title.get_height() + 8 + hint.get_height()//2))
            self.screen.blit(hint, hint_rect)

        # Screen effects
        self.draw_life_loss_flash()
        
        # Draw hammer hit effects
        self.draw_hammer_hit_effects()
        
        if self.game_over:
            self.game_over_screen.draw(self.screen, self.hits, self.misses)
        self.draw_hammer_cursor()

        pygame.display.flip()

Game().run()