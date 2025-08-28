from __future__ import annotations

"""Zombie entity: lifecycle, animation, hit testing, and rendering.

A zombie spawns, plays idle animation, times out to attack if not hit (costing
the player a life), and then despawns with animation. Uses sprite sheets if
available, but degrades gracefully.
"""

import math
import os
import pygame

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
    def _scaled_size(cls) -> tuple[int, int]:
        """Return (w, h) used everywhere for this zombie's scaled sprite."""
        return (int(cls.SPRITE_BASE_W * cls.SPRITE_SCALE),
                int(cls.SPRITE_BASE_H * cls.SPRITE_SCALE))

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

        if not Zombie.sprites_loaded:
            Zombie.load_sprites()

    # ------------------------------- Update & State ----------------------------------

    def is_active(self, now_ms: int) -> bool:
        return not self.dead

    def mark_hit(self, now_ms: int) -> None:
        if self.hit or self.dead or self.attacking:
            return
        self.hit = True
        self.hit_time = now_ms
        self.despawn_start = now_ms

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

    # ------------------------------- Rendering ---------------------------------------

    def get_vertical_offset(self, now_ms: int) -> int:
        """
        Positive values = zombie is below ground, 0 = fully emerged.
        Uses scaled sprite height so rise/sink matches visual size.
        """
        _, sprite_height = self._scaled_size()

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
            sprite_width, sprite_height = self._scaled_size()

        adjusted_cy = cy + vertical_offset

        rect_left   = cx - sprite_width // 2
        rect_top    = adjusted_cy - sprite_height // 2
        rect_right  = rect_left + sprite_width
        rect_bottom = rect_top + sprite_height

        px, py = point
        return (rect_left <= px <= rect_right) and (rect_top <= py <= rect_bottom)
