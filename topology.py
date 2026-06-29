from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from maze import Maze, Square


def _neighbors(maze: Maze, sq: Square) -> list[tuple[Square, int]]:
    result = []
    for direction in range(4):
        other = sq.directions[direction]
        if other and not sq.blocked[direction] and sq.doors[direction] == -1:
            result.append((other, direction))
    return result


def find_bridges(maze: Maze) -> list[tuple[Square, int, int]]:
    """Return bridge edges as (square, direction, side_size) sorted by side_size desc."""
    index: dict[Square, int] = {}
    low: dict[Square, int] = {}
    disc: dict[Square, int] = {}
    parent: dict[Square, Square | None] = {}
    bridges: list[tuple[Square, int]] = []
    timer = [0]

    def dfs(sq: Square) -> None:
        disc[sq] = low[sq] = timer[0]
        timer[0] += 1
        for neighbor, direction in _neighbors(maze, sq):
            if neighbor not in disc:
                parent[neighbor] = sq
                dfs(neighbor)
                low[sq] = min(low[sq], low[neighbor])
                if low[neighbor] > disc[sq]:
                    bridges.append((sq, direction))
            elif neighbor != parent.get(sq):
                low[sq] = min(low[sq], disc[neighbor])

    for sq in maze.all_squares:
        if sq not in disc:
            parent[sq] = None
            dfs(sq)

    scored: list[tuple[Square, int, int]] = []
    for sq, direction in bridges:
        side_size = _component_size(maze, sq.directions[direction], sq, direction)
        scored.append((sq, direction, side_size))
    scored.sort(key=lambda item: item[2], reverse=True)
    return scored


def _component_size(
    maze: Maze, start: Square | None, blocked_sq: Square, blocked_dir: int
) -> int:
    if start is None:
        return 0
    seen = {blocked_sq}
    stack = [start]
    count = 0
    while stack:
        sq = stack.pop()
        if sq in seen:
            continue
        seen.add(sq)
        count += 1
        for direction in range(4):
            other = sq.directions[direction]
            if other is None or other in seen:
                continue
            if sq is blocked_sq and direction == blocked_dir:
                continue
            if other is blocked_sq and direction == _reverse(blocked_dir):
                continue
            if not sq.blocked[direction] and sq.doors[direction] == -1:
                stack.append(other)
    return count


def find_articulation_points(maze: Maze) -> list[Square]:
    disc: dict[Square, int] = {}
    low: dict[Square, int] = {}
    parent: dict[Square, Square | None] = {}
    points: set[Square] = set()
    timer = [0]

    def dfs(sq: Square, is_root: bool) -> None:
        children = 0
        disc[sq] = low[sq] = timer[0]
        timer[0] += 1
        for neighbor, _ in _neighbors(maze, sq):
            if neighbor not in disc:
                parent[neighbor] = sq
                children += 1
                dfs(neighbor, False)
                low[sq] = min(low[sq], low[neighbor])
                if not is_root and low[neighbor] >= disc[sq]:
                    points.add(sq)
                if is_root and children > 1:
                    points.add(sq)
            elif neighbor != parent.get(sq):
                low[sq] = min(low[sq], disc[neighbor])

    for sq in maze.all_squares:
        if sq not in disc:
            parent[sq] = None
            dfs(sq, True)
    return list(points)


def _reverse(direction: int) -> int:
    return (direction + 2) % 4
