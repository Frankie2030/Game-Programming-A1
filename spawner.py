from __future__ import annotations

import random

from constants import (
    SPAWN_INTERVAL_MS, LEVEL_SPAWN_DECREASE, MIN_SPAWN_INTERVAL, MAX_LIFETIME_MS, LEVEL_LIFETIME_DECREASE,
    BRAIN_SPAWN_CHECK_INTERVAL_MS, BRAIN_SPAWN_PROBABILITY
)
from models import SpawnPoint
from zombie import Zombie
from brain import Brain


class Spawner:
    """
    Responsible for spawning new zombies at randomized intervals and locations.
    Supports level-based difficulty scaling.

    Notes
    - Spawn timing uses wall-clock ms to be independent of frame rate.
    - Difficulty increases with level: faster spawning and shorter lifetimes.
    """

    def __init__(self, spawn_points: list[SpawnPoint]) -> None:
        self.spawn_points = spawn_points
        self.next_spawn_at = 0  # ms timestamp for next spawn
        self.next_brain_check_at = 0  # ms timestamp for next brain spawn check

    def get_spawn_interval(self, level: int) -> int:
        """
        Calculate spawn interval (milliseconds) based on level.
        """
        return max(MIN_SPAWN_INTERVAL, SPAWN_INTERVAL_MS - (level - 1) * LEVEL_SPAWN_DECREASE)

    def schedule_next(self, now_ms: int, level: int) -> None:
        """
        Pick the next spawn time based on level-adjusted cadence with jitter.
        """
        base_interval = self.get_spawn_interval(level)
        jitter = random.randint(-150, 220)  # add variability to cadence
        self.next_spawn_at = now_ms + max(200, base_interval + jitter)

    def get_available_spawn_points(self, zombies: list[Zombie], brains: list[Brain] | None = None) -> list[SpawnPoint]:
        """
        Get spawn points that don't currently have active zombies or brains.
        
        Parameters
        ----------
        zombies : list[Zombie]
            Current list of active zombies
        brains : list[Brain] | None
            Current list of active brains (optional)
            
        Returns
        -------
        list[SpawnPoint]
            List of spawn points without active entities
        """
        occupied_spawn_points = {zombie.spawn for zombie in zombies if zombie.is_active(0)}
        
        if brains:
            brain_spawn_points = {brain.spawn for brain in brains if brain.is_active(0)}
            occupied_spawn_points.update(brain_spawn_points)
        
        return [sp for sp in self.spawn_points if sp not in occupied_spawn_points]

    def maybe_spawn(self, now_ms: int, zombies: list[Zombie], level: int, brains: list[Brain] | None = None) -> None:
        """
        Spawn a zombie if timing is due and there are available spawn points.
        
        Parameters
        ----------
        now_ms : int
            Current time in milliseconds
        zombies : list[Zombie]
            Current list of active zombies
        level : int
            Current game level
        brains : list[Brain] | None
            Current list of active brains (optional)
        """
        # Set initial schedule on first call
        if self.next_spawn_at == 0:
            self.schedule_next(now_ms, level)

        if now_ms >= self.next_spawn_at:
            available_spawns = self.get_available_spawn_points(zombies, brains)
            
            # Only spawn if there are available spawn points
            if available_spawns:
                spawn = random.choice(available_spawns)
                lifetime = MAX_LIFETIME_MS - (level - 1) * LEVEL_LIFETIME_DECREASE
                zombies.append(Zombie(spawn, born_at_ms=now_ms, lifetime_ms=lifetime))
            
            # Always schedule next spawn, even if we couldn't spawn this time
            self.schedule_next(now_ms, level)
    
    def maybe_spawn_brain(self, now_ms: int, zombies: list[Zombie], brains: list[Brain]) -> None:
        """
        Check if it's time to potentially spawn a brain pickup.
        
        Parameters
        ----------
        now_ms : int
            Current time in milliseconds
        zombies : list[Zombie]
            Current list of active zombies
        brains : list[Brain]
            Current list of active brains
        """
        # Set initial schedule on first call
        if self.next_brain_check_at == 0:
            self.next_brain_check_at = now_ms + BRAIN_SPAWN_CHECK_INTERVAL_MS
        
        if now_ms >= self.next_brain_check_at:
            # Check probability
            if random.random() < BRAIN_SPAWN_PROBABILITY:
                available_spawns = self.get_available_spawn_points(zombies, brains)
                
                # Only spawn brain if there are available spawn points
                if available_spawns:
                    spawn = random.choice(available_spawns)
                    brains.append(Brain(spawn, born_at_ms=now_ms))
                    print(f"Brain spawned at {spawn.pos}!")  # Debug message
            
            # Schedule next brain check
            self.next_brain_check_at = now_ms + BRAIN_SPAWN_CHECK_INTERVAL_MS
