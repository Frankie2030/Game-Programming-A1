"""UI components: HUD and Game Over screen for Whack-a-Zombie.

Provides readouts for level progression, lives, hits, misses, accuracy, FPS,
and pause/mute indicators. Uses right/left HUD layout to avoid the play area.
"""

import pygame
import os

from constants import (
    WIDTH, HEIGHT, HUD_PADDING, TEXT_COLOR, 
    MAX_LEVEL, ZOMBIES_PER_LEVEL, FONT_NAME,
    FONT_SIZE_SMALL, BRAIN_PATH
)

class HUD:
    """Heads-Up Display with left/right split layout."""

    def __init__(self, font: pygame.font.Font) -> None:
        self.font = font
        self.small_font = pygame.font.Font(FONT_NAME, FONT_SIZE_SMALL)
        self.brain_icon = self.load_brain_icon()
        self._debug_hud = False  # Debug mode for HUD positioning
    
    def update_fonts(self, new_font: pygame.font.Font) -> None:
        """Update fonts for responsive scaling."""
        self.font = new_font
        
    def update_brain_icon_scaling(self, scale_factor: float) -> None:
        """Update brain icon size for responsive scaling."""
        if hasattr(self, 'original_brain_icon') and self.original_brain_icon:
            # Calculate new size based on scale factor
            base_size = 20
            new_size = max(16, int(base_size * scale_factor))
            self.brain_icon = pygame.transform.scale(self.original_brain_icon, (new_size, new_size))
    
    def toggle_debug(self) -> None:
        """Toggle debug mode for HUD positioning."""
        self._debug_hud = not self._debug_hud
        print(f"HUD Debug mode: {'ON' if self._debug_hud else 'OFF'}")
        
    def load_brain_icon(self) -> pygame.Surface | None:
        """Load brain icon for lives display."""
        if os.path.exists(BRAIN_PATH):
            try:
                brain_img = pygame.image.load(BRAIN_PATH).convert_alpha()
                # Store original for responsive scaling
                self.original_brain_icon = brain_img
                # Scale to small icon size (20x20)
                return pygame.transform.scale(brain_img, (20, 20))
            except Exception as e:
                print(f"Failed to load brain icon: {e}")
        return None

    def draw(self, surf: pygame.Surface, hits: int, misses: int, lives: int, 
             level: int, show_fps: bool = False, fps: float = 0.0, 
             paused: bool = False, muted: bool = False) -> None:
        """Render a comprehensive HUD with left/right split layout."""
        total = hits + misses
        acc = (hits / total * 100.0) if total > 0 else 0.0
        
        # Get current surface dimensions for responsive positioning
        current_width = surf.get_width()
        current_height = surf.get_height()
        
        # LEFT SIDE: Level and Lives - Responsive positioning
        # Scale padding based on window size
        responsive_padding = max(8, int(HUD_PADDING * (min(current_width, current_height) / 540)))
        left_x = responsive_padding
        left_y = responsive_padding

        level_text = self.font.render(f"Level: {level}", True, TEXT_COLOR)
        surf.blit(level_text, (left_x, left_y))
        left_y += level_text.get_height() + 4
        
        if level < MAX_LEVEL:
            zombies_in_level = hits % ZOMBIES_PER_LEVEL
            progress_text = f"Progress: {zombies_in_level}/{ZOMBIES_PER_LEVEL}"
            progress_surf = self.small_font.render(progress_text, True, TEXT_COLOR)
            surf.blit(progress_surf, (left_x, left_y))
            left_y += progress_surf.get_height() + 8
        else:
            max_level_text = self.font.render("MAXED", True, (255, 215, 0))
            surf.blit(max_level_text, (left_x, left_y))
            left_y += max_level_text.get_height() + 8
        
        # Lives display with brain icon format
        if self.brain_icon:
            # Draw brain icon and text in format: <brain_png>: X
            surf.blit(self.brain_icon, (left_x, left_y))
            # Responsive offset based on icon size
            icon_offset = self.brain_icon.get_width() + 5
            lives_text = self.font.render(f": {lives}", True, TEXT_COLOR)
            surf.blit(lives_text, (left_x + icon_offset, left_y))
        else:
            # Fallback to text only format
            lives_text = self.font.render(f"Lives: {lives}", True, TEXT_COLOR)
            surf.blit(lives_text, (left_x, left_y))
        
        # RIGHT SIDE: Stats and optional indicators - Responsive positioning
        # Calculate right side position based on content width and window size
        stats_width = 0
        temp_stats = [
            f"Hits: {hits}",
            f"Misses: {misses}",
            f"Accuracy: {acc:.1f}%",
            f"Zombies Killed: {zombies_killed}"
        ]
        
        # Find the widest stat line to calculate proper positioning
        for line in temp_stats:
            text_surf = self.font.render(line, True, TEXT_COLOR)
            stats_width = max(stats_width, text_surf.get_width())
        
        # Position right side with proper spacing
        right_x = current_width - stats_width - responsive_padding
        right_y = responsive_padding
        
        # Debug: Print HUD positioning info (can be removed in production)
        if hasattr(self, '_debug_hud') and self._debug_hud:
            print(f"HUD Debug - Window: {current_width}x{current_height}, Padding: {responsive_padding}")
            print(f"  Left: ({left_x}, {left_y}), Right: ({right_x}, {right_y})")
            print(f"  Stats width: {stats_width}")
        
        # Stats
        right_stats = [
            f"Hits: {hits}",
            f"Misses: {misses}",
            f"Accuracy: {acc:.1f}%",
            # f"Zombies Killed: {zombies_killed}"
        ]
        
        for line in right_stats:
            text_surf = self.font.render(line, True, TEXT_COLOR)
            surf.blit(text_surf, (right_x, right_y))
            right_y += text_surf.get_height() + 4
        
        if show_fps:
            right_y += 4  # Extra spacing
            fps_color = (0, 255, 0) if fps >= 55 else (255, 255, 0) if fps >= 30 else (255, 0, 0)
            fps_text = self.small_font.render(f"FPS: {fps:.1f}", True, fps_color)
            surf.blit(fps_text, (right_x, right_y))
            right_y += fps_text.get_height() + 4
        
        if muted:
            right_y += 4  # Extra spacing  
            muted_text = self.small_font.render("MUTED", True, (255, 150, 150))
            surf.blit(muted_text, (right_x, right_y))

        if paused:
            pause_text = self.font.render("PAUSED", True, (255, 255, 100))
            # Responsive positioning - scale based on window height
            pause_y = max(80, int(current_height * 0.15))  # 15% from top, minimum 80px
            text_rect = pause_text.get_rect(center=(current_width//2, pause_y))
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
    
    def update_fonts(self, new_font_big: pygame.font.Font, new_font_small: pygame.font.Font) -> None:
        """Update fonts for responsive scaling."""
        self.font_big = new_font_big
        self.font_small = new_font_small
        
    def draw(self, surf: pygame.Surface, hits: int, misses: int) -> bool:
        """
        Draw game over screen.
        
        Returns True if restart button is hovered, False otherwise.
        """
        # Get current surface dimensions for responsive positioning
        current_width = surf.get_width()
        current_height = surf.get_height()
        
        # Semi-transparent overlay
        overlay = pygame.Surface((current_width, current_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0, 0))
        
        # Game Over title - Responsive positioning
        game_over_text = self.font_big.render("GAME OVER", True, (255, 100, 100))
        title_y = max(80, int(current_height * 0.25))  # 25% from top, minimum 80px
        game_over_rect = game_over_text.get_rect(center=(current_width//2, title_y))
        surf.blit(game_over_text, game_over_rect)
        
        # Final stats - Responsive positioning
        total = hits + misses
        acc = (hits / total * 100.0) if total > 0 else 0.0
        score = max(0, hits - misses)
        
        stats_lines = [
            f"Final Score: {score}",
            f"Hits: {hits}",
            f"Misses: {misses}", 
            f"Accuracy: {acc:.1f}%"
        ]
        
        # Calculate stats position based on window height
        stats_start_y = max(title_y + 80, int(current_height * 0.4))  # 40% from top or below title
        y_offset = stats_start_y
        for line in stats_lines:
            text_surf = self.font_small.render(line, True, TEXT_COLOR)
            text_rect = text_surf.get_rect(center=(current_width // 2, y_offset))
            surf.blit(text_surf, text_rect)
            y_offset += 30
            
        # Restart button - Responsive positioning
        mouse_x, mouse_y = pygame.mouse.get_pos()
        button_width = min(200, int(current_width * 0.3))  # 30% of window width, max 200px
        button_height = min(50, int(current_height * 0.08))  # 8% of window height, max 50px
        button_x = current_width // 2 - button_width // 2
        button_y = max(y_offset + 30, int(current_height * 0.65))  # Below stats or 65% from top
        
        button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        button_hovered = button_rect.collidepoint(mouse_x, mouse_y)
        
        button_color = (100, 150, 100) if button_hovered else (80, 80, 80)
        pygame.draw.rect(surf, button_color, button_rect)
        pygame.draw.rect(surf, TEXT_COLOR, button_rect, 2)
        
        restart_text = self.font_small.render("Click to Restart", True, TEXT_COLOR)
        restart_rect = restart_text.get_rect(center=button_rect.center)
        surf.blit(restart_text, restart_rect)
        
        # Instructions - Responsive positioning
        inst_text = self.font_small.render("Press R to restart or ESC to quit", True, (150, 150, 150))
        inst_y = max(button_y + button_height + 20, int(current_height * 0.8))  # Below button or 80% from top
        inst_rect = inst_text.get_rect(center=(current_width // 2, inst_y))
        surf.blit(inst_text, inst_rect)
        
        return button_hovered
