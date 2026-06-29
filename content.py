from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DoorKind(str, Enum):
    SHORTCUT = "shortcut"
    SECTION_GATE = "section_gate"


DIR_NAMES = ("up", "right", "down", "left")


@dataclass
class Monster:
    index: int
    blocking: bool
    fight_steps: int


@dataclass
class Trap:
    index: int
    step_penalty: int
    one_shot: bool = True


@dataclass
class Treasure:
    index: int
    bonus_points: int
