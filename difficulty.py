from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Difficulty:
    name: str
    min_size: int
    max_size: int
    door_count_min: int
    door_count_max: int
    tightness_weights: tuple[int, ...]
    shortcut_gap_threshold: int
    section_gate_min: int
    section_gate_max: int
    blocking_monster_min: int
    blocking_monster_max: int
    optional_monster_min: int
    optional_monster_max: int
    trap_min: int
    trap_max: int
    treasure_min: int
    treasure_max: int
    key_distribution_seconds: float
    fight_steps: int
    trap_step_penalty: int
    treasure_bonus_points: int


EASY = Difficulty(
    name="easy",
    min_size=16,
    max_size=20,
    door_count_min=1,
    door_count_max=3,
    tightness_weights=(1, 1, 2, 2, 3),
    shortcut_gap_threshold=14,
    section_gate_min=0,
    section_gate_max=1,
    blocking_monster_min=0,
    blocking_monster_max=1,
    optional_monster_min=1,
    optional_monster_max=2,
    trap_min=1,
    trap_max=3,
    treasure_min=1,
    treasure_max=2,
    key_distribution_seconds=8,
    fight_steps=3,
    trap_step_penalty=2,
    treasure_bonus_points=10,
)

MEDIUM = Difficulty(
    name="medium",
    min_size=18,
    max_size=24,
    door_count_min=2,
    door_count_max=5,
    tightness_weights=(1, 2, 2, 3, 7),
    shortcut_gap_threshold=10,
    section_gate_min=1,
    section_gate_max=2,
    blocking_monster_min=1,
    blocking_monster_max=2,
    optional_monster_min=2,
    optional_monster_max=4,
    trap_min=2,
    trap_max=5,
    treasure_min=2,
    treasure_max=4,
    key_distribution_seconds=10,
    fight_steps=5,
    trap_step_penalty=3,
    treasure_bonus_points=15,
)

HARD = Difficulty(
    name="hard",
    min_size=24,
    max_size=28,
    door_count_min=5,
    door_count_max=8,
    tightness_weights=(2, 3, 3, 7, 7),
    shortcut_gap_threshold=8,
    section_gate_min=2,
    section_gate_max=4,
    blocking_monster_min=2,
    blocking_monster_max=4,
    optional_monster_min=4,
    optional_monster_max=6,
    trap_min=4,
    trap_max=8,
    treasure_min=3,
    treasure_max=6,
    key_distribution_seconds=15,
    fight_steps=7,
    trap_step_penalty=4,
    treasure_bonus_points=20,
)

DIFFICULTY_PRESETS = (EASY, MEDIUM, HARD)


def difficulty_for_seed(rng: random.Random) -> Difficulty:
    return DIFFICULTY_PRESETS[rng.randint(0, len(DIFFICULTY_PRESETS) - 1)]
