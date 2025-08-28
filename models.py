"""Lightweight data models used across the game."""

from dataclasses import dataclass

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
    pos: tuple[int, int]
    radius: int

