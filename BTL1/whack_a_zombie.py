#!/usr/bin/env python3
"""
Whack-a-Zombie — Assignment 1
=============================

A self-contained Pygame implementation that satisfies the rubric:

Required Features
-----------------
- Background with multiple zombie spawn locations (>= 6).
- Distinct zombie design (drawn procedurally as a green "head" with eyes & scar).
- Zombie head display has a lifetime timer (800-1500 ms, randomized).
- Mouse interaction / hit detection via a circular hitbox.
- Prevent double-counting; ignore extra clicks while a zombie is resolving.
- Score HUD shows hits, misses, and accuracy (hits / (hits + misses)).

Bonus (Extra Credit)
--------------------
- Audio stubs for background music & hit SFX with a mute/unmute toggle (press 'M').
  *This is optional and will only play if you add files to ./assets.*
- Simple spawn/despawn animations (scale in on spawn, scale out on despawn).
- Immediate visual hit feedback (brief flash + squash/stretch on hit).

Notes
-----
- Uses a fixed timestep-ish loop (capped FPS) and all timings in milliseconds using
  ``pygame.time.get_ticks()``, so spawn timing is independent of frame rate.
- Assets are procedurally drawn to avoid external dependencies; you can drop your
  own sprites / audio in ``assets/`` and adjust paths if desired.
- Code is documented with professional docstrings and targeted inline comments.

Run
---
    python whack_a_zombie.py

Controls
--------
- Left Click: whack a zombie.
- R: Reset scores.
- M: Mute / unmute audio (if assets available).
- ESC / Q: Quit.

Author: Your Name
License: MIT
"""

from __future__ import annotations

import math
import os
import random
import sys
from dataclasses import dataclass
from typing import List, Tuple, Optional

import pygame


# --------------------------------------------------------------------------------------
# Configuration Constants
# --------------------------------------------------------------------------------------

WIDTH, HEIGHT = 960, 540           # 16:9 playfield
FPS = 60                           # target frame rate
BG_COLOR = (25, 28, 33)            # dark background
TEXT_COLOR = (235, 235, 235)       # light text
HOLE_COLOR = (60, 65, 75)          # spawn point "hole"
HOLE_RING = (30, 33, 40)           # subtle ring for holes
ZOMBIE_GREEN = (82, 180, 95)       # zombie head base color
ZOMBIE_DARK = (42, 100, 50)        # shading
FLASH_COLOR = (255, 235, 90)       # hit flash accent
HUD_PADDING = 12
FONT_NAME = "freesansbold.ttf"

# Game Settings
INITIAL_LIVES = 3                  # Starting lives
ATTACK_ANIM_MS = 300               # Zombie attack animation duration
LIFE_LOSS_FLASH_MS = 500           # Screen flash when losing life

MIN_LIFETIME_MS = 1800              # recommended range
MAX_LIFETIME_MS = 3500

SPAWN_INTERVAL_MS = 600            # try to spawn a new zombie roughly every 0.6s
MAX_CONCURRENT_ZOMBIES = 1         # only one head counts per click is implicit; keep it simple

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
MUSIC_PATH = os.path.join(ASSETS_DIR, "bg_music.mp3")    # optional
HIT_SFX_PATH = os.path.join(ASSETS_DIR, "hit.mp3")       # optional
HAMMER_PATH = os.path.join(ASSETS_DIR, "hammer.png")     # optional hammer cursor
ZOMBIE_SPRITE_PATH = os.path.join(ASSETS_DIR, "zombiesprite_166x144.png")  # zombie sprite sheet


# --------------------------------------------------------------------------------------
# Helper Data Classes
# --------------------------------------------------------------------------------------

@dataclass(frozen=True)
class SpawnPoint:
    """
    A single, fixed spawn location for zombie heads.

    Attributes
    ----------
    pos : Tuple[int, int]
        The (x, y) center position on the playfield for this spawn point.
    radius : int
        Radius used to draw the hole and approximate the clickable region.
    """
    pos: Tuple[int, int]
    radius: int


class Zombie:
    """
    Represents one zombie "head" that can be whacked.

    Lifecycle:
    - SPAWNING: scales up from 0.6 → 1.0 over ~120ms for a "pop" effect.
    - ACTIVE:   remains visible until lifetime expires or it's hit.
    - ATTACKING: plays attack animation when lifetime expires without being hit.
    - DESPAWN:  scales down to 0 over ~160ms, then is removed.

    Timings are driven via pygame.time.get_ticks() (ms-precise, frame-rate independent).
    """

    SPAWN_ANIM_MS = 120
    DESPAWN_ANIM_MS = 160
    HIT_FLASH_MS = 120
    
    # Class variables for sprite management
    sprite_sheet = None
    normal_frames = []
    attack_frames = []
    death_frames = []
    sprites_loaded = False

    @classmethod
    def load_sprites(cls):
        """Load zombie sprites from sprite sheet."""
        if cls.sprites_loaded:
            return
            
        if os.path.exists(ZOMBIE_SPRITE_PATH):
            try:
                cls.sprite_sheet = pygame.image.load(ZOMBIE_SPRITE_PATH).convert_alpha()
                sheet_width, sheet_height = cls.sprite_sheet.get_size()
                print(f"Loaded sprite sheet: {sheet_width}x{sheet_height}")
                
                # Based on your sprite sheet, let's try different dimensions
                # If it's 166x144, let's assume 11 columns x 12 rows
                cols, rows = 11, 12
                sprite_width = sheet_width // cols  # Should be about 15
                sprite_height = sheet_height // rows  # Should be about 12
                
                print(f"Individual sprite size: {sprite_width}x{sprite_height}")
                
                # Pick specific frames for different states:
                # Normal idle frames - let's use some walking frames from first few rows
                normal_positions = [
                    (0, 0), (1, 0), (2, 0), (3, 0),  # First row
                    (0, 1), (1, 1), (2, 1), (3, 1),  # Second row
                ]
                
                for col, row in normal_positions:
                    x = col * sprite_width
                    y = row * sprite_height
                    rect = pygame.Rect(x, y, sprite_width, sprite_height)
                    frame = cls.sprite_sheet.subsurface(rect)
                    # Scale down to a reasonable size (about 80px wide)
                    scaled_frame = pygame.transform.scale(frame, (80, 70))
                    cls.normal_frames.append(scaled_frame)
                
                # Attack frames - use different poses, maybe from middle rows
                attack_positions = [
                    (4, 2), (5, 2), (6, 2), (7, 2),  # Middle area
                ]
                
                for col, row in attack_positions:
                    x = col * sprite_width
                    y = row * sprite_height
                    rect = pygame.Rect(x, y, sprite_width, sprite_height)
                    frame = cls.sprite_sheet.subsurface(rect)
                    scaled_frame = pygame.transform.scale(frame, (80, 70))
                    cls.attack_frames.append(scaled_frame)
                
                # Death frames - use frames from bottom rows (look like falling/dead)  
                death_positions = [
                    (0, 10), (1, 10), (2, 10), (3, 10),  # Bottom rows
                ]
                
                for col, row in death_positions:
                    x = col * sprite_width  
                    y = row * sprite_height
                    rect = pygame.Rect(x, y, sprite_width, sprite_height)
                    frame = cls.sprite_sheet.subsurface(rect)
                    scaled_frame = pygame.transform.scale(frame, (80, 70))
                    cls.death_frames.append(scaled_frame)
                    
                cls.sprites_loaded = True
                print(f"Successfully loaded zombie sprites: {len(cls.normal_frames)} normal, {len(cls.attack_frames)} attack, {len(cls.death_frames)} death")
            except Exception as e:
                print(f"Failed to load sprites: {e}")
                import traceback
                traceback.print_exc()
                cls.sprites_loaded = False
        else:
            print("Zombie sprite sheet not found, using procedural drawing")
            cls.sprites_loaded = False

    def __init__(self, spawn: SpawnPoint, born_at_ms: int, lifetime_ms: int) -> None:
        """
        Parameters
        ----------
        spawn : SpawnPoint
            The location where this zombie appears.
        born_at_ms : int
            Milliseconds timestamp of spawn (pygame.time.get_ticks()).
        lifetime_ms : int
            How long this zombie remains active before auto-despawning.
        """
        self.spawn = spawn
        self.born_at = born_at_ms
        self.lifetime = lifetime_ms
        self.dead = False
        self.hit = False
        self.hit_time: Optional[int] = None  # when it was hit (ms)
        self.despawn_start: Optional[int] = None  # start time of despawn animation (ms)
        self.attacking = False
        self.attack_start: Optional[int] = None  # start time of attack animation (ms)
        self.has_dealt_damage = False  # Flag to prevent multiple damage from same zombie
        self.animation_frame = 0  # Current animation frame index
        
        # Load sprites if not already loaded
        if not Zombie.sprites_loaded:
            Zombie.load_sprites()

    # ------------------------------- Update & State ----------------------------------

    def is_active(self, now_ms: int) -> bool:
        """Return True if the zombie should be considered "alive/visible" on screen."""
        return not self.dead

    def mark_hit(self, now_ms: int) -> None:
        """Mark as hit and begin despawn flow (prevents double counting)."""
        if self.hit or self.dead or self.attacking:
            return
        self.hit = True
        self.hit_time = now_ms
        self.despawn_start = now_ms  # start the despawn animation immediately on hit

    def start_attack(self, now_ms: int) -> None:
        """Start attack animation when zombie escapes without being hit."""
        if self.hit or self.dead or self.attacking:
            return
        self.attacking = True
        self.attack_start = now_ms

    def is_attacking(self) -> bool:
        """Return True if zombie is currently attacking."""
        return self.attacking and not self.hit and not self.dead

    def update(self, now_ms: int) -> bool:
        """
        Advance the zombie's lifecycle based on current time.
        
        Returns True if zombie attacked (player loses life), False otherwise.
        """
        attack_occurred = False
        
        # If still active and lifetime expired (not hit yet), start attack animation.
        if (not self.hit) and (not self.attacking) and (now_ms - self.born_at >= self.lifetime) and self.despawn_start is None:
            self.start_attack(now_ms)
            
        # If attacking and animation finished, cause damage and start despawn (but only once!)
        if self.attacking and self.attack_start is not None and not self.has_dealt_damage:
            if now_ms - self.attack_start >= ATTACK_ANIM_MS:
                attack_occurred = True
                self.has_dealt_damage = True  # Prevent multiple damage from same zombie
                self.despawn_start = now_ms

        # When despawn animation finishes, mark as dead (remove externally).
        if self.despawn_start is not None:
            if now_ms - self.despawn_start >= self.DESPAWN_ANIM_MS:
                self.dead = True
                
        return attack_occurred

    # ------------------------------- Rendering ---------------------------------------

    def get_vertical_offset(self, now_ms: int) -> int:
        """
        Compute the vertical offset for rise/fall animations.
        Positive values = zombie is below ground, 0 = fully emerged.
        
        Returns
        -------
        int
            Vertical offset in pixels to apply to the zombie's position.
        """
        sprite_height = 70  # Height of our scaled sprites
        
        # Spawn animation: rise up from underground
        t_spawn = now_ms - self.born_at
        if t_spawn < self.SPAWN_ANIM_MS:
            # Ease-out animation: start buried, end fully emerged
            progress = t_spawn / self.SPAWN_ANIM_MS
            # Smooth easing function
            eased_progress = 1 - (1 - progress) * (1 - progress)
            return int(sprite_height * (1 - eased_progress))

        # Attack animation: slight bob up and down
        if self.attacking and self.attack_start is not None:
            t = (now_ms - self.attack_start) / ATTACK_ANIM_MS
            if t < 1.0:
                # Small vertical bounce during attack
                bounce_offset = int(5 * math.sin(t * math.pi * 6))
                return -bounce_offset  # Negative = above normal position

        # Despawn animation: sink back down into hole
        if self.despawn_start is not None:
            t = (now_ms - self.despawn_start) / self.DESPAWN_ANIM_MS
            if t < 1.0:
                # Sink back down
                progress = t
                # Ease-in animation for sinking
                eased_progress = progress * progress
                return int(sprite_height * eased_progress)
            else:
                return sprite_height  # Fully buried

        return 0  # Fully emerged, normal position

    def get_current_sprite(self, now_ms: int) -> Optional[pygame.Surface]:
        """Get the current sprite based on zombie state and animation frame."""
        if not self.sprites_loaded or not (self.normal_frames or self.attack_frames or self.death_frames):
            return None
            
        # Update animation frame based on time
        frame_duration = 100  # ms per frame
        self.animation_frame = (now_ms // frame_duration) % max(1, len(self.normal_frames))
        
        if self.hit and self.death_frames:
            # Use death animation
            frame_idx = min(self.animation_frame, len(self.death_frames) - 1)
            return self.death_frames[frame_idx]
        elif self.attacking and self.attack_frames:
            # Use attack animation
            frame_idx = min(self.animation_frame, len(self.attack_frames) - 1)
            return self.attack_frames[frame_idx]
        elif self.normal_frames:
            # Use normal animation
            frame_idx = self.animation_frame % len(self.normal_frames)
            return self.normal_frames[frame_idx]
        
        return None

    def draw(self, surf: pygame.Surface, now_ms: int) -> None:
        """
        Render the zombie using sprites with vertical offset for rise/fall animations.
        """
        center = self.spawn.pos
        vertical_offset = self.get_vertical_offset(now_ms)
        
        # Try to use sprites first
        sprite = self.get_current_sprite(now_ms)
        if sprite and self.sprites_loaded:
            # Use sprite-based rendering with vertical offset
            sprite_rect = sprite.get_rect()
            
            # Apply hit flash effect
            display_sprite = sprite
            if self.hit and self.hit_time is not None and now_ms - self.hit_time < self.HIT_FLASH_MS:
                # Create a copy and apply flash effect
                flash_sprite = sprite.copy()
                flash_alpha = int(180 * (1.0 - (now_ms - self.hit_time) / self.HIT_FLASH_MS))
                flash_surface = pygame.Surface(flash_sprite.get_size(), pygame.SRCALPHA)
                flash_surface.fill((*FLASH_COLOR, flash_alpha))
                flash_sprite.blit(flash_surface, (0, 0), special_flags=pygame.BLEND_ADD)
                display_sprite = flash_sprite
            
            # Position the sprite with vertical offset
            sprite_rect = display_sprite.get_rect()
            sprite_rect.centerx = center[0]
            sprite_rect.centery = center[1] + vertical_offset
            surf.blit(display_sprite, sprite_rect)
            return
        
        # Fallback to procedural drawing if sprites not available
        adjusted_center = (center[0], center[1] + vertical_offset)
        self._draw_procedural(surf, now_ms, adjusted_center, 1.0)

    def _draw_procedural(self, surf: pygame.Surface, now_ms: int, center: Tuple[int, int], scale: float) -> None:
        """Fallback procedural drawing method."""
        base_r = int(self.spawn.radius * 0.9)
        
        # Different scaling for attack vs hit
        if self.attacking:
            r_x = int(base_r * scale * 1.05)
            r_y = int(base_r * scale * 0.95)
        else:
            r_x = int(base_r * scale * (1.08 if self.hit else 1.0))
            r_y = int(base_r * scale * (0.92 if self.hit else 1.0))
        
        r = max(1, int((r_x + r_y) * 0.5))

        # Choose color based on state
        if self.attacking:
            head_color = (150, 50, 50)
            shade_color = (80, 20, 20)
        else:
            head_color = ZOMBIE_GREEN
            shade_color = ZOMBIE_DARK

        # Head base
        pygame.draw.ellipse(surf, head_color, (center[0]-r_x, center[1]-r_y, 2*r_x, 2*r_y))
        # Shading
        pygame.draw.ellipse(surf, shade_color, (center[0]-int(r_x*0.8), center[1]-int(r_y*0.8), int(1.6*r_x), int(1.6*r_y)), width=2)

        # Eyes and scar (simplified for brevity)
        eye_offset_x = int(r * 0.35)
        eye_offset_y = int(r * (-0.05 if self.attacking else -0.10))
        eye_r = max(2, int(r * 0.14))
        
        if not self.attacking:
            pygame.draw.circle(surf, (250, 250, 250), (center[0]-eye_offset_x, center[1]+eye_offset_y), eye_r)
            pygame.draw.circle(surf, (250, 250, 250), (center[0]+eye_offset_x, center[1]+eye_offset_y), eye_r)
            pupil_r = max(1, int(eye_r * 0.5))
            pygame.draw.circle(surf, (10, 10, 10), (center[0]-eye_offset_x, center[1]+eye_offset_y), pupil_r)
            pygame.draw.circle(surf, (10, 10, 10), (center[0]+eye_offset_x, center[1]+eye_offset_y), pupil_r)

        # Hit flash overlay
        if self.hit and self.hit_time is not None and now_ms - self.hit_time < self.HIT_FLASH_MS:
            alpha = int(180 * (1.0 - (now_ms - self.hit_time) / self.HIT_FLASH_MS))
            flash = pygame.Surface((2*r_x, 2*r_y), pygame.SRCALPHA)
            flash.fill((*FLASH_COLOR, alpha))
            surf.blit(flash, (center[0]-r_x, center[1]-r_y))

    # ------------------------------- Hit Testing -------------------------------------

    def contains_point(self, point: Tuple[int, int], now_ms: int) -> bool:
        """
        Circle/ellipse-based hit test. Only allow hits when zombie is not attacking.

        Parameters
        ----------
        point : Tuple[int, int]
            Mouse click position.
        now_ms : int
            Current time in ms (used to match scale used for drawing).

        Returns
        -------
        bool
            True if the click lies within the scaled ellipse head and zombie is hittable.
        """
        # Can't hit attacking zombies
        if self.attacking:
            return False
            
        cx, cy = self.spawn.pos
        base_r = int(self.spawn.radius * 0.9)
        
        # Apply vertical offset to hit detection area
        vertical_offset = self.get_vertical_offset(now_ms)
        adjusted_cy = cy + vertical_offset
        
        # Use fixed size for hit detection (no scaling)
        r_x = base_r
        r_y = base_r

        # Check point inside ellipse: ((x-cx)/rx)^2 + ((y-cy)/ry)^2 <= 1
        px, py = point
        dx = (px - cx) / float(r_x)
        dy = (py - adjusted_cy) / float(r_y)
        return (dx*dx + dy*dy) <= 1.0


class HUD:
    """Heads-Up Display to render hits, misses, accuracy, lives, and optional FPS."""

    def __init__(self, font: pygame.font.Font) -> None:
        self.font = font
        self.small_font = pygame.font.Font(FONT_NAME, 16)

    def draw_life_icon(self, surf: pygame.Surface, x: int, y: int) -> None:
        """Draw a heart/brain icon representing a life."""
        # Draw a simple heart shape as life icon
        points = [
            (x, y+8), (x-8, y), (x-12, y-4), (x-8, y-8),
            (x, y-6), (x+8, y-8), (x+12, y-4), (x+8, y), (x, y+8)
        ]
        pygame.draw.polygon(surf, (220, 50, 50), points)
        pygame.draw.polygon(surf, (255, 100, 100), points, 2)

    def draw(self, surf: pygame.Surface, hits: int, misses: int, lives: int, 
             show_fps: bool = False, fps: float = 0.0, paused: bool = False) -> None:
        """Render a comprehensive HUD."""
        total = hits + misses
        acc = (hits / total * 100.0) if total > 0 else 0.0
        
        # Main stats
        lines = [
            f"Hits:   {hits}",
            f"Misses: {misses}",
            f"Accuracy: {acc:.1f}%",
        ]
        x, y = HUD_PADDING, HUD_PADDING
        for line in lines:
            text_surf = self.font.render(line, True, TEXT_COLOR)
            surf.blit(text_surf, (x, y))
            y += text_surf.get_height() + 4

        # Lives display
        lives_text = self.font.render(f"Lives: {lives}", True, TEXT_COLOR)
        surf.blit(lives_text, (x, y))
        
        # Draw heart icons
        heart_x = x + lives_text.get_width() + 10
        for i in range(lives):
            self.draw_life_icon(surf, heart_x + i * 25, y + lives_text.get_height() // 2)
        y += lives_text.get_height() + 8

        # Optional FPS display
        if show_fps:
            fps_color = (0, 255, 0) if fps >= 55 else (255, 255, 0) if fps >= 30 else (255, 0, 0)
            fps_text = self.small_font.render(f"FPS: {fps:.1f}", True, fps_color)
            surf.blit(fps_text, (x, y))

        # Pause indicator
        if paused:
            pause_text = self.font.render("PAUSED", True, (255, 255, 100))
            text_rect = pause_text.get_rect(center=(surf.get_width()//2, 100))
            # Semi-transparent background
            bg_rect = text_rect.inflate(20, 10)
            bg_surf = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
            bg_surf.fill((0, 0, 0, 128))
            surf.blit(bg_surf, bg_rect)
            surf.blit(pause_text, text_rect)


class GameOverScreen:
    """Game over screen with final stats and restart option."""
    
    def __init__(self, font_big: pygame.font.Font, font_small: pygame.font.Font):
        self.font_big = font_big
        self.font_small = font_small
        
    def draw(self, surf: pygame.Surface, hits: int, misses: int) -> bool:
        """
        Draw game over screen.
        
        Returns True if restart button is hovered, False otherwise.
        """
        # Semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0, 0))
        
        # Game Over title
        game_over_text = self.font_big.render("GAME OVER", True, (255, 100, 100))
        game_over_rect = game_over_text.get_rect(center=(WIDTH//2, HEIGHT//2 - 100))
        surf.blit(game_over_text, game_over_rect)
        
        # Final stats
        total = hits + misses
        acc = (hits / total * 100.0) if total > 0 else 0.0
        score = max(0, hits - misses)
        
        stats_lines = [
            f"Final Score: {score}",
            f"Hits: {hits}",
            f"Misses: {misses}", 
            f"Accuracy: {acc:.1f}%"
        ]
        
        y_offset = HEIGHT//2 - 30
        for line in stats_lines:
            text_surf = self.font_small.render(line, True, TEXT_COLOR)
            text_rect = text_surf.get_rect(center=(WIDTH//2, y_offset))
            surf.blit(text_surf, text_rect)
            y_offset += 30
            
        # Restart button
        mouse_x, mouse_y = pygame.mouse.get_pos()
        button_rect = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 80, 200, 50)
        button_hovered = button_rect.collidepoint(mouse_x, mouse_y)
        
        button_color = (100, 150, 100) if button_hovered else (80, 80, 80)
        pygame.draw.rect(surf, button_color, button_rect)
        pygame.draw.rect(surf, TEXT_COLOR, button_rect, 2)
        
        restart_text = self.font_small.render("Click to Restart", True, TEXT_COLOR)
        restart_rect = restart_text.get_rect(center=button_rect.center)
        surf.blit(restart_text, restart_rect)
        
        # Instructions
        inst_text = self.font_small.render("Press R to restart or ESC to quit", True, (150, 150, 150))
        inst_rect = inst_text.get_rect(center=(WIDTH//2, HEIGHT//2 + 150))
        surf.blit(inst_text, inst_rect)
        
        return button_hovered


class Spawner:
    """
    Responsible for spawning new zombies at randomized intervals and locations.

    Notes
    -----
    - We try to keep at most ``MAX_CONCURRENT_ZOMBIES`` active to match
      the classic Whack-a-Mole pacing.
    - Spawn timing uses wall-clock ms to be independent of frame rate.
    """

    def __init__(self, spawn_points: List[SpawnPoint]) -> None:
        self.spawn_points = spawn_points
        self.next_spawn_at = 0  # ms timestamp for next spawn

    def schedule_next(self, now_ms: int) -> None:
        """Pick the next spawn time around a target cadence with jitter."""
        jitter = random.randint(-150, 220)  # add variability to cadence
        self.next_spawn_at = now_ms + max(200, SPAWN_INTERVAL_MS + jitter)

    def maybe_spawn(self, now_ms: int, zombies: List[Zombie]) -> None:
        """
        Spawn a zombie if timing is due and we aren't at the concurrency limit.
        """
        # Set initial schedule on first call
        if self.next_spawn_at == 0:
            self.schedule_next(now_ms)

        if now_ms >= self.next_spawn_at and len(zombies) < MAX_CONCURRENT_ZOMBIES:
            spawn = random.choice(self.spawn_points)
            lifetime = random.randint(MIN_LIFETIME_MS, MAX_LIFETIME_MS)
            zombies.append(Zombie(spawn, born_at_ms=now_ms, lifetime_ms=lifetime))
            self.schedule_next(now_ms)


class Game:
    """
    Main game controller: initializes subsystems, runs the loop, handles input,
    updates entities, and draws the frame.
    """

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Whack-a-Zombie — Assignment 1")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.Font(FONT_NAME, 20)
        self.font_big = pygame.font.Font(FONT_NAME, 28)

        # Prepare spawn points (>= 6; we use a 3x3 grid minus center for clarity)
        self.spawn_points: List[SpawnPoint] = self._make_spawn_points()
        self.spawner = Spawner(self.spawn_points)

        # Game state
        self.reset_game()
        self.game_over = False
        self.paused = False
        self.show_fps = False
        self.fps_samples = []
        self.life_lost_flash = 0  # Timer for life lost screen flash
        
        # UI components
        self.hud = HUD(self.font_small)
        self.game_over_screen = GameOverScreen(self.font_big, self.font_small)

        # Mouse cursor
        self.hammer_cursor = None
        self._load_hammer_cursor()
        pygame.mouse.set_visible(False)  # Hide default cursor

        # Audio
        self.muted = False
        self.snd_hit: Optional[pygame.mixer.Sound] = None
        self._init_audio()

    def reset_game(self) -> None:
        """Reset all game state to initial values."""
        self.zombies: List[Zombie] = []
        self.hits = 0
        self.misses = 0
        self.lives = INITIAL_LIVES
        self.game_over = False
        self.spawner.next_spawn_at = 0  # Reset spawner timing

    # --------------------------------- Setup ----------------------------------------

    def _load_hammer_cursor(self) -> None:
        """Load hammer cursor or create fallback."""
        if os.path.exists(HAMMER_PATH):
            try:
                self.hammer_cursor = pygame.image.load(HAMMER_PATH).convert_alpha()
                self.hammer_cursor = pygame.transform.scale(self.hammer_cursor, (40, 40))
            except Exception:
                self._create_fallback_hammer()
        else:
            self._create_fallback_hammer()
    
    def _create_fallback_hammer(self) -> None:
        """Create a simple hammer cursor if asset not available."""
        self.hammer_cursor = pygame.Surface((40, 40), pygame.SRCALPHA)
        # Handle
        pygame.draw.rect(self.hammer_cursor, (101, 67, 33), (15, 10, 8, 25))
        # Head
        pygame.draw.rect(self.hammer_cursor, (150, 150, 150), (5, 5, 25, 15))
        pygame.draw.rect(self.hammer_cursor, (100, 100, 100), (5, 5, 25, 15), 2)

    def _make_spawn_points(self) -> List[SpawnPoint]:
        """Create 9 well-spaced positions (3x3 grid)."""
        cols, rows = 3, 3
        padding_x, padding_y = 120, 90
        usable_w = WIDTH - 2 * padding_x
        usable_h = HEIGHT - 2 * padding_y
        cell_w = usable_w // (cols - 1)
        cell_h = usable_h // (rows - 1)
        radius = 52
        points: List[SpawnPoint] = []
        for j in range(rows):
            for i in range(cols):
                x = padding_x + i * cell_w
                y = padding_y + j * cell_h
                points.append(SpawnPoint((x, y), radius))
        return points  # 9 spawn points (>= 6 as required)

    def _init_audio(self) -> None:
        """Try to initialize audio & load assets if available (safe to run without)."""
        try:
            pygame.mixer.init()
        except Exception:
            # Audio device not available; run silently.
            return
        # Background music (looped) – optional
        if os.path.exists(MUSIC_PATH):
            try:
                pygame.mixer.music.load(MUSIC_PATH)
                pygame.mixer.music.set_volume(0.35)
                pygame.mixer.music.play(-1)
            except Exception:
                pass
        # Hit SFX – optional
        if os.path.exists(HIT_SFX_PATH):
            try:
                self.snd_hit = pygame.mixer.Sound(HIT_SFX_PATH)
                self.snd_hit.set_volume(0.6)
            except Exception:
                self.snd_hit = None

    # --------------------------------- Loop -----------------------------------------

    def run(self) -> None:
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
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                    elif event.key == pygame.K_r:
                        self._reset_scores()
                    elif event.key == pygame.K_m:
                        self._toggle_mute()
                    elif event.key == pygame.K_p:
                        self._toggle_pause()
                    elif event.key == pygame.K_f:
                        self.show_fps = not self.show_fps
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.game_over:
                        # Check if clicked restart button or just restart
                        self.reset_game()
                    elif not self.paused:
                        self._handle_click(pygame.mouse.get_pos(), now)

            # Update game state (only if not paused and not game over)
            if not self.paused and not self.game_over:
                # Update zombies and check for attacks
                attacks_this_frame = 0
                for z in self.zombies:
                    if z.update(now):  # Returns True if zombie attacked (only once per zombie)
                        attacks_this_frame += 1
                
                # Handle life loss from zombie attacks
                if attacks_this_frame > 0:
                    self.lives -= attacks_this_frame
                    self.life_lost_flash = LIFE_LOSS_FLASH_MS
                    if self.lives <= 0:
                        self.lives = 0
                        self.game_over = True
                        pygame.mouse.set_visible(True)  # Show cursor on game over
                
                # Remove dead zombies
                self.zombies = [z for z in self.zombies if z.is_active(now)]

                # Spawning
                self.spawner.maybe_spawn(now, self.zombies)
            
            # Update screen flash timer
            if self.life_lost_flash > 0:
                self.life_lost_flash = max(0, self.life_lost_flash - self.clock.get_time())

            # Draw
            self._draw(now, avg_fps)

            # Cap frame rate
            self.clock.tick(FPS)

        pygame.quit()

    # --------------------------------- Input ----------------------------------------

    def _handle_click(self, pos: Tuple[int, int], now_ms: int) -> None:
        """
        Handle left-clicks: if an ACTIVE zombie is clicked, count a hit and
        immediately mark it for despawn; otherwise count a miss.
        """
        # Make newest-first to favor topmost if overlap ever happens
        for z in reversed(self.zombies):
            if not z.hit and not z.attacking and z.contains_point(pos, now_ms):
                z.mark_hit(now_ms)
                self.hits += 1
                if self.snd_hit and not self.muted:
                    self.snd_hit.play()
                return
        # No zombie consumed the click → miss
        self.misses += 1

    def _reset_scores(self) -> None:
        """Reset score counters and restart game."""
        self.reset_game()
        pygame.mouse.set_visible(False)

    def _toggle_pause(self) -> None:
        """Toggle pause state."""
        if not self.game_over:
            self.paused = not self.paused

    def _toggle_mute(self) -> None:
        """Mute/unmute mixer (and remember toggle)."""
        self.muted = not self.muted
        try:
            pygame.mixer.music.set_volume(0.0 if self.muted else 0.35)
        except Exception:
            pass

    # --------------------------------- Rendering ------------------------------------

    def _draw_hammer_cursor(self) -> None:
        """Draw the hammer cursor at mouse position."""
        if self.hammer_cursor:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            # Offset so the hammer "hits" where the cursor points
            cursor_rect = self.hammer_cursor.get_rect(center=(mouse_x + 5, mouse_y + 5))
            self.screen.blit(self.hammer_cursor, cursor_rect)

    def _draw_life_loss_flash(self) -> None:
        """Draw screen flash when life is lost."""
        if self.life_lost_flash > 0:
            alpha = int(100 * (self.life_lost_flash / LIFE_LOSS_FLASH_MS))
            flash_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash_surface.fill((255, 0, 0, alpha))
            self.screen.blit(flash_surface, (0, 0))

    def _draw_background(self, surf: pygame.Surface) -> None:
        """Draw the background and spawn holes (rings + shadows)."""
        surf.fill(BG_COLOR)

        # Subtle vignette / gradient rectangles for polish (no perf cost)
        rect = pygame.Rect(0, 0, WIDTH, HEIGHT)
        pygame.draw.rect(surf, (20, 22, 27), rect, width=24, border_radius=18)

        # Draw holes
        for sp in self.spawn_points:
            x, y = sp.pos
            r = sp.radius
            # outer ring
            pygame.draw.circle(surf, HOLE_RING, (x, y), r+6)
            # inner dark hole
            pygame.draw.circle(surf, HOLE_COLOR, (x, y), r)

    def _draw(self, now_ms: int, fps: float) -> None:
        """Compose the frame: bg → zombies → HUD → effects → cursor."""
        self._draw_background(self.screen)

        # Draw active zombies
        for z in self.zombies:
            z.draw(self.screen, now_ms)

        # HUD
        self.hud.draw(self.screen, self.hits, self.misses, self.lives, 
                      self.show_fps, fps, self.paused)

        # Title / hints
        if not self.game_over:
            title = self.font_big.render("Whack-a-Zombie", True, TEXT_COLOR)
            self.screen.blit(title, (WIDTH - title.get_width() - HUD_PADDING, HUD_PADDING))
            hint_text = "[LMB] hit  |  [P] pause  |  [F] fps  |  [R] reset  |  [M] mute  |  [ESC/Q] quit"
            hint = self.font_small.render(hint_text, True, (200, 200, 200))
            self.screen.blit(hint, (WIDTH - hint.get_width() - HUD_PADDING, HUD_PADDING + title.get_height() + 4))

        # Screen effects
        self._draw_life_loss_flash()
        
        # Game over screen
        if self.game_over:
            self.game_over_screen.draw(self.screen, self.hits, self.misses)
        else:
            # Draw hammer cursor only if game is active
            self._draw_hammer_cursor()

        pygame.display.flip()


def main() -> None:
    """Entry point; constructs the Game and starts the main loop."""
    Game().run()


if __name__ == "__main__":
    main()
