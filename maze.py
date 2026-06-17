from __future__ import annotations
import random
import pygame

UP = 0
RIGHT = 1
DOWN = 2
LEFT = 3

MIN_SIZE = 15
MAX_SIZE = 26

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
        self.doors = [0] * 4
        for _ in range(4):
            self.blocked.append(bool(self.maze.rng.randint(0, 2)))

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

    def can_go_through(self, direction, key_mask):
        if not self.blocked[direction]:
            if not self.doors[direction] or pow(2, self.doors[direction]) & key_mask:
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
        self.grid: list[list[Square]] = []
        self.max_distances = {}
        for x in range(self.width):
            self.grid.append([])
            for y in range(self.height):
                self.grid[-1].append(Square(x, y, self))
        for col in self.grid:
            for sq in col:
                sq.set_directions()
        self.entrance = self.rng.choice(self.rng.choice(self.grid))
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
        for x in range(self.width):
            self.find_distances(self.grid[x][0], 0)
            self.find_distances(self.grid[x][self.height - 1], 0)
        for y in range(self.height):
            self.find_distances(self.grid[0][y], 0)
            self.find_distances(self.grid[self.width - 1][y], 0)

        best = 0
        squares = list(self.max_distances.keys())
        self.rng.shuffle( squares)
        for k in squares:
            if self.max_distances[k] > best:
                self.entrance = self.grid[k[0]][k[1]]

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
        distance_key = (start_square.x, start_square.y, keys)
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
                distance = sq.distances.get(distance_key, 0)
                temperature = pygame.Color("red")
                temperature.hsva = ((distance * 4)%360, 100, 100, 100)
                canvas.set_at((corner[0] + 2, corner[1] + 2), temperature)

        pygame.image.save(
            pygame.transform.scale(canvas, (pix_w * 5, pix_h * 5)), f"{name}.png"
        )


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


test = Maze(find_seed(MAX_SIZE,MAX_SIZE))
test.draw_maze("longest")
