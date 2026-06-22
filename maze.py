from __future__ import annotations
import random
import time
import pygame
import numbercombos

UP = 0
RIGHT = 1
DOWN = 2
LEFT = 3

MIN_SIZE = 16
MAX_SIZE = 26
MAX_DOORS = 8

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
        for _ in range(4):
            self.blocked.append(bool(self.maze.rng.randint(0, 2)))

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

    def explore(self, key: tuple, distance: int):
        if key not in self.distances or self.distances[key] > distance:
            self.distances[key] = distance
            if distance > self.maze.max_distances.get(key, -1):
                self.maze.max_distances[key] = distance
            for dir in range(4):
                if self.directions[dir] and self.can_go_through(dir, key[2]):
                    self.directions[dir].explore(key, distance + 1)

    def remove_dist(self, key):
        if key in self.distances:
            del self.distances[key]

    def add_door(self, direction, key_index) -> bool:
        if self.directions[direction] is None:
            return False
        self.doors[direction] = key_index
        self.blocked[direction] = False
        other: Square = self.directions[direction]
        other.doors[reverse(direction)] = key_index
        other.blocked[reverse(direction)] = False
        self.maze.door_locations.append((self, key_index))
        self.maze.door_locations.append((other, key_index))

    def can_go_through(self, direction, key_mask):
        if not self.blocked[direction]:
            if self.doors[direction] == -1 or pow(2, self.doors[direction]) & key_mask:
                return True
        return False


class Maze:
    def __init__(self, seed: str | None = None):
        if seed is None:
            seed = random_string(20)
        self.seed = seed
        self.rng = random.Random(seed)
        self.width = self.rng.randint(MIN_SIZE, MAX_SIZE)
        self.height = self.rng.randint(MIN_SIZE, MAX_SIZE)
        self.door_count = self.rng.randint(1, MAX_DOORS)
        self.grid: list[list[Square]] = []
        self.all_squares: list[Square] = []
        self.key_locations: list[Square] = []
        self.door_locations = []
        self.longest_path = 0
        self.max_distances = {}
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
        base_key = (self.entrance.x, self.entrance.y, 0)
        self.find_distances(self.entrance, 0)
        blocked = self.find_blocked_cells(self.entrance, 0)
        self.rng.shuffle(blocked)

        while blocked:
            unblocked = False
            while not unblocked:
                sq = blocked.pop()
                dir = self.rng.randint(0, 3)
                if sq.directions[dir] and base_key in sq.directions[dir].distances:
                    unblocked = True
                    sq.blocked[dir] = False
                    sq.directions[dir].blocked[reverse(dir)] = False
                if not blocked:
                    blocked = self.find_blocked_cells(self.entrance, 0)
                    self.rng.shuffle(blocked)
            self.full_dist_wipe()
            self.find_distances(self.entrance, 0)
            blocked = self.find_blocked_cells(self.entrance, 0)
            self.rng.shuffle(blocked)

        self.longest_path = self.choose_start_end()
        self.find_shortcuts(doors=self.door_count)
        best = -1
        key_positions = []
        st_time=time.time()
        pic_index = 0
        while time.time() < st_time+30:
            self.full_dist_wipe()
            self.place_keys()
            saved = self.shortest_routes()
            if saved > best:
                self.draw_maze(pic_index)
                pic_index+=1
                best = saved
                key_positions = self.key_locations.copy()

        self.key_locations = key_positions
        print(best)
        print("doors",self.door_locations)
        print("keys",self.key_locations)

    def choose_start_end(self) -> int:
        self.full_dist_wipe()
        for x in range(self.width):
            self.find_distances(self.grid[x][0], 0)
            self.find_distances(self.grid[x][self.height - 1], 0)
        for y in range(self.height):
            self.find_distances(self.grid[0][y], 0)
            self.find_distances(self.grid[self.width - 1][y], 0)
        best = 0
        squares = list(self.max_distances.keys())
        self.rng.shuffle(squares)
        for k in squares:
            if self.max_distances[k] > best:
                self.entrance = self.grid[k[0]][k[1]]
        furthest = 0
        for sq in self.all_squares:
            dist = sq.distances.get((self.entrance.x, self.entrance.y, 0), -1)
            if dist > furthest:
                self.exit = sq
                furthest = dist
        return furthest

    def find_shortcuts(self, doors=6):
        keys = 0
        start = self.entrance
        for key in range(doors):
            self.wipe_distances(start, keys)
            self.find_distances(start, keys)
            shortcuts: list[tuple[int, int, int, int]] = []
            for sq in self.all_squares:
                for dir in range(4):
                    if sq.directions[dir]:
                        a = sq.distances.get((start.x, start.y, keys))
                        b = sq.directions[dir].distances.get((start.x, start.y, keys))
                        if None not in (a, b) and abs(a - b) > 10:
                            shortcuts.append((abs(a - b), sq.x, sq.y, dir))
            if shortcuts:
                shortcuts.sort(reverse=True)
                door_params = shortcuts[0]
                sq = self.grid[door_params[1]][door_params[2]]
                sq.add_door(door_params[3], key)
            keys += pow(2, key)

    def wipe_distances(self, start_square: Square, keys: int):
        key = (start_square.x, start_square.y, keys)
        for col in self.grid:
            for sq in col:
                sq.remove_dist(key)

    def full_dist_wipe(self):
        self.max_distances = {}
        for col in self.grid:
            for sq in col:
                sq.distances = {}

    def find_blocked_cells(self, start_square: Square, keys: int) -> list[Square]:
        key = (start_square.x, start_square.y, keys)
        blocked = []
        for col in self.grid:
            for sq in col:
                if key not in sq.distances:
                    blocked.append(sq)
        return blocked

    def find_distances(self, start_square: Square, keys: int):
        key = (start_square.x, start_square.y, keys)
        start_square.explore(key, 0)

    def print_maze(self, keys=0):
        key = (self.entrance.x, self.entrance.y, keys)
        for y in range(self.height):
            line = ""
            for x in range(self.width):
                sq = self.grid[x][y]
                line += f"{sq.distances.get(key, -1):02d} "
            print()
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
            step = 360 / self.door_count
            col.hsva = ((key_index * step) % 360, 100, 99, 100)
            return col

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
                    if sq.doors[UP] >= 0:
                        canvas.set_at(
                            (corner[0] + i, corner[1]), key_colour(sq.doors[UP])
                        )
                    if sq.doors[RIGHT] >= 0:
                        canvas.set_at(
                            (corner[0] + 4, corner[1] + i), key_colour(sq.doors[RIGHT])
                        )

                if sq in self.key_locations:
                    canvas.set_at(
                        (corner[0] + 2, corner[1] + 2),
                        key_colour(self.key_locations.index(sq)),
                    )

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
        self.find_distances(self.entrance, 0)
        for i in range(self.door_count):
            pick = self.rng.choice(self.all_squares)
            while pick in self.key_locations or pick == self.entrance or pick == self.exit:
                pick = self.rng.choice(self.all_squares)
            self.key_locations.append(pick)

    def shortest_routes(self):

        base_len = None
        savings = 0
        combos = numbercombos.get_combinations(self.door_count)
        if len(combos) >10000:
            picks = []
            for i in range(8000):
                pick = self.rng.choice(combos)
                while pick in picks:
                    pick = self.rng.choice(combos)
                picks.append(pick)
            combos = picks
        for keyset in combos:
            count = 0
            begin = self.entrance
            target = begin
            keys = 0
            for digit in keyset:
                begin = target
                target = self.key_locations[digit - 1]
                keys += pow(2, digit - 1)
                self.find_distances(begin, keys)
                count += target.distances[(begin.x, begin.y, keys)]
            begin = target
            target = self.exit
            self.find_distances(begin, keys)
            count += target.distances[(begin.x, begin.y, keys)]
            if base_len is None:
                base_len = count
            savings = max(savings,base_len-count)
        return savings


def find_seed(width, height) -> str:
    w = -1
    h = -1
    seed = ""
    while w != width or h != height:
        seed = random_string(20)
        rng = random.Random(seed)
        w = rng.randint(MIN_SIZE, MAX_SIZE)
        h = rng.randint(MIN_SIZE, MAX_SIZE)
    return seed


good = False
test = Maze()
test.draw_maze("finished")
