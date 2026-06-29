from __future__ import annotations

from typing import TYPE_CHECKING

import numbercombos

if TYPE_CHECKING:
    from maze import Maze, Square

BIG_DISTANCE = 9999999


def path_key(
    start_x: int,
    start_y: int,
    key_mask: int,
    monster_mask: int = 0,
    trap_mask: int = 0,
) -> tuple[int, int, int, int, int]:
    return (start_x, start_y, key_mask, monster_mask, trap_mask)


def _arrival_costs(square: Square, distance: int, monster_mask: int, trap_mask: int) -> tuple[int, int, int]:
    if square.monster and square.monster.blocking:
        bit = 1 << square.monster.index
        if not (monster_mask & bit):
            distance += square.monster.fight_steps
            monster_mask |= bit
    if square.trap and square.trap.one_shot:
        bit = 1 << square.trap.index
        if not (trap_mask & bit):
            distance += square.trap.step_penalty
            trap_mask |= bit
    return distance, monster_mask, trap_mask


def explore_square(
    square: Square,
    origin_state: tuple[int, int, int, int, int],
    distance: int,
    maze: Maze,
) -> None:
    key_mask = origin_state[2]
    monster_mask = origin_state[3]
    trap_mask = origin_state[4]

    distance, monster_mask, trap_mask = _arrival_costs(
        square, distance, monster_mask, trap_mask
    )
    state = path_key(origin_state[0], origin_state[1], key_mask, monster_mask, trap_mask)

    if state in square.distances and square.distances[state] <= distance:
        return
    square.distances[state] = distance
    if distance > maze.max_distances.get(state, -1):
        maze.max_distances[state] = distance

    child_origin = path_key(origin_state[0], origin_state[1], key_mask, monster_mask, trap_mask)
    for direction in range(4):
        neighbor = square.directions[direction]
        if neighbor and square.can_go_through(direction, key_mask):
            neighbor.explore(child_origin, distance + 1, maze)


def wipe_distances(maze: Maze, start_square: Square, state_key: tuple) -> None:
    for col in maze.grid:
        for sq in col:
            sq.remove_dist(state_key)


def full_dist_wipe(maze: Maze) -> None:
    maze.max_distances = {}
    for col in maze.grid:
        for sq in col:
            sq.distances = {}


def find_distances(
    maze: Maze,
    start_square: Square,
    key_mask: int,
    monster_mask: int = 0,
    trap_mask: int = 0,
) -> tuple[int, int, int, int, int]:
    state = path_key(start_square.x, start_square.y, key_mask, monster_mask, trap_mask)
    start_square.explore(state, 0, maze)
    return state


def find_blocked_cells(
    maze: Maze,
    start_square: Square,
    key_mask: int,
    monster_mask: int = 0,
    trap_mask: int = 0,
) -> list[Square]:
    state = path_key(start_square.x, start_square.y, key_mask, monster_mask, trap_mask)
    return [sq for col in maze.grid for sq in col if state not in sq.distances]


def cached_distance(
    maze: Maze,
    begin: Square,
    target: Square,
    key_mask: int,
    monster_mask: int,
    trap_mask: int,
    cache: dict[tuple, bool],
) -> tuple[int, int, int]:
    cache_key = path_key(begin.x, begin.y, key_mask, monster_mask, trap_mask)
    if cache_key not in cache:
        full_dist_wipe(maze)
        find_distances(maze, begin, key_mask, monster_mask, trap_mask)
        cache[cache_key] = True

    best = BIG_DISTANCE
    best_monster = monster_mask
    best_trap = trap_mask
    for state, dist in target.distances.items():
        if state[0] != begin.x or state[1] != begin.y or state[2] != key_mask:
            continue
        if (state[3] & monster_mask) != monster_mask:
            continue
        if (state[4] & trap_mask) != trap_mask:
            continue
        if dist < best:
            best = dist
            best_monster = state[3]
            best_trap = state[4]
    return best, best_monster, best_trap


def shortest_routes(maze: Maze, debug=None) -> int:
    dist_cache: dict[tuple, bool] = {}
    entrance_state = path_key(maze.entrance.x, maze.entrance.y, 0, 0, 0)
    full_dist_wipe(maze)
    find_distances(maze, maze.entrance, 0, 0, 0)
    dist_cache[entrance_state] = True
    maze.good_keysets = []
    base_len = maze.exit.distances.get(entrance_state, BIG_DISTANCE)
    savings = 0
    best_len = base_len
    maze.optimal_steps = base_len

    if debug is None:
        combos = numbercombos.get_combinations(maze.door_count)
    else:
        combos = list(debug) + [[]]

    for keyset in combos:
        count = 0
        begin = maze.entrance
        target = begin
        keys = 0
        monster_mask = 0
        trap_mask = 0
        unreachable = False
        for digit in keyset:
            begin = target
            target = maze.key_locations[digit - 1]
            dist, monster_mask, trap_mask = cached_distance(
                maze, begin, target, keys, monster_mask, trap_mask, dist_cache
            )
            if dist >= BIG_DISTANCE:
                unreachable = True
                break
            if debug is not None:
                print(f"{dist} steps from {begin} to {target}")
            count += dist
            keys |= 1 << (digit - 1)

        if unreachable:
            continue

        begin = target
        target = maze.exit
        dist, monster_mask, trap_mask = cached_distance(
            maze, begin, target, keys, monster_mask, trap_mask, dist_cache
        )
        if dist >= BIG_DISTANCE:
            continue
        if debug is not None:
            print(f"{dist} steps from {begin} to {target}")
        count += dist

        if count < best_len:
            best_len = count
            maze.optimal_steps = count

        if base_len - count > savings and base_len * 0.66 > base_len - count:
            savings = base_len - count
            maze.good_keysets.append(keyset)

    maze.baseline_steps = base_len
    return savings


def is_reachable(
    maze: Maze,
    start: Square,
    goal: Square,
    key_mask: int = 0,
    monster_mask: int = 0,
    trap_mask: int = 0,
) -> bool:
    full_dist_wipe(maze)
    find_distances(maze, start, key_mask, monster_mask, trap_mask)
    goal_state = path_key(start.x, start.y, key_mask, monster_mask, trap_mask)
    if goal_state in goal.distances:
        return True
    for state in goal.distances:
        if state[0] == start.x and state[1] == start.y and state[2] == key_mask:
            if (state[3] & monster_mask) == monster_mask and (state[4] & trap_mask) == trap_mask:
                return True
    return False


def optimal_route_cells(maze: Maze) -> set[Square]:
    """Approximate cells on a best mandatory route (entrance to exit, best keyset)."""
    full_dist_wipe(maze)
    keyset = maze.good_keysets[0] if maze.good_keysets else []
    keys = 0
    monster_mask = 0
    trap_mask = 0
    waypoints = [maze.entrance]
    for digit in keyset:
        waypoints.append(maze.key_locations[digit - 1])
        keys |= 1 << (digit - 1)
    waypoints.append(maze.exit)

    cells: set[Square] = set()
    dist_cache: dict[tuple, bool] = {}
    for begin, target in zip(waypoints, waypoints[1:]):
        cells.add(begin)
        cells.add(target)
        cache_key = path_key(begin.x, begin.y, keys, monster_mask, trap_mask)
        if cache_key not in dist_cache:
            full_dist_wipe(maze)
            find_distances(maze, begin, keys, monster_mask, trap_mask)
            dist_cache[cache_key] = True
        _, monster_mask, trap_mask = cached_distance(
            maze, begin, target, keys, monster_mask, trap_mask, dist_cache
        )
    return cells
