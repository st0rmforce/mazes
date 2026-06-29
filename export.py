from __future__ import annotations

import json
from typing import TYPE_CHECKING

from content import DIR_NAMES, DoorKind, Monster, Trap, Treasure

if TYPE_CHECKING:
    from maze import Maze, Square


def _walls_for_square(sq: Square) -> list[str]:
    walls = []
    for direction in range(4):
        if sq.blocked[direction] and sq.doors[direction] == -1:
            walls.append(DIR_NAMES[direction])
    return walls


def _door_for_square(sq: Square) -> dict | None:
    for direction in range(4):
        if sq.doors[direction] >= 0:
            other = sq.directions[direction]
            if other is None:
                continue
            entry = sq.maze.door_entry_for(sq, direction)
            if entry:
                return {
                    "index": sq.doors[direction],
                    "kind": entry["kind"].value,
                    "direction": DIR_NAMES[direction],
                    "to": [other.x, other.y],
                }
    return None


def _monster_dict(sq: Square) -> dict | None:
    if sq.monster is None:
        return None
    return {
        "index": sq.monster.index,
        "blocking": sq.monster.blocking,
        "fight_steps": sq.monster.fight_steps,
    }


def _trap_dict(sq: Square) -> dict | None:
    if sq.trap is None:
        return None
    return {
        "index": sq.trap.index,
        "step_penalty": sq.trap.step_penalty,
        "one_shot": sq.trap.one_shot,
    }


def _treasure_dict(sq: Square) -> dict | None:
    if sq.treasure is None:
        return None
    return {
        "index": sq.treasure.index,
        "bonus_points": sq.treasure.bonus_points,
    }


def maze_to_dict(maze: Maze) -> dict:
    cells = []
    for sq in maze.all_squares:
        cells.append(
            {
                "x": sq.x,
                "y": sq.y,
                "walls": _walls_for_square(sq),
                "door": _door_for_square(sq),
                "trap": _trap_dict(sq),
                "treasure": _treasure_dict(sq),
                "monster": _monster_dict(sq),
            }
        )

    keys = [
        {"index": index, "x": sq.x, "y": sq.y}
        for index, sq in enumerate(maze.key_locations)
    ]

    doors = []
    seen: set[tuple[int, int, int, int]] = set()
    for entry in maze.door_entries:
        sq = entry["square"]
        direction = entry["direction"]
        other = sq.directions[direction]
        if other is None:
            continue
        pair = tuple(sorted([(sq.x, sq.y), (other.x, other.y)]) + [direction])
        if pair in seen:
            continue
        seen.add(pair)
        doors.append(
            {
                "index": entry["key_index"],
                "kind": entry["kind"].value,
                "from": [sq.x, sq.y],
                "to": [other.x, other.y],
                "direction": DIR_NAMES[direction],
            }
        )

    side_content = []
    for sq in maze.all_squares:
        if sq.monster and not sq.monster.blocking:
            side_content.append(
                {
                    "type": "monster",
                    "x": sq.x,
                    "y": sq.y,
                    "index": sq.monster.index,
                    "fight_steps": sq.monster.fight_steps,
                }
            )
        if sq.treasure:
            side_content.append(
                {
                    "type": "treasure",
                    "x": sq.x,
                    "y": sq.y,
                    "index": sq.treasure.index,
                    "bonus_points": sq.treasure.bonus_points,
                }
            )

    return {
        "seed": maze.seed,
        "difficulty": maze.difficulty.name,
        "width": maze.width,
        "height": maze.height,
        "entrance": [maze.entrance.x, maze.entrance.y],
        "exit": [maze.exit.x, maze.exit.y],
        "cells": cells,
        "keys": keys,
        "doors": doors,
        "metadata": {
            "optimal_steps": getattr(maze, "optimal_steps", None),
            "baseline_steps": getattr(maze, "baseline_steps", None),
            "best_keysets": [list(ks) for ks in getattr(maze, "best_keysets", [])],
            "section_gate_count": maze.section_gate_count,
            "shortcut_door_count": maze.shortcut_door_count,
            "treasure_count": sum(1 for sq in maze.all_squares if sq.treasure),
            "optional_monster_count": sum(
                1 for sq in maze.all_squares if sq.monster and not sq.monster.blocking
            ),
            "blocking_monster_count": sum(
                1 for sq in maze.all_squares if sq.monster and sq.monster.blocking
            ),
            "trap_count": sum(1 for sq in maze.all_squares if sq.trap),
            "side_content": side_content,
        },
    }


def maze_to_json(maze: Maze, indent: int = 2) -> str:
    return json.dumps(maze_to_dict(maze), indent=indent)
