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
        
    def load_brain_icon(self) -> pygame.Surface | None:
        """Load brain icon for lives display."""
        if os.path.exists(BRAIN_PATH):
            try:
                brain_img = pygame.image.load(BRAIN_PATH).convert_alpha()
                # Scale to small icon size (20x20)
                return pygame.transform.scale(brain_img, (20, 20))
            except Exception as e:
                print(f"Failed to load brain icon: {e}")
        return None

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
             level: int, zombies_killed: int, show_fps: bool = False, fps: float = 0.0, 
             paused: bool = False, muted: bool = False) -> None:
        """Render a comprehensive HUD with left/right split layout."""
        total = hits + misses
        acc = (hits / total * 100.0) if total > 0 else 0.0
        
        # LEFT SIDE: Level and Lives
        left_x, left_y = HUD_PADDING, HUD_PADDING

        level_text = self.font.render(f"Level: {level}", True, TEXT_COLOR)
        surf.blit(level_text, (left_x, left_y))
        left_y += level_text.get_height() + 4
        
        if level < MAX_LEVEL:
            zombies_in_level = zombies_killed % ZOMBIES_PER_LEVEL
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
            lives_text = self.font.render(f": {lives}", True, TEXT_COLOR)
            surf.blit(lives_text, (left_x + 25, left_y))
        else:
            # Fallback to text only format
            lives_text = self.font.render(f"Lives: {lives}", True, TEXT_COLOR)
            surf.blit(lives_text, (left_x, left_y))
        
        # RIGHT SIDE: Stats and optional indicators
        right_x = WIDTH - 150  # Fixed distance from right edge
        right_y = HUD_PADDING
        
        # Stats
        right_stats = [
            f"Hits: {hits}",
            f"Misses: {misses}",
            f"Accuracy: {acc:.1f}%",
            f"Zombies Killed: {zombies_killed}"
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
        
        y_offset = HEIGHT // 2 - 30
        for line in stats_lines:
            text_surf = self.font_small.render(line, True, TEXT_COLOR)
            text_rect = text_surf.get_rect(center=(WIDTH // 2, y_offset))
            surf.blit(text_surf, text_rect)
            y_offset += 30
            
        # Restart button
        mouse_x, mouse_y = pygame.mouse.get_pos()
        button_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 80, 200, 50)
        button_hovered = button_rect.collidepoint(mouse_x, mouse_y)
        
        button_color = (100, 150, 100) if button_hovered else (80, 80, 80)
        pygame.draw.rect(surf, button_color, button_rect)
        pygame.draw.rect(surf, TEXT_COLOR, button_rect, 2)
        
        restart_text = self.font_small.render("Click to Restart", True, TEXT_COLOR)
        restart_rect = restart_text.get_rect(center=button_rect.center)
        surf.blit(restart_text, restart_rect)
        
        # Instructions
        inst_text = self.font_small.render("Press R to restart or ESC to quit", True, (150, 150, 150))
        inst_rect = inst_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 150))
        surf.blit(inst_text, inst_rect)
        
        return button_hovered
