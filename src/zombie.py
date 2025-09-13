from __future__ import annotations

# enables forward references and delayed evaluation of type annotations.

import math
import os
import pygame
import random

from .constants import (
    ATTACK_ANIM_MS, 
    ZOMBIE_SPRITE_PATH, 
    FLASH_COLOR
)
from .models import SpawnPoint

class Zombie:
    """
    Represents one zombie "head" that can be whacked.

    Lifecycle:
    - SPAWNING:     scales up for a "pop" effect.
    - ACTIVE:       remains visible until lifetime expires or it's hit.
    - ATTACKING:    plays attack animation when lifetime expires without being hit.
    - DESPAWN:      scales down and is removed.

    Timings are driven via pygame.time.get_ticks() (frame-rate independent).
    """

    SPAWN_ANIM_MS = 150
    DESPAWN_ANIM_MS = 250
    HIT_FLASH_MS = 150

    SPRITE_BASE_W = 80
    SPRITE_BASE_H = 70
    SPRITE_SCALE  = 1.35   # make the zombie bigger (~108x95)

    ANCHOR_OFFSET_X = -18
    ANCHOR_OFFSET_Y = -6

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
                # Sprite sheet is a PNG image now being organized into 11 columns and 12 rows.
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

        # zombie is not hit by user
        # + zombie is not attacking
        # + zombie lifetime has expired
        # + zombie not start despawning
        # ==> start attacking
        if not self.hit \
            and not self.attacking \
            and (now_ms - self.born_at >= self.lifetime) \
            and self.despawn_start is None:
                self.start_attack(now_ms)

        # zombie is attacking
        # + zombie attact time is set already 
        # + zombie has not dealt damage yet
        # + attack animation has finished
        # ==> deal damage and start despawning
        if self.attacking \
            and self.attack_start is not None \
            and not self.has_dealt_damage \
            and now_ms - self.attack_start >= ATTACK_ANIM_MS:
                attack_occurred = True
                self.has_dealt_damage = True
                self.despawn_start = now_ms

        # zombie is despawning
        # + zombie despawn animation is done
        # ==> zombie should be die
        if self.despawn_start is not None \
            and now_ms - self.despawn_start >= self.DESPAWN_ANIM_MS:
                self.dead = True

        return attack_occurred

    def update_scale_factor(self, new_scale_factor: float) -> None:
        """Update the zombie's scale factor for responsive sizing."""
        if self.scale_factor != new_scale_factor:
            self.scale_factor = new_scale_factor
            # Reload sprites with new scale factor to ensure proper sizing
            self._reload_sprites_with_new_scale()

    def _reload_sprites_with_new_scale(self) -> None:
        """Reload zombie sprites with the current scale factor for responsive sizing."""
        if not Zombie.sprites_loaded or not Zombie.sprite_sheet:
            return
            
        # Clear existing scaled sprites
        Zombie.normal_frames.clear()
        Zombie.attack_frames.clear()
        Zombie.death_frames.clear()
        
        # Get new scaled size
        out_w, out_h = self._scaled_size(self.scale_factor)
        
        # Get Sprite Sheet Dimensions
        sheet_width, sheet_height = Zombie.sprite_sheet.get_size()
        cols, rows = 11, 12
        sprite_width = sheet_width // cols
        sprite_height = sheet_height // rows
        
        # Reload each animation type 
        # - extract each frame 
        # - scale it to the new size 
        # - add to the appropriate frame list 

        # Reload normal frames
        normal_positions = [
            (0, 0), (1, 0), (2, 0), (3, 0),
            (0, 1), (1, 1), (2, 1), (3, 1),
        ]
        for col, row in normal_positions:
            x = col * sprite_width
            y = row * sprite_height
            rect = pygame.Rect(x, y, sprite_width, sprite_height)
            frame = Zombie.sprite_sheet.subsurface(rect)
            Zombie.normal_frames.append(pygame.transform.scale(frame, (out_w, out_h)))
        
        # Reload attack frames
        attack_positions = [(4, 2), (5, 2), (6, 2), (7, 2)]
        for col, row in attack_positions:
            x = col * sprite_width
            y = row * sprite_height
            rect = pygame.Rect(x, y, sprite_width, sprite_height)
            frame = Zombie.sprite_sheet.subsurface(rect)
            Zombie.attack_frames.append(pygame.transform.scale(frame, (out_w, out_h)))
        
        # Reload death frames
        death_positions = [(0, 10), (1, 10), (2, 10), (3, 10)]
        for col, row in death_positions:
            x = col * sprite_width
            y = row * sprite_height
            rect = pygame.Rect(x, y, sprite_width, sprite_height)
            frame = Zombie.sprite_sheet.subsurface(rect)
            Zombie.death_frames.append(pygame.transform.scale(frame, (out_w, out_h)))

    def create_hit_effects(self, hit_pos: tuple[int, int]) -> None:
        """Create particle effects when zombie is hit."""
        
        # Create impact particles
        for _ in range(12):
            # Generate random direction (0 to 2π radians = full circle)
            angle = random.uniform(0, 2 * math.pi)
            # Random speed between 1-3 pixels per frame for visible movement
            speed = random.uniform(1, 3)  # Reduced speed for better visibility
            
            # Calculate velocity components using trigonometry
            dx = math.cos(angle) * speed  # Horizontal velocity
            dy = math.sin(angle) * speed  # Vertical velocity
            
            # Create particle dictionary with all necessary properties
            particle = {
                'x': hit_pos[0],      # Starting X position (hit location)
                'y': hit_pos[1],      # Starting Y position (hit location)
                'dx': dx,             # Horizontal velocity per frame
                'dy': dy,             # Vertical velocity per frame
                'life': random.randint(80, 120),  # Random lifetime (80-120 frames)
                'max_life': 120,      # Maximum lifetime for alpha calculation
                'alpha': 255,         # Starting alpha (fully opaque)
                'size': random.randint(4, 7),  # Random particle size (4-7 pixels)
                # Random color selection: red, orange, or yellow
                'color': random.choice([(255, 100, 100), (255, 200, 100), (255, 255, 100)])
            }
            self.hit_particles.append(particle)
        
        # Set hit flash timer for screen flash effect (150ms duration)
        self.hit_flash_timer = 150

    def update_hit_effects(self, now_ms: int) -> None:
        """Update hit particle effects."""
        # Update hit flash timer
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= 16  # 16ms per frame at 60fps
        
        # Update each hit particle (use [:] to avoid modification during iteration)
        for particle in self.hit_particles[:]:
            # Decrease particle lifetime
            particle['life'] -= 16  # 16ms per frame at 60fps
            
            # Remove dead particles from the list
            if particle['life'] <= 0:
                self.hit_particles.remove(particle)
            else:
                # Move particles based on their velocity
                particle['x'] += particle['dx']  # Update X position
                particle['y'] += particle['dy']  # Update Y position
                
                # Calculate alpha based on remaining lifetime (fade out effect)
                particle['alpha'] = int(255 * (particle['life'] / particle['max_life']))
                
                # Add gravity effect (particles fall down over time)
                particle['dy'] += 0.2  # Increase downward velocity each frame

    def draw_spawn_effects(self, surf: pygame.Surface) -> None:
        """Draw spawn particle effects and glow."""
        # Draw dust particles
        for particle in self.spawn_particles:
            # Only draw visible particles
            if particle['alpha'] > 0:
                # Create a surface for each particle with alpha support
                particle_surf = pygame.Surface((particle['size'], particle['size']), pygame.SRCALPHA)
                # Brown dust color with current alpha value
                particle_color = (139, 69, 19, particle['alpha'])  # Brown dust color
                # Draw circle particle centered on the surface
                pygame.draw.circle(particle_surf, particle_color, (particle['size']//2, particle['size']//2), particle['size']//2)
                # Blit particle to main surface at correct position
                surf.blit(particle_surf, (particle['x'] - particle['size']//2, particle['y'] - particle['size']//2))
        
        # Draw spawn glow effect
        if self.spawn_glow_alpha > 0:
            center_x, center_y = self.spawn.pos
            # Glow radius is 1.5x the spawn point radius
            glow_radius = int(self.spawn.radius * 1.5)
            
            # Create glow surface (square surface for circle)
            glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            # Base glow color (yellow with reduced alpha)
            glow_color = (255, 255, 0, self.spawn_glow_alpha // 3)  # Yellow glow
            
            # Draw multiple concentric circles for layered glow effect
            for i in range(3):
                # Calculate alpha for this layer (decreases with each layer)
                alpha = self.spawn_glow_alpha // (3 * (i + 1))
                # Calculate radius for this layer (decreases by 5 pixels each layer)
                radius = glow_radius - i * 5
                if radius > 0:  
                    glow_color = (255, 255, 0, alpha)  # Yellow with calculated alpha
                    # Draw circle centered on the glow surface
                    pygame.draw.circle(glow_surf, glow_color, (glow_radius, glow_radius), radius)
            
            # Blit the entire glow effect to the main surface
            surf.blit(glow_surf, (center_x - glow_radius, center_y - glow_radius))

    def draw_hit_effects(self, surf: pygame.Surface) -> None:
        """Draw hit particle effects."""
        # Draw hit particles
        for particle in self.hit_particles:
            if particle['alpha'] > 0:
                # Create a surface for each particle with alpha support
                particle_surf = pygame.Surface((particle['size'], particle['size']), pygame.SRCALPHA)
                # Combine particle color with current alpha value
                particle_color = (*particle['color'], particle['alpha'])
                # Draw circle particle centered on the surface
                pygame.draw.circle(particle_surf, particle_color, (particle['size']//2, particle['size']//2), particle['size']//2)
                # Blit particle to main surface at correct position
                surf.blit(particle_surf, (particle['x'] - particle['size']//2, particle['y'] - particle['size']//2))

    def update_spawn_effects(self, now_ms: int) -> None:
        """Update spawn particle effects and glow."""
        # Update dust alpha (fade out over spawn animation)
        if now_ms - self.born_at < self.SPAWN_ANIM_MS:
            # Calculate progress through spawn animation (0.0 to 1.0)
            progress = (now_ms - self.born_at) / self.SPAWN_ANIM_MS
            # Fade out dust and glow effects (alpha decreases as progress increases)
            self.spawn_dust_alpha = int(255 * (1 - progress))
            self.spawn_glow_alpha = int(255 * (1 - progress))
        
        # Update each spawn particle (use [:] to avoid modification during iteration)
        for particle in self.spawn_particles[:]:
            # Decrease particle lifetime
            particle['life'] -= 16  # 16ms per frame at 60fps
            
            # Remove dead particles from the list
            if particle['life'] <= 0:
                self.spawn_particles.remove(particle)
            else:
                # Move particles outward from spawn point
                particle['x'] += particle['dx']  # Update X position
                particle['y'] += particle['dy']  # Update Y position
                
                # Calculate alpha based on remaining lifetime (fade out effect)
                particle['alpha'] = int(255 * (particle['life'] / particle['max_life']))

    def create_spawn_particles(self) -> None:
        """Create particle effects for zombie spawning."""
        
        center_x, center_y = self.spawn.pos
        
        # Create 8 dust particles for spawn effect
        for _ in range(8):
            # Generate random direction (0 to 2π radians = full circle)
            angle = random.uniform(0, 2 * math.pi)
            # Random speed between 0.5-1.5 pixels per frame for gentle movement
            speed = random.uniform(0.5, 1.5)  # Reduced speed for better visibility
            
            # Calculate velocity components using trigonometry
            dx = math.cos(angle) * speed  # Horizontal velocity
            dy = math.sin(angle) * speed  # Vertical velocity
            
            # Create particle dictionary with all necessary properties
            particle = {
                'x': center_x,      # Starting X position (spawn center)
                'y': center_y,      # Starting Y position (spawn center)
                'dx': dx,           # Horizontal velocity per frame
                'dy': dy,           # Vertical velocity per frame
                'life': random.randint(60, 90),  # Random lifetime (60-90 frames)
                'max_life': 90,     # Maximum lifetime for alpha calculation
                'alpha': 255,       # Starting alpha (fully opaque)
                'size': random.randint(3, 5)  # Random particle size (3-5 pixels)
            }
            self.spawn_particles.append(particle)

    # ------------------------------- Rendering ---------------------------------------

    def get_vertical_offset(self, now_ms: int) -> int:
        """
        Positive values = zombie is below ground, 0 = fully emerged.
        Uses scaled sprite height so rise/sink matches visual size.
        """
        # Get current sprite height for proper scaling
        _, sprite_height = self._scaled_size(self.scale_factor)

        # Spawn animation: zombie rises up from underground
        t_spawn = now_ms - self.born_at
        if t_spawn < self.SPAWN_ANIM_MS:
            # Calculate progress through spawn animation (0.0 to 1.0)
            progress = t_spawn / self.SPAWN_ANIM_MS
            # Apply easing function for smooth rise (ease-out quadratic)
            eased_progress = 1 - (1 - progress) * (1 - progress)
            # Return offset (starts at full height, decreases to 0)
            return int(sprite_height * (1 - eased_progress))

        # Attack animation: zombie bounces up and down
        if self.attacking and self.attack_start is not None:
            # Calculate progress through attack animation
            t = (now_ms - self.attack_start) / ATTACK_ANIM_MS
            if t < 1.0:
                # Create bouncing effect using sine wave (6 cycles)
                bounce_offset = int(5 * math.sin(t * math.pi * 6))
                return -bounce_offset  # Negative = above normal position

        # Despawn animation: zombie sinks back underground
        if self.despawn_start is not None:
            # Calculate progress through despawn animation
            t = (now_ms - self.despawn_start) / self.DESPAWN_ANIM_MS
            if t < 1.0:
                # Apply easing function for smooth sink (ease-in quadratic)
                eased_progress = t * t
                return int(sprite_height * eased_progress)
            # Fully sunk - return full sprite height
            return sprite_height

        # Normal state - zombie is fully emerged
        return 0

    def get_current_sprite(self, now_ms: int) -> pygame.Surface | None:
        """Get the current sprite frame based on zombie state and animation timing."""
        if not self.sprites_loaded or not (self.normal_frames or self.attack_frames or self.death_frames):
            return None

        # Frame duration: each frame is displayed for 100ms
        frame_duration = 100
        # Calculate current animation frame based on time
        self.animation_frame = (now_ms // frame_duration) % max(1, len(self.normal_frames))

        # Priority order: death > attack > normal
        if self.hit and self.death_frames:
            # Zombie is hit - show death animation
            frame_idx = min(self.animation_frame, len(self.death_frames) - 1)
            return self.death_frames[frame_idx]
        if self.attacking and self.attack_frames:
            # Zombie is attacking - show attack animation
            frame_idx = min(self.animation_frame, len(self.attack_frames) - 1)
            return self.attack_frames[frame_idx]
        if self.normal_frames:
            # Normal state - show idle animation (cycles through frames)
            frame_idx = self.animation_frame % len(self.normal_frames)
            return self.normal_frames[frame_idx]
        return None

    def draw_timer_bar(self, surf: pygame.Surface, now_ms: int) -> None:
        """Draw a timer bar showing zombie's remaining lifetime."""
        if self.hit or self.attacking or self.dead:
            return

        # Calculate time remaining and progress
        elapsed = now_ms - self.born_at
        time_remaining = max(0, self.lifetime - elapsed)
        progress = time_remaining / self.lifetime

        # Set timer bar dimensions
        bar_width = self.spawn.radius * 2  # Width = 2x spawn radius
        bar_height = 4  # Fixed height
        center_x, center_y = self.spawn.pos
        bar_x = center_x - bar_width // 2  # Center horizontally
        bar_y = center_y - self.spawn.radius - 15  # Position above spawn point

        # Draw background bar (dark gray)
        pygame.draw.rect(surf, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))

        # Calculate filled width based on progress
        filled_width = int(bar_width * progress)
        
        # Choose color based on remaining time
        if progress > 0.6:
            color = (0, 255, 0)      # Green: >60% time remaining
        elif progress > 0.3:
            color = (255, 255, 0)    # Yellow: 30-60% time remaining
        else:
            color = (255, 0, 0)      # Red: <30% time remaining

        # Draw filled portion of the bar
        if filled_width > 0:
            pygame.draw.rect(surf, color, (bar_x, bar_y, filled_width, bar_height))

        # Draw border outline (light gray)
        pygame.draw.rect(surf, (200, 200, 200), (bar_x, bar_y, bar_width, bar_height), 1)

    ## DEBUG FUNCTION
    def draw_center_dot(self, surf: pygame.Surface, now_ms: int) -> None:
        """
        Draw a red dot at the center of the zombie sprite.
        """
        center = self.spawn.pos
        vertical_offset = self.get_vertical_offset(now_ms)
        dot_radius = 3
        pygame.draw.circle(surf, (255, 0, 0), (center[0], center[1] + vertical_offset), dot_radius)

    def draw(self, surf: pygame.Surface, now_ms: int) -> None:
        """
        Render using sprites with vertical offset for rise/fall animations.
        """
        center = self.spawn.pos
        vertical_offset = self.get_vertical_offset(now_ms)
        
        # Draw background effects first (behind zombie)
        self.draw_spawn_effects(surf)           # Dust particles and glow
        self.draw_hit_effects(surf)             # Explosion particles
        self.draw_timer_bar(surf, now_ms)       # Lifetime indicator
        # self.draw_center_dot(surf, now_ms)    # Debug center point

        # Get current sprite frame based on zombie state
        sprite = self.get_current_sprite(now_ms)
        if sprite and self.sprites_loaded:
            display_sprite = sprite
            
            # Apply hit flash effect if zombie was recently hit
            if self.hit and self.hit_time is not None and now_ms - self.hit_time < self.HIT_FLASH_MS:
                # Create a copy of the sprite for flash effect
                flash_sprite = sprite.copy()
                # Calculate flash alpha (fades out over time)
                flash_alpha = int(180 * (1.0 - (now_ms - self.hit_time) / self.HIT_FLASH_MS))
                # Create flash surface with the flash color
                flash_surface = pygame.Surface(flash_sprite.get_size(), pygame.SRCALPHA)
                flash_surface.fill((*FLASH_COLOR, flash_alpha))
                # Apply flash effect using additive blending
                flash_sprite.blit(flash_surface, (0, 0), special_flags=pygame.BLEND_ADD)
                display_sprite = flash_sprite

            # Position sprite with proper offsets
            sprite_rect = display_sprite.get_rect()
            sprite_rect.centerx = center[0] + self.ANCHOR_OFFSET_X                      # Horizontal positioning
            sprite_rect.centery = center[1] + vertical_offset + self.ANCHOR_OFFSET_Y    # Vertical positioning
            
            # Draw the final sprite to the surface
            surf.blit(display_sprite, sprite_rect)
            return

    def get_hitbox_rect(self, now_ms: int) -> pygame.Rect:
        """
        Calculate the zombie's hitbox rectangle based on current position and sprite size.
        Uses the exact same positioning logic as sprite drawing for consistency.
        """
        center = self.spawn.pos
        vertical_offset = self.get_vertical_offset(now_ms)
        sprite_width, sprite_height = self._scaled_size()
        
        # Create hitbox that's smaller than the sprite (50% width, 90% height)
        hitbox_rect = pygame.Rect(0, 0, int(sprite_width * 0.5), int(sprite_height * 0.9))
        
        # Center the hitbox horizontally and position it with vertical offset
        hitbox_rect.centerx = center[0]
        hitbox_rect.centery = center[1] + vertical_offset
        return hitbox_rect

    def contains_point(self, point: tuple[int, int], now_ms: int) -> bool:
        """
        Rectangle-based hit test for zombie sprites. Only allow hits when zombie is not attacking.
        """
        # Zombies cannot be hit while attacking
        if self.attacking:
            return False
        # Get current hitbox and test collision
        hitbox_rect = self.get_hitbox_rect(now_ms)
        return hitbox_rect.collidepoint(point)
    
    def draw_hitbox(self, surf: pygame.Surface, now_ms: int) -> None:
        """
        Draw the zombie's hitbox as a colored rectangle outline for debugging.
        """
        hitbox_rect = self.get_hitbox_rect(now_ms)
        
        # Choose color based on zombie state
        if self.attacking:
            color = (255, 0, 0)      # Red when attacking (not hittable)
        elif self.hit:
            color = (128, 128, 128)  # Gray when hit
        else:
            color = (0, 255, 0)      # Green when hittable
            
        # Draw hitbox outline with 2-pixel thickness
        pygame.draw.rect(surf, color, hitbox_rect, 2)
