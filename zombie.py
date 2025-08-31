from __future__ import annotations

"""Zombie entity: lifecycle, animation, hit testing, and rendering.

A zombie spawns, plays idle animation, times out to attack if not hit (costing
the player a life), and then despawns with animation. Uses sprite sheets if
available, but degrades gracefully.
"""

import math
import os
import pygame
import random

from constants import (
    ATTACK_ANIM_MS, 
    ZOMBIE_SPRITE_PATH, 
    FLASH_COLOR
)
from models import SpawnPoint

class Zombie:
    """
    Represents one zombie "head" that can be whacked.

    Lifecycle:
    - SPAWNING: scales up from 0.6 → 1.0 over ~120ms for a "pop" effect.
    - ACTIVE:   remains visible until lifetime expires or it's hit.
    - ATTACKING: plays attack animation when lifetime expires without being hit.
    - DESPAWN:  scales down to 0 over ~160ms, then is removed.

    Timings are driven via pygame.time.get_ticks() (ms-precise, frame-rate independent).
    
    Visual Effects:
    - Spawn effects: dust particles and yellow glow when appearing
    - Hit effects: colorful impact particles when hit
    - Death animation: sprite-based death sequence
    - Health bar: color-coded timer showing remaining lifetime
    """

    SPAWN_ANIM_MS = 150
    DESPAWN_ANIM_MS = 250
    HIT_FLASH_MS = 150

    SPRITE_BASE_W = 80
    SPRITE_BASE_H = 70
    SPRITE_SCALE  = 1.35   # make the zombie bigger (~108x95)

    # Class variables for sprite management
    sprite_sheet = None
    normal_frames = []
    attack_frames = []
    death_frames = []
    sprites_loaded = False

    @classmethod
    def _scaled_size(cls, scale_factor: float = 1.0) -> tuple[int, int]:
        """Return (w, h) used everywhere for this zombie's scaled sprite."""
        # Apply additional scale factor for responsive sizing
        responsive_scale = cls.SPRITE_SCALE * scale_factor
        return (int(cls.SPRITE_BASE_W * responsive_scale),
                int(cls.SPRITE_BASE_H * responsive_scale))

    @classmethod
    def load_sprites(cls):
        """Load zombie sprites from sprite sheet."""
        if cls.sprites_loaded:
            return

        if os.path.exists(ZOMBIE_SPRITE_PATH):
            try:
                cls.sprite_sheet = pygame.image.load(ZOMBIE_SPRITE_PATH).convert_alpha()
                sheet_width, sheet_height = cls.sprite_sheet.get_size()

                cols, rows = 11, 12
                sprite_width = sheet_width // cols
                sprite_height = sheet_height // rows
                
                # Desired output size (scaled)
                out_w, out_h = cls._scaled_size()

                normal_positions = [
                    (0, 0), (1, 0), (2, 0), (3, 0),
                    (0, 1), (1, 1), (2, 1), (3, 1),
                ]
                attack_positions = [(4, 2), (5, 2), (6, 2), (7, 2)]
                death_positions = [(0, 10), (1, 10), (2, 10), (3, 10)]
                for col, row in normal_positions:
                    x = col * sprite_width
                    y = row * sprite_height
                    rect = pygame.Rect(x, y, sprite_width, sprite_height)
                    frame = cls.sprite_sheet.subsurface(rect)
                    cls.normal_frames.append(pygame.transform.scale(frame, (out_w, out_h)))

                for col, row in attack_positions:
                    x = col * sprite_width
                    y = row * sprite_height
                    rect = pygame.Rect(x, y, sprite_width, sprite_height)
                    frame = cls.sprite_sheet.subsurface(rect)
                    cls.attack_frames.append(pygame.transform.scale(frame, (out_w, out_h)))

                for col, row in death_positions:
                    x = col * sprite_width
                    y = row * sprite_height
                    rect = pygame.Rect(x, y, sprite_width, sprite_height)
                    frame = cls.sprite_sheet.subsurface(rect)
                    cls.death_frames.append(pygame.transform.scale(frame, (out_w, out_h)))

                cls.sprites_loaded = True
            except Exception as e:
                print(f"Failed to load sprites: {e}")
                cls.sprites_loaded = False
        else:
            cls.sprites_loaded = False

    def __init__(self, spawn: SpawnPoint, born_at_ms: int, lifetime_ms: int) -> None:
        self.spawn = spawn
        self.born_at = born_at_ms
        self.lifetime = lifetime_ms
        self.dead = False
        self.hit = False
        self.hit_time: int | None = None
        self.despawn_start: int | None = None
        self.attacking = False
        self.attack_start: int | None = None
        self.has_dealt_damage = False
        self.animation_frame = 0
        
        # Spawn effects
        self.spawn_particles = []
        self.spawn_dust_alpha = 255
        self.spawn_glow_alpha = 255
        
        # Hit effects
        self.hit_particles = []
        self.hit_flash_timer = 0

        if not Zombie.sprites_loaded:
            Zombie.load_sprites()
        
        # Store scale factor for responsive sizing
        self.scale_factor = 1.0

    # ------------------------------- Update & State ----------------------------------

    def is_active(self, now_ms: int) -> bool:
        return not self.dead

    def mark_hit(self, now_ms: int) -> None:
        if self.hit or self.dead or self.attacking:
            return
        self.hit = True
        self.hit_time = now_ms
        self.despawn_start = now_ms
        
        # Create hit effects at the hit position
        self.create_hit_effects(self.spawn.pos)

    def start_attack(self, now_ms: int) -> None:
        if self.hit or self.dead or self.attacking:
            return
        self.attacking = True
        self.attack_start = now_ms

    def is_attacking(self) -> bool:
        return self.attacking and not self.hit and not self.dead

    def update(self, now_ms: int) -> bool:
        attack_occurred = False

        if not self.hit \
            and not self.attacking \
            and (now_ms - self.born_at >= self.lifetime) \
            and self.despawn_start is None:
                self.start_attack(now_ms)

        if self.attacking \
            and self.attack_start is not None \
            and not self.has_dealt_damage \
            and now_ms - self.attack_start >= ATTACK_ANIM_MS:
                attack_occurred = True
                self.has_dealt_damage = True
                self.despawn_start = now_ms

        if self.despawn_start is not None \
            and now_ms - self.despawn_start >= self.DESPAWN_ANIM_MS:
                self.dead = True

        return attack_occurred

    def update_scale_factor(self, new_scale_factor: float) -> None:
        """Update the zombie's scale factor for responsive sizing."""
        self.scale_factor = new_scale_factor

    def create_hit_effects(self, hit_pos: tuple[int, int]) -> None:
        """Create particle effects when zombie is hit."""
        
        # Create impact particles
        for _ in range(12):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1, 3)  # Reduced speed for better visibility
            dx = math.cos(angle) * speed
            dy = math.sin(angle) * speed
            
            particle = {
                'x': hit_pos[0],
                'y': hit_pos[1],
                'dx': dx,
                'dy': dy,
                'life': random.randint(80, 120),  # Increased lifetime
                'max_life': 120,  # Increased max lifetime
                'alpha': 255,
                'size': random.randint(4, 7),  # Slightly larger particles
                'color': random.choice([(255, 100, 100), (255, 200, 100), (255, 255, 100)])  # Red, orange, yellow
            }
            self.hit_particles.append(particle)
        
        # Set hit flash timer
        self.hit_flash_timer = 150

    def update_hit_effects(self, now_ms: int) -> None:
        """Update hit particle effects."""
        # Update hit flash timer
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= 16  # 16ms per frame at 60fps
        
        # Update hit particles
        for particle in self.hit_particles[:]:
            particle['life'] -= 16
            if particle['life'] <= 0:
                self.hit_particles.remove(particle)
            else:
                # Move particles outward
                particle['x'] += particle['dx']
                particle['y'] += particle['dy']
                particle['alpha'] = int(255 * (particle['life'] / particle['max_life']))
                # Add gravity effect
                particle['dy'] += 0.2

    def draw_spawn_effects(self, surf: pygame.Surface) -> None:
        """Draw spawn particle effects and glow."""
        # Draw dust particles
        for particle in self.spawn_particles:
            if particle['alpha'] > 0:
                # Create particle surface with alpha
                particle_surf = pygame.Surface((particle['size'], particle['size']), pygame.SRCALPHA)
                particle_color = (139, 69, 19, particle['alpha'])  # Brown dust color
                pygame.draw.circle(particle_surf, particle_color, (particle['size']//2, particle['size']//2), particle['size']//2)
                surf.blit(particle_surf, (particle['x'] - particle['size']//2, particle['y'] - particle['size']//2))
        
        # Draw spawn glow effect
        if self.spawn_glow_alpha > 0:
            center_x, center_y = self.spawn.pos
            glow_radius = int(self.spawn.radius * 1.5)
            
            # Create glow surface
            glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            glow_color = (255, 255, 0, self.spawn_glow_alpha // 3)  # Yellow glow
            
            # Draw multiple circles for glow effect
            for i in range(3):
                alpha = self.spawn_glow_alpha // (3 * (i + 1))
                radius = glow_radius - i * 5
                if radius > 0:
                    glow_color = (255, 255, 0, alpha)
                    pygame.draw.circle(glow_surf, glow_color, (glow_radius, glow_radius), radius)
            
            surf.blit(glow_surf, (center_x - glow_radius, center_y - glow_radius))

    def draw_hit_effects(self, surf: pygame.Surface) -> None:
        """Draw hit particle effects."""
        # Draw hit particles
        for particle in self.hit_particles:
            if particle['alpha'] > 0:
                # Create particle surface with alpha
                particle_surf = pygame.Surface((particle['size'], particle['size']), pygame.SRCALPHA)
                particle_color = (*particle['color'], particle['alpha'])
                pygame.draw.circle(particle_surf, particle_color, (particle['size']//2, particle['size']//2), particle['size']//2)
                surf.blit(particle_surf, (particle['x'] - particle['size']//2, particle['y'] - particle['size']//2))

    def update_spawn_effects(self, now_ms: int) -> None:
        """Update spawn particle effects and glow."""
        # Update dust alpha (fade out over spawn animation)
        if now_ms - self.born_at < self.SPAWN_ANIM_MS:
            progress = (now_ms - self.born_at) / self.SPAWN_ANIM_MS
            self.spawn_dust_alpha = int(255 * (1 - progress))
            self.spawn_glow_alpha = int(255 * (1 - progress))
        
        # Update particles
        for particle in self.spawn_particles[:]:
            particle['life'] -= 16  # 16ms per frame at 60fps
            if particle['life'] <= 0:
                self.spawn_particles.remove(particle)
            else:
                # Move particles outward
                particle['x'] += particle['dx']
                particle['y'] += particle['dy']
                particle['alpha'] = int(255 * (particle['life'] / particle['max_life']))

    def create_spawn_particles(self) -> None:
        """Create particle effects for zombie spawning."""
        
        center_x, center_y = self.spawn.pos
        
        # Create dust particles
        for _ in range(8):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.5, 1.5)  # Reduced speed for better visibility
            dx = math.cos(angle) * speed
            dy = math.sin(angle) * speed
            
            particle = {
                'x': center_x,
                'y': center_y,
                'dx': dx,
                'dy': dy,
                'life': random.randint(60, 90),  # Increased lifetime
                'max_life': 90,  # Increased max lifetime
                'alpha': 255,
                'size': random.randint(3, 5)  # Slightly larger particles
            }
            self.spawn_particles.append(particle)

    # ------------------------------- Rendering ---------------------------------------

    def get_vertical_offset(self, now_ms: int) -> int:
        """
        Positive values = zombie is below ground, 0 = fully emerged.
        Uses scaled sprite height so rise/sink matches visual size.
        """
        _, sprite_height = self._scaled_size(self.scale_factor)

        # Spawn animation: rise up
        t_spawn = now_ms - self.born_at
        if t_spawn < self.SPAWN_ANIM_MS:
            progress = t_spawn / self.SPAWN_ANIM_MS
            eased_progress = 1 - (1 - progress) * (1 - progress)
            return int(sprite_height * (1 - eased_progress))

        # Attack bob
        if self.attacking and self.attack_start is not None:
            t = (now_ms - self.attack_start) / ATTACK_ANIM_MS
            if t < 1.0:
                bounce_offset = int(5 * math.sin(t * math.pi * 6))
                return -bounce_offset

        # Despawn: sink
        if self.despawn_start is not None:
            t = (now_ms - self.despawn_start) / self.DESPAWN_ANIM_MS
            if t < 1.0:
                eased_progress = t * t
                return int(sprite_height * eased_progress)
            return sprite_height

        return 0

    def get_current_sprite(self, now_ms: int) -> pygame.Surface | None:
        if not self.sprites_loaded or not (self.normal_frames or self.attack_frames or self.death_frames):
            return None

        frame_duration = 100
        self.animation_frame = (now_ms // frame_duration) % max(1, len(self.normal_frames))

        if self.hit and self.death_frames:
            frame_idx = min(self.animation_frame, len(self.death_frames) - 1)
            return self.death_frames[frame_idx]
        if self.attacking and self.attack_frames:
            frame_idx = min(self.animation_frame, len(self.attack_frames) - 1)
            return self.attack_frames[frame_idx]
        if self.normal_frames:
            frame_idx = self.animation_frame % len(self.normal_frames)
            return self.normal_frames[frame_idx]
        return None

    def draw_timer_bar(self, surf: pygame.Surface, now_ms: int) -> None:
        if self.hit or self.attacking or self.dead:
            return

        elapsed = now_ms - self.born_at
        time_remaining = max(0, self.lifetime - elapsed)
        progress = time_remaining / self.lifetime

        bar_width = self.spawn.radius * 2
        bar_height = 4
        center_x, center_y = self.spawn.pos
        bar_x = center_x - bar_width // 2
        bar_y = center_y - self.spawn.radius - 15

        pygame.draw.rect(surf, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))

        filled_width = int(bar_width * progress)
        if progress > 0.6:
            color = (0, 255, 0)
        elif progress > 0.3:
            color = (255, 255, 0)
        else:
            color = (255, 0, 0)

        if filled_width > 0:
            pygame.draw.rect(surf, color, (bar_x, bar_y, filled_width, bar_height))

        pygame.draw.rect(surf, (200, 200, 200), (bar_x, bar_y, bar_width, bar_height), 1)

    def draw(self, surf: pygame.Surface, now_ms: int) -> None:
        """
        Render using sprites with vertical offset for rise/fall animations.
        Adds a small downward anchor so the sprite visually centers in the hole.
        """
        center = self.spawn.pos
        vertical_offset = self.get_vertical_offset(now_ms)

        # Draw spawn effects first (behind zombie)
        self.draw_spawn_effects(surf)
        
        # Draw hit effects (behind zombie)
        self.draw_hit_effects(surf)
        
        # Timer bar behind zombie
        self.draw_timer_bar(surf, now_ms)

        sprite = self.get_current_sprite(now_ms)
        if sprite and self.sprites_loaded:
            display_sprite = sprite
            if self.hit and self.hit_time is not None and now_ms - self.hit_time < self.HIT_FLASH_MS:
                flash_sprite = sprite.copy()
                flash_alpha = int(180 * (1.0 - (now_ms - self.hit_time) / self.HIT_FLASH_MS))
                flash_surface = pygame.Surface(flash_sprite.get_size(), pygame.SRCALPHA)
                flash_surface.fill((*FLASH_COLOR, flash_alpha))
                flash_sprite.blit(flash_surface, (0, 0), special_flags=pygame.BLEND_ADD)
                display_sprite = flash_sprite

            sprite_rect = display_sprite.get_rect()
            sprite_rect.centerx = center[0]
            sprite_rect.centery = center[1] + vertical_offset
            surf.blit(display_sprite, sprite_rect)
            return

        print("No sprite available for drawing")

    def contains_point(self, point: tuple[int, int], now_ms: int) -> bool:
        """
        Rectangle-based hit test for zombie sprites. Only allow hits when zombie is not attacking.
        Uses the same scaled size and anchor as drawing so clicks feel correct.
        """
        if self.attacking:
            return False

        cx, cy = self.spawn.pos
        vertical_offset = self.get_vertical_offset(now_ms)

        if self.sprites_loaded and self.normal_frames:
            sprite_width, sprite_height = self.normal_frames[0].get_size()
        else:
            sprite_width, sprite_height = self._scaled_size(self.scale_factor)

        adjusted_cy = cy + vertical_offset

        rect_left   = cx - sprite_width // 2
        rect_top    = adjusted_cy - sprite_height // 2
        rect_right  = rect_left + sprite_width
        rect_bottom = rect_top + sprite_height

        px, py = point
        return (rect_left <= px <= rect_right) and (rect_top <= py <= rect_bottom)
