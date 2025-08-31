from __future__ import annotations

"""Brain pickup entity that grants a life on click.

Fades in, idles until lifetime expires or clicked, then fades out. Simple
rectangle hitbox based on sprite bounds.
"""

import os
import pygame

from constants import BRAIN_PATH, BRAIN_LIFETIME_MS
from models import SpawnPoint

class Brain:
    """
    Represents a brain pickup that grants +1 life when clicked.
    
    Lifecycle:
    - SPAWNING: fades in over ~200ms
    - ACTIVE: remains visible until lifetime expires or clicked
    - DESPAWN: fades out over ~300ms, then is removed
    
    Timings are driven via pygame.time.get_ticks() (ms-precise, frame-rate independent).
    """

    SPAWN_ANIM_MS = 200
    DESPAWN_ANIM_MS = 300
    PICKUP_FLASH_MS = 150
    
    # Sprite scaling
    SPRITE_SCALE = 0.15
    
    # Class variables for sprite management
    sprite_image = None
    sprites_loaded = False
    
    @classmethod
    def load_sprite(cls):
        """Load brain sprite from assets."""
        if cls.sprites_loaded:
            return
            
        if os.path.exists(BRAIN_PATH):
            try:
                original = pygame.image.load(BRAIN_PATH).convert_alpha()
                original_w, original_h = original.get_size()
                
                print(f"Original brain sprite size: {original_w}x{original_h}")
                
                # Store original for responsive scaling
                cls.original_sprite = original
                cls.sprites_loaded = True
                print(f"Successfully loaded brain sprite: {original_w}x{original_h}")
            except Exception as e:
                print(f"Failed to load brain sprite: {e}")
                cls.sprites_loaded = False
        else:
            cls.sprites_loaded = False

    def __init__(self, spawn: SpawnPoint, born_at_ms: int) -> None:
        self.spawn = spawn
        self.born_at = born_at_ms
        self.lifetime = BRAIN_LIFETIME_MS
        self.dead = False
        self.picked_up = False
        self.pickup_time: int | None = None
        self.despawn_start: int | None = None
        
        # Store scale factor for responsive sizing
        self.scale_factor = 1.0
        
        if not Brain.sprites_loaded:
            Brain.load_sprite()

    # ------------------------------- Update & State ----------------------------------
    
    def is_active(self, now_ms: int) -> bool:
        return not self.dead
    
    def mark_picked_up(self, now_ms: int) -> None:
        """Mark brain as picked up by player."""
        if self.picked_up or self.dead:
            return
        self.picked_up = True
        self.pickup_time = now_ms
        self.despawn_start = now_ms
    
    def update(self, now_ms: int) -> None:
        """Update brain state - check for lifetime expiration."""
        # Auto-despawn if lifetime expired and not picked up
        if not self.picked_up and not self.dead and self.despawn_start is None:
            if now_ms - self.born_at >= self.lifetime:
                self.despawn_start = now_ms
        
        # Remove brain after despawn animation
        if self.despawn_start is not None and now_ms - self.despawn_start >= self.DESPAWN_ANIM_MS:
            self.dead = True

    def update_scale_factor(self, new_scale_factor: float) -> None:
        """Update the brain's scale factor for responsive sizing."""
        self.scale_factor = new_scale_factor

    def get_scaled_sprite(self) -> pygame.Surface | None:
        """Get brain sprite scaled according to current scale factor."""
        if not self.sprites_loaded or not hasattr(Brain, 'original_sprite'):
            return None
        
        # Calculate new size with responsive scaling
        original_w, original_h = Brain.original_sprite.get_size()
        new_w = int(original_w * Brain.SPRITE_SCALE * self.scale_factor)
        new_h = int(original_h * Brain.SPRITE_SCALE * self.scale_factor)
        
        return pygame.transform.scale(Brain.original_sprite, (new_w, new_h))

    # ------------------------------- Rendering ---------------------------------------
    
    def get_alpha(self, now_ms: int) -> int:
        """Calculate current alpha for fade in/out effects."""
        # Spawn fade-in
        spawn_elapsed = now_ms - self.born_at
        if spawn_elapsed < self.SPAWN_ANIM_MS:
            progress = spawn_elapsed / self.SPAWN_ANIM_MS
            return int(255 * progress)
        
        # Despawn fade-out
        if self.despawn_start is not None:
            despawn_elapsed = now_ms - self.despawn_start
            if despawn_elapsed < self.DESPAWN_ANIM_MS:
                progress = despawn_elapsed / self.DESPAWN_ANIM_MS
                return int(255 * (1.0 - progress))
        
        return 255  # Fully visible
    
    def draw(self, surf: pygame.Surface, now_ms: int) -> None:
        """Render the brain pickup."""
        center = self.spawn.pos
        alpha = self.get_alpha(now_ms)
        
        if alpha <= 0:
            return
            
        if self.sprites_loaded:
            # Get scaled sprite
            display_sprite = self.get_scaled_sprite()
            if display_sprite is None:
                return
            
            # Apply alpha
            if alpha < 255:
                display_sprite.set_alpha(alpha)
            
            # Add pickup flash effect
            if self.picked_up and self.pickup_time is not None and now_ms - self.pickup_time < self.PICKUP_FLASH_MS:
                flash_alpha = int(128 * (1.0 - (now_ms - self.pickup_time) / self.PICKUP_FLASH_MS))
                flash_surface = pygame.Surface(display_sprite.get_size(), pygame.SRCALPHA)
                flash_surface.fill((255, 255, 255, flash_alpha))
                display_sprite.blit(flash_surface, (0, 0), special_flags=pygame.BLEND_ADD)
            
            sprite_rect = display_sprite.get_rect(center=center)
            surf.blit(display_sprite, sprite_rect)
    
    def contains_point(self, point: tuple[int, int]) -> bool:
        """Check if a point is within the brain's clickable area."""
        if self.picked_up or self.dead:
            return False
        if self.sprites_loaded:
            # Use scaled sprite bounds
            display_sprite = self.get_scaled_sprite()
            if display_sprite is None:
                return False
            sprite_rect = display_sprite.get_rect(center=self.spawn.pos)
            return sprite_rect.collidepoint(point)
        return False