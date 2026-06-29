from __future__ import annotations

import random
import time

import pygame

import pathfinding
from content import DoorKind, Monster, Trap, Treasure
from difficulty import difficulty_for_seed
from export import maze_to_dict
from topology import find_articulation_points, find_bridges

UP = 0
RIGHT = 1
DOWN = 2
LEFT = 3

MIN_SIZE = 16
MAX_SIZE = 28
MAX_DOORS = 8
KEY_DISTRIBUTION_SECONDS = 10

BIG_DISTANCE = 9999999


def reverse(dir: int) -> int:
    return (dir + 2) % 4


def random_string(size: int) -> str:
    output = ""
    for _ in range(size):
        output += random.choice(
            "1234567890qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM"
        )
    return output


class Square:
    def __init__(self, x: int, y: int, maze: Maze):
        self.maze = maze
        self.x = x
        self.y = y
        self.directions: list[Square | None] = [None] * 4
        self.distances = {}
        self.blocked = []
        self.doors = [-1] * 4
        self.monster: Monster | None = None
        self.trap: Trap | None = None
        self.treasure: Treasure | None = None
        for _ in range(4):
            self.blocked.append(bool(self.maze.rng.randint(0, maze.tightness)))

    def __str__(self):
        return f"Square {self.x},{self.y}"

    def __repr__(self):
        return f"Square {self.x}x{self.y}"

    def set_directions(self):
        if self.x > 0:
            self.directions[LEFT] = self.maze.grid[self.x - 1][self.y]
        else:
            self.blocked[LEFT] = True
        if self.y > 0:
            self.directions[UP] = self.maze.grid[self.x][self.y - 1]
        else:
            self.blocked[UP] = True
        if self.x < self.maze.width - 1:
            self.directions[RIGHT] = self.maze.grid[self.x + 1][self.y]
        else:
            self.blocked[RIGHT] = True
        if self.y < self.maze.height - 1:
            self.directions[DOWN] = self.maze.grid[self.x][self.y + 1]
        else:
            self.blocked[DOWN] = True
        for dir in range(4):
            if (
                self.directions[dir]
                and self.blocked[dir] != self.directions[dir].blocked[reverse(dir)]
            ):
                pick = bool(self.maze.rng.randint(0, 1))
                self.blocked[dir] = pick
                self.directions[dir].blocked[reverse(dir)] = pick

    def explore(self, origin_state: tuple, distance: int, maze: Maze | None = None):
        if maze is None:
            maze = self.maze
        pathfinding.explore_square(self, origin_state, distance, maze)

    def remove_dist(self, key):
        if key in self.distances:
            del self.distances[key]

    def add_door(self, direction, key_index, kind: DoorKind = DoorKind.SHORTCUT) -> bool:
        if self.directions[direction] is None:
            return False
        if self.doors[direction] >= 0:
            return False
        self.doors[direction] = key_index
        self.blocked[direction] = False
        other: Square = self.directions[direction]
        other.doors[reverse(direction)] = key_index
        other.blocked[reverse(direction)] = False
        self.maze.door_locations.append((self, key_index))
        self.maze.door_locations.append((other, key_index))
        self.maze.door_entries.append(
            {"square": self, "direction": direction, "key_index": key_index, "kind": kind}
        )
        return True

    def can_go_through(self, direction, key_mask):
        if not self.blocked[direction]:
            if self.doors[direction] == -1 or (1 << self.doors[direction]) & key_mask:
                return True
        return False

    def is_occupied(self) -> bool:
        return (
            self.monster is not None
            or self.trap is not None
            or self.treasure is not None
            or self in self.maze.key_locations
            or self is self.maze.entrance
            or self is self.maze.exit
        )


class Maze:
    def __init__(self, seed: str | None = None, save_snapshots: bool = False):
        if seed is None:
            seed = random_string(20)
        self.seed = seed
        self.save_snapshots = save_snapshots
        self.rng = random.Random(seed)
        self.difficulty = difficulty_for_seed(self.rng)
        self.width = self.rng.randint(self.difficulty.min_size, self.difficulty.max_size)
        self.height = self.rng.randint(self.difficulty.min_size, self.difficulty.max_size)
        self.tightness = self.rng.choice(self.difficulty.tightness_weights)

        shortcut_target = self.rng.randint(
            self.difficulty.door_count_min, self.difficulty.door_count_max
        )
        self.section_gate_count = self.rng.randint(
            self.difficulty.section_gate_min, self.difficulty.section_gate_max
        )
        self.door_count = min(self.section_gate_count + shortcut_target, MAX_DOORS)
        self.section_gate_count = min(self.section_gate_count, self.door_count)
        self.shortcut_door_count = self.door_count - self.section_gate_count

        self.blocking_monster_count = self.rng.randint(
            self.difficulty.blocking_monster_min, self.difficulty.blocking_monster_max
        )
        self.optional_monster_count = self.rng.randint(
            self.difficulty.optional_monster_min, self.difficulty.optional_monster_max
        )
        self.trap_count = self.rng.randint(self.difficulty.trap_min, self.difficulty.trap_max)
        self.treasure_count = self.rng.randint(
            self.difficulty.treasure_min, self.difficulty.treasure_max
        )

        self.grid: list[list[Square]] = []
        self.all_squares: list[Square] = []
        self.key_locations: list[Square] = []
        self.dead_ends: list[Square] = []
        self.door_locations = []
        self.door_entries: list[dict] = []
        self.longest_path = 0
        self.max_distances = {}
        self.good_keysets: list = []
        self.best_keysets: list = []
        self.optimal_steps = 0
        self.baseline_steps = 0
        self.optimal_route_cells: set[Square] = set()

        for x in range(self.width):
            self.grid.append([])
            for y in range(self.height):
                self.grid[-1].append(Square(x, y, self))
                self.all_squares.append(self.grid[-1][-1])
        self.rng.shuffle(self.all_squares)
        for col in self.grid:
            for sq in col:
                sq.set_directions()
        self.entrance = self.rng.choice(self.rng.choice(self.grid))
        self.exit = self.rng.choice(self.rng.choice(self.grid))
        self._ensure_connectivity()
        self.longest_path = self.choose_start_end()
        self.place_section_gates(self.section_gate_count)
        self.door_count = self.section_gate_count + self.find_shortcuts(
            doors=self.shortcut_door_count, key_offset=self.section_gate_count
        )
        self.distribute_keys()
        self.place_blocking_monsters()
        self.find_dead_ends()
        self.move_keys_into_dead_ends()
        pathfinding.shortest_routes(self)
        self.optimal_route_cells = pathfinding.optimal_route_cells(self)
        self.place_optional_monsters()
        self.place_traps_and_treasures()
        pathfinding.shortest_routes(self)
        self.optimal_route_cells = pathfinding.optimal_route_cells(self)
        validate_maze(self)

    def _ensure_connectivity(self):
        base_key = pathfinding.path_key(self.entrance.x, self.entrance.y, 0, 0, 0)
        pathfinding.find_distances(self, self.entrance, 0)
        blocked = pathfinding.find_blocked_cells(self, self.entrance, 0)
        self.rng.shuffle(blocked)

        while blocked:
            opened = False
            self.rng.shuffle(blocked)
            for sq in blocked:
                if opened:
                    break
                dirs = list(range(4))
                self.rng.shuffle(dirs)
                for dir in dirs:
                    neighbor = sq.directions[dir]
                    if neighbor and base_key in neighbor.distances:
                        sq.blocked[dir] = False
                        neighbor.blocked[reverse(dir)] = False
                        opened = True
                        break
            if not opened:
                sq = blocked[0]
                for dir in range(4):
                    neighbor = sq.directions[dir]
                    if neighbor:
                        sq.blocked[dir] = False
                        neighbor.blocked[reverse(dir)] = False
                        break
            pathfinding.full_dist_wipe(self)
            pathfinding.find_distances(self, self.entrance, 0)
            base_key = pathfinding.path_key(self.entrance.x, self.entrance.y, 0, 0, 0)
            blocked = pathfinding.find_blocked_cells(self, self.entrance, 0)
            self.rng.shuffle(blocked)

    def door_entry_for(self, sq: Square, direction: int) -> dict | None:
        for entry in self.door_entries:
            if entry["square"] is sq and entry["direction"] == direction:
                return entry
        return None

    def distribute_keys(self):
        best = -1
        key_positions = []
        st_time = time.time()
        pic_index = 0
        self.best_keysets = []
        duration = self.difficulty.key_distribution_seconds
        while time.time() < st_time + duration:
            pathfinding.full_dist_wipe(self)
            self.place_keys()
            saved = pathfinding.shortest_routes(self)
            if saved > best:
                self.best_keysets = list(self.good_keysets)
                if self.save_snapshots:
                    self.draw_maze(str(pic_index))
                    pic_index += 1
                best = saved
                key_positions = self.key_locations.copy()

        self.key_locations = key_positions
        print(best)
        print("doors", self.door_locations)
        print("keys", self.key_locations)

    def choose_start_end(self) -> int:
        pathfinding.full_dist_wipe(self)
        for x in range(self.width):
            pathfinding.find_distances(self, self.grid[x][0], 0)
            pathfinding.find_distances(self, self.grid[x][self.height - 1], 0)
        for y in range(self.height):
            pathfinding.find_distances(self, self.grid[0][y], 0)
            pathfinding.find_distances(self, self.grid[self.width - 1][y], 0)
        best = 0
        squares = list(self.max_distances.keys())
        self.rng.shuffle(squares)
        for k in squares:
            if self.max_distances[k] > best:
                self.entrance = self.grid[k[0]][k[1]]
        furthest = 0
        entrance_state = pathfinding.path_key(self.entrance.x, self.entrance.y, 0, 0, 0)
        for sq in self.all_squares:
            dist = sq.distances.get(entrance_state, -1)
            if dist > furthest:
                self.exit = sq
                furthest = dist
        return furthest

    def place_section_gates(self, gate_count: int) -> int:
        if gate_count <= 0:
            return 0
        bridges = find_bridges(self)
        placed = 0
        used_edges: set[tuple[int, int, int]] = set()
        for sq, direction, _side_size in bridges:
            if placed >= gate_count:
                break
            edge = (sq.x, sq.y, direction)
            if edge in used_edges or sq.doors[direction] >= 0:
                continue
            if not self._entrance_exit_connected_without_edge(sq, direction):
                continue
            if sq.add_door(direction, placed, DoorKind.SECTION_GATE):
                used_edges.add(edge)
                placed += 1
        self.section_gate_count = placed
        return placed

    def _entrance_exit_connected_without_edge(self, blocked_sq: Square, blocked_dir: int) -> bool:
        seen = {self.entrance}
        stack = [self.entrance]
        while stack:
            sq = stack.pop()
            for direction in range(4):
                other = sq.directions[direction]
                if other is None or other in seen:
                    continue
                if sq is blocked_sq and direction == blocked_dir:
                    continue
                if other is blocked_sq and direction == reverse(blocked_dir):
                    continue
                if sq.blocked[direction] and sq.doors[direction] == -1:
                    continue
                if sq.doors[direction] >= 0:
                    continue
                seen.add(other)
                stack.append(other)
                if other is self.exit:
                    return True
        return self.exit in seen

    def find_shortcuts(self, doors=6, key_offset=0):
        keys = (1 << key_offset) - 1 if key_offset else 0
        start = self.entrance
        added = 0
        threshold = self.difficulty.shortcut_gap_threshold
        for key in range(key_offset, key_offset + doors):
            pathfinding.wipe_distances(
                self, start, pathfinding.path_key(start.x, start.y, keys, 0, 0)
            )
            pathfinding.find_distances(self, start, keys)
            state = pathfinding.path_key(start.x, start.y, keys, 0, 0)
            shortcuts: list[tuple[int, int, int, int]] = []
            for sq in self.all_squares:
                for dir in range(4):
                    if sq.directions[dir]:
                        a = sq.distances.get(state)
                        b = sq.directions[dir].distances.get(state)
                        if None not in (a, b) and abs(a - b) > threshold:
                            if sq.doors[dir] == -1:
                                shortcuts.append((abs(a - b), sq.x, sq.y, dir))
            if shortcuts:
                shortcuts.sort(reverse=True)
                door_params = shortcuts[0]
                sq = self.grid[door_params[1]][door_params[2]]
                if sq.add_door(door_params[3], key, DoorKind.SHORTCUT):
                    added += 1
            keys |= 1 << key
        self.shortcut_door_count = added
        return added

    def place_blocking_monsters(self):
        if self.blocking_monster_count <= 0:
            return
        candidates = [
            sq
            for sq in find_articulation_points(self)
            if sq not in (self.entrance, self.exit) and not sq.is_occupied()
        ]
        if not candidates:
            candidates = [
                sq
                for sq in self.all_squares
                if sq not in (self.entrance, self.exit)
                and sq.blocked.count(True) == 2
                and not sq.is_occupied()
            ]
        self.rng.shuffle(candidates)
        for index in range(min(self.blocking_monster_count, len(candidates))):
            sq = candidates[index]
            sq.monster = Monster(
                index=index,
                blocking=True,
                fight_steps=self.difficulty.fight_steps,
            )

    def place_optional_monsters(self):
        if self.optional_monster_count <= 0:
            return
        candidates = [
            sq
            for sq in self.dead_ends
            if not sq.is_occupied() and sq not in self.optimal_route_cells
        ]
        if len(candidates) < self.optional_monster_count:
            extra = [
                sq
                for sq in self.all_squares
                if sq not in candidates
                and not sq.is_occupied()
                and sq not in self.optimal_route_cells
            ]
            self.rng.shuffle(extra)
            candidates.extend(extra)
        self.rng.shuffle(candidates)
        start_index = sum(1 for sq in self.all_squares if sq.monster and sq.monster.blocking)
        for offset in range(min(self.optional_monster_count, len(candidates))):
            sq = candidates[offset]
            sq.monster = Monster(
                index=start_index + offset,
                blocking=False,
                fight_steps=self.difficulty.fight_steps,
            )

    def place_traps_and_treasures(self):
        off_route = [
            sq
            for sq in self.all_squares
            if sq not in self.optimal_route_cells
            and not sq.is_occupied()
        ]
        dead_end_off_route = [sq for sq in self.dead_ends if sq in off_route]
        self.rng.shuffle(dead_end_off_route)
        self.rng.shuffle(off_route)

        treasure_placed = 0
        for sq in dead_end_off_route:
            if treasure_placed >= self.treasure_count:
                break
            sq.treasure = Treasure(
                index=treasure_placed,
                bonus_points=self.difficulty.treasure_bonus_points,
            )
            treasure_placed += 1
        for sq in off_route:
            if treasure_placed >= self.treasure_count:
                break
            if sq.treasure:
                continue
            sq.treasure = Treasure(
                index=treasure_placed,
                bonus_points=self.difficulty.treasure_bonus_points,
            )
            treasure_placed += 1

        trap_placed = 0
        trap_candidates = [sq for sq in off_route if not sq.treasure and not sq.monster]
        self.rng.shuffle(trap_candidates)
        for sq in trap_candidates:
            if trap_placed >= self.trap_count:
                break
            sq.trap = Trap(
                index=trap_placed,
                step_penalty=self.difficulty.trap_step_penalty,
                one_shot=True,
            )
            trap_placed += 1

    def wipe_distances(self, start_square: Square, keys: int):
        pathfinding.wipe_distances(
            self, start_square, pathfinding.path_key(start_square.x, start_square.y, keys, 0, 0)
        )

    def full_dist_wipe(self):
        pathfinding.full_dist_wipe(self)

    def find_blocked_cells(self, start_square: Square, keys: int) -> list[Square]:
        return pathfinding.find_blocked_cells(self, start_square, keys)

    def find_distances(self, start_square: Square, keys: int):
        pathfinding.find_distances(self, start_square, keys)

    def print_maze(self, keys=0):
        key = pathfinding.path_key(self.entrance.x, self.entrance.y, keys, 0, 0)
        for y in range(self.height):
            line = ""
            for x in range(self.width):
                sq = self.grid[x][y]
                line += f"{sq.distances.get(key, -1):02d} "
            print(line)

    def draw_maze(self, name: str, start_square: Square | None = None, keys=0):
        if start_square is None:
            start_square = self.entrance
        pix_w = self.width * 5
        pix_h = self.height * 5
        canvas = pygame.Surface((pix_w, pix_h))
        canvas.fill("white")

        def key_colour(key_index):
            col = pygame.Color("red")
            step = 360 / max(self.door_count, 1)
            col.hsva = ((key_index * step) % 360, 100, 99, 100)
            return col

        key_index = {sq: i for i, sq in enumerate(self.key_locations)}

        for sq_y in range(self.height):
            for sq_x in range(self.width):
                sq = self.grid[sq_x][sq_y]
                corner = (sq_x * 5, sq_y * 5)
                canvas.set_at((corner[0], corner[1]), "black")
                canvas.set_at((corner[0] + 4, corner[1]), "black")
                canvas.set_at((corner[0], corner[1] + 4), "black")
                canvas.set_at((corner[0] + 4, corner[1] + 4), "black")

                for i in range(1, 4):
                    if sq.blocked[UP]:
                        canvas.set_at((corner[0] + i, corner[1]), "black")
                    if sq.blocked[RIGHT]:
                        canvas.set_at((corner[0] + 4, corner[1] + i), "black")
                    if sq.blocked[LEFT]:
                        canvas.set_at((corner[0], corner[1] + i), "black")
                    if sq.blocked[DOWN]:
                        canvas.set_at((corner[0] + i, corner[1] + 4), "black")
                for i in range(1, 4):
                    if sq.doors[UP] >= 0:
                        entry = self.door_entry_for(sq, UP)
                        col = (
                            pygame.Color("cyan")
                            if entry and entry["kind"] == DoorKind.SECTION_GATE
                            else key_colour(sq.doors[UP])
                        )
                        canvas.set_at((corner[0] + i, corner[1]), col)
                    if sq.doors[RIGHT] >= 0:
                        entry = self.door_entry_for(sq, RIGHT)
                        col = (
                            pygame.Color("cyan")
                            if entry and entry["kind"] == DoorKind.SECTION_GATE
                            else key_colour(sq.doors[RIGHT])
                        )
                        canvas.set_at((corner[0] + 4, corner[1] + i), col)

                if sq in key_index:
                    canvas.set_at(
                        (corner[0] + 2, corner[1] + 2),
                        key_colour(key_index[sq]),
                    )
                if sq.treasure:
                    canvas.set_at((corner[0] + 2, corner[1] + 2), pygame.Color("gold"))
                if sq.trap:
                    canvas.set_at((corner[0] + 1, corner[1] + 2), pygame.Color("orange"))
                    canvas.set_at((corner[0] + 3, corner[1] + 2), pygame.Color("orange"))
                if sq.monster:
                    colour = pygame.Color("purple") if sq.monster.blocking else pygame.Color("gray")
                    canvas.set_at((corner[0] + 2, corner[1] + 1), colour)
                    canvas.set_at((corner[0] + 2, corner[1] + 3), colour)

                if self.exit == sq:
                    for x in range(1, 4):
                        for y in range(1, 4):
                            canvas.set_at(
                                (corner[0] + x, corner[1] + y), pygame.Color("red")
                            )
                if self.entrance == sq:
                    for x in range(1, 4):
                        for y in range(1, 4):
                            canvas.set_at(
                                (corner[0] + x, corner[1] + y), pygame.Color("green")
                            )

        pygame.image.save(
            pygame.transform.scale(canvas, (pix_w * 5, pix_h * 5)), f"{name}.png"
        )

    def place_keys(self):
        self.key_locations = []
        pathfinding.find_distances(self, self.entrance, 0)
        candidates = [
            sq for sq in self.all_squares if sq not in (self.entrance, self.exit) and not sq.is_occupied()
        ]
        for _ in range(self.door_count):
            if not candidates:
                break
            pick = self.rng.choice(candidates)
            candidates.remove(pick)
            self.key_locations.append(pick)

    def shortest_routes(self, debug=None):
        return pathfinding.shortest_routes(self, debug)

    def find_dead_ends(self):
        self.dead_ends = []
        for sq in self.all_squares:
            if sq.blocked.count(True) == 3:
                self.dead_ends.append(sq)

    def move_keys_into_dead_ends(self):
        new_layout: list[Square] = []
        for key in self.key_locations:
            if key in self.dead_ends:
                new_layout.append(key)
                continue
            pathfinding.wipe_distances(
                self, key, pathfinding.path_key(key.x, key.y, 0, 0, 0)
            )
            pathfinding.find_distances(self, key, 0)
            closest = (9, key)
            key_state = pathfinding.path_key(key.x, key.y, 0, 0, 0)
            for dead_end in self.dead_ends:
                dist = dead_end.distances.get(key_state, BIG_DISTANCE)
                if (
                    dead_end not in self.key_locations
                    and dead_end not in new_layout
                    and dist < closest[0]
                ):
                    closest = (dist, dead_end)
            new_layout.append(closest[1])
        self.key_locations = new_layout

    def to_dict(self) -> dict:
        return maze_to_dict(self)


def validate_maze(maze: Maze) -> None:
    if maze.door_count > 0 and not maze.best_keysets and not maze.good_keysets:
        pass
    if not pathfinding.is_reachable(maze, maze.entrance, maze.exit):
        raise ValueError("Exit unreachable from entrance")
    for sq in maze.all_squares:
        if sq.monster and not sq.monster.blocking and sq in maze.optimal_route_cells:
            raise ValueError(f"Optional monster on optimal route at {sq.x},{sq.y}")
        if sq.treasure and sq in maze.optimal_route_cells:
            raise ValueError(f"Treasure on optimal route at {sq.x},{sq.y}")


def find_seed(width, height, keys: int | None = None) -> str:
    w = -1
    h = -1
    k = -1
    seed = ""
    while w != width or h != height or (keys is not None and k != keys):
        seed = random_string(20)
        rng = random.Random(seed)
        difficulty = difficulty_for_seed(rng)
        w = rng.randint(difficulty.min_size, difficulty.max_size)
        h = rng.randint(difficulty.min_size, difficulty.max_size)
        section_gates = rng.randint(difficulty.section_gate_min, difficulty.section_gate_max)
        shortcuts = rng.randint(difficulty.door_count_min, difficulty.door_count_max)
        k = min(section_gates + shortcuts, MAX_DOORS)
    return seed


if __name__ == "__main__":
    test = Maze()
    test.draw_maze("finished")
    keysets_before = list(test.best_keysets)
    test.shortest_routes(debug=test.best_keysets)
    assert test.best_keysets == keysets_before
    print(f"difficulty={test.difficulty.name} optimal_steps={test.optimal_steps}")
