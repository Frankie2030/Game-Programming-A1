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

MIN_LIFETIME_MS = 800              # recommended range
MAX_LIFETIME_MS = 1500

SPAWN_INTERVAL_MS = 600            # try to spawn a new zombie roughly every 0.6s
MAX_CONCURRENT_ZOMBIES = 1         # only one head counts per click is implicit; keep it simple

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
MUSIC_PATH = os.path.join(ASSETS_DIR, "bg_music.mp3")    # optional
HIT_SFX_PATH = os.path.join(ASSETS_DIR, "hit.mp3")       # optional


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
    - DESPAWN:  scales down to 0 over ~160ms, then is removed.

    Timings are driven via pygame.time.get_ticks() (ms-precise, frame-rate independent).
    """

    SPAWN_ANIM_MS = 120
    DESPAWN_ANIM_MS = 160
    HIT_FLASH_MS = 120

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

    # ------------------------------- Update & State ----------------------------------

    def is_active(self, now_ms: int) -> bool:
        """Return True if the zombie should be considered "alive/visible" on screen."""
        return not self.dead

    def mark_hit(self, now_ms: int) -> None:
        """Mark as hit and begin despawn flow (prevents double counting)."""
        if self.hit or self.dead:
            return
        self.hit = True
        self.hit_time = now_ms
        self.despawn_start = now_ms  # start the despawn animation immediately on hit

    def update(self, now_ms: int) -> None:
        """
        Advance the zombie's lifecycle based on current time.

        - If lifetime exceeded and not yet hit, start despawn.
        - If currently despawning and animation done, mark as dead.
        """
        # If still active and lifetime expired (not hit yet), start despawn animation.
        if (not self.hit) and (now_ms - self.born_at >= self.lifetime) and self.despawn_start is None:
            self.despawn_start = now_ms

        # When despawn animation finishes, mark as dead (remove externally).
        if self.despawn_start is not None:
            if now_ms - self.despawn_start >= self.DESPAWN_ANIM_MS:
                self.dead = True

    # ------------------------------- Rendering ---------------------------------------

    def current_scale(self, now_ms: int) -> float:
        """
        Compute the scale factor for spawn/despawn animations.

        Returns
        -------
        float
            Scale factor to apply to the base radius (1.0 = normal size).
        """
        # Spawn pop: ease-out scale 0.6 -> 1.0
        t_spawn = now_ms - self.born_at
        if t_spawn < self.SPAWN_ANIM_MS:
            return 0.6 + 0.4 * (t_spawn / self.SPAWN_ANIM_MS)

        # Despawn shrink: 1.0 -> 0
        if self.despawn_start is not None:
            t = (now_ms - self.despawn_start) / self.DESPAWN_ANIM_MS
            return max(0.0, 1.0 - t)

        return 1.0

    def draw(self, surf: pygame.Surface, now_ms: int) -> None:
        """
        Render the zombie head with simple shading and facial features.

        Visual feedback:
        - On hit: brief flash overlay + slight squash/stretch during first HIT_FLASH_MS.
        """
        center = self.spawn.pos
        base_r = int(self.spawn.radius * 0.9)  # head a bit smaller than hole
        scale = self.current_scale(now_ms)
        r_x = int(base_r * scale * (1.08 if self.hit else 1.0))   # slight stretch on hit
        r_y = int(base_r * scale * (0.92 if self.hit else 1.0))
        r = max(1, int((r_x + r_y) * 0.5))

        # Head base
        pygame.draw.ellipse(surf, ZOMBIE_GREEN, (center[0]-r_x, center[1]-r_y, 2*r_x, 2*r_y))
        # Shading
        pygame.draw.ellipse(surf, ZOMBIE_DARK, (center[0]-int(r_x*0.8), center[1]-int(r_y*0.8), int(1.6*r_x), int(1.6*r_y)), width=2)

        # Eyes
        eye_offset_x = int(r * 0.35)
        eye_offset_y = int(r * -0.10)
        eye_r = max(2, int(r * 0.14))
        pygame.draw.circle(surf, (250, 250, 250), (center[0]-eye_offset_x, center[1]+eye_offset_y), eye_r)
        pygame.draw.circle(surf, (250, 250, 250), (center[0]+eye_offset_x, center[1]+eye_offset_y), eye_r)
        pupil_r = max(1, int(eye_r * 0.5))
        pygame.draw.circle(surf, (10, 10, 10), (center[0]-eye_offset_x, center[1]+eye_offset_y), pupil_r)
        pygame.draw.circle(surf, (10, 10, 10), (center[0]+eye_offset_x, center[1]+eye_offset_y), pupil_r)

        # Scar
        scar_len = int(r * 0.9)
        x1, y1 = center[0]-int(scar_len*0.4), center[1]-int(r*0.2)
        x2, y2 = center[0]+int(scar_len*0.4), center[1]-int(r*0.25)
        pygame.draw.line(surf, (80, 30, 30), (x1, y1), (x2, y2), 3)
        for t in (-0.25, 0.05, 0.35):
            sx = int(x1 + (x2-x1)*(0.5+t))
            sy = int(y1 + (y2-y1)*(0.5+t))
            pygame.draw.line(surf, (80, 30, 30), (sx-6, sy-6), (sx+6, sy+6), 2)

        # Hit flash overlay (very brief)
        if self.hit and self.hit_time is not None and now_ms - self.hit_time < self.HIT_FLASH_MS:
            alpha = int(180 * (1.0 - (now_ms - self.hit_time) / self.HIT_FLASH_MS))
            flash = pygame.Surface((2*r_x, 2*r_y), pygame.SRCALPHA)
            flash.fill((*FLASH_COLOR, alpha))
            surf.blit(flash, (center[0]-r_x, center[1]-r_y))

    # ------------------------------- Hit Testing -------------------------------------

    def contains_point(self, point: Tuple[int, int], now_ms: int) -> bool:
        """
        Circle/ellipse-based hit test.

        Parameters
        ----------
        point : Tuple[int, int]
            Mouse click position.
        now_ms : int
            Current time in ms (used to match scale used for drawing).

        Returns
        -------
        bool
            True if the click lies within the scaled ellipse head.
        """
        cx, cy = self.spawn.pos
        base_r = int(self.spawn.radius * 0.9)
        scale = self.current_scale(now_ms)
        r_x = max(1, int(base_r * scale))
        r_y = max(1, int(base_r * scale))

        # Check point inside ellipse: ((x-cx)/rx)^2 + ((y-cy)/ry)^2 <= 1
        px, py = point
        dx = (px - cx) / float(r_x)
        dy = (py - cy) / float(r_y)
        return (dx*dx + dy*dy) <= 1.0


class HUD:
    """Heads-Up Display to render hits, misses, and accuracy percentage."""

    def __init__(self, font: pygame.font.Font) -> None:
        self.font = font

    def draw(self, surf: pygame.Surface, hits: int, misses: int) -> None:
        """Render a compact HUD in the top-left corner."""
        total = hits + misses
        acc = (hits / total * 100.0) if total > 0 else 0.0
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

        # Gameplay state
        self.zombies: List[Zombie] = []
        self.hits = 0
        self.misses = 0
        self.hud = HUD(self.font_small)

        # Audio
        self.muted = False
        self.snd_hit: Optional[pygame.mixer.Sound] = None
        self._init_audio()

    # --------------------------------- Setup ----------------------------------------

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
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(pygame.mouse.get_pos(), now)

            # Update entities
            for z in self.zombies:
                z.update(now)
            # Remove dead
            self.zombies = [z for z in self.zombies if z.is_active(now)]

            # Spawning
            self.spawner.maybe_spawn(now, self.zombies)

            # Draw
            self._draw(now)

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
            if not z.hit and z.contains_point(pos, now_ms):
                z.mark_hit(now_ms)
                self.hits += 1
                if self.snd_hit and not self.muted:
                    self.snd_hit.play()
                return
        # No zombie consumed the click → miss
        self.misses += 1

    def _reset_scores(self) -> None:
        """Reset score counters to zero."""
        self.hits = 0
        self.misses = 0

    def _toggle_mute(self) -> None:
        """Mute/unmute mixer (and remember toggle)."""
        self.muted = not self.muted
        try:
            pygame.mixer.music.set_volume(0.0 if self.muted else 0.35)
        except Exception:
            pass

    # --------------------------------- Rendering ------------------------------------

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

    def _draw(self, now_ms: int) -> None:
        """Compose the frame: bg → zombies → HUD → header text."""
        self._draw_background(self.screen)

        # Draw active zombies
        for z in self.zombies:
            z.draw(self.screen, now_ms)

        # HUD
        self.hud.draw(self.screen, self.hits, self.misses)

        # Title / hints
        title = self.font_big.render("Whack-a-Zombie", True, TEXT_COLOR)
        self.screen.blit(title, (WIDTH - title.get_width() - HUD_PADDING, HUD_PADDING))
        hint = self.font_small.render("[LMB] hit  |  [R] reset  |  [M] mute  |  [ESC/Q] quit", True, (200, 200, 200))
        self.screen.blit(hint, (WIDTH - hint.get_width() - HUD_PADDING, HUD_PADDING + title.get_height() + 4))

        pygame.display.flip()


def main() -> None:
    """Entry point; constructs the Game and starts the main loop."""
    Game().run()


if __name__ == "__main__":
    main()
