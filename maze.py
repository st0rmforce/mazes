from __future__ import annotations
import random

UP = 0
RIGHT = 1
DOWN = 2
LEFT = 3

MIN_SIZE = 12
MAX_SIZE = 21

BIG_DISTANCE = 9999999


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
        for _ in range(4):
            self.blocked.append(self.maze.rng.choice([True, False]))

    def set_directions(self):
        if self.x > 0:
            self.directions[LEFT] = self.maze.grid[self.x - 1][self.y]
        if self.y > 0:
            self.directions[UP] = self.maze.grid[self.x][self.y - 1]
        if self.x < self.maze.width - 1:
            self.directions[RIGHT] = self.maze.grid[self.x + 1][self.y]
        if self.y < self.maze.height - 1:
            self.directions[DOWN] = self.maze.grid[self.x][self.y + 1]

    def explore(self, key: tuple, distance: int):
        if key not in self.distances or self.distances[key] > distance:
            self.distances[key] = distance
            for dir in range(4):
                if self.directions[dir] and not self.blocked[dir]:
                    self.directions[dir].explore(key, distance + 1)

    def remove_dist(self, key):
        if key in self.distances:
            del self.distances[key]


class Maze:
    def __init__(self, seed: str | None):
        if seed is None:
            seed = random_string(20)
        self.seed = seed
        self.rng = random.Random(seed)
        self.width = self.rng.randint(MIN_SIZE, MAX_SIZE)
        self.height = self.rng.randint(MIN_SIZE, MAX_SIZE)
        self.grid: list[list[Square]] = []
        for x in range(self.width):
            self.grid.append([])
            for y in range(self.height):
                self.grid[-1].append(Square(x, y, self))
        for col in self.grid:
            for sq in col:
                sq.set_directions()
        self.entrance = self.rng.choice(self.rng.choice(self.grid))
        base_key =  (self.entrance.x, self.entrance.y, 0)
        self.find_distances(self.entrance, 0)
        blocked = self.find_blocked_cells(self.entrance, 0)
        self.rng.shuffle(blocked)
        print(len(blocked))
        while blocked:
            unblocked = False
            while not unblocked:
                sq = blocked.pop()
                dir = self.rng.randint(0,3)
                if sq.directions[dir] and base_key in sq.directions[dir].distances:
                    unblocked = True
                    sq.blocked[dir] = False
                    sq.directions[dir].blocked[(dir+2)%4] = False
                if not blocked:
                    blocked = self.find_blocked_cells(self.entrance, 0)
                    self.rng.shuffle(blocked)  
            self.wipe_distances(self.entrance, 0)    
            self.find_distances(self.entrance, 0)
            blocked = self.find_blocked_cells(self.entrance, 0)
            self.rng.shuffle(blocked)        


    def wipe_distances(self, start_square: Square, keys: int):
        key = (start_square.x, start_square.y, keys)
        for col in self.grid:
            for sq in col:
                sq.remove_dist(key)

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


test = Maze("RrGdD3mT1PeBtEh0nZG6")
key = (test.entrance.x, test.entrance.y, 0)
for col in test.grid:
    line = ""
    for sq in col:
        line += f"{sq.distances.get(key, -1):02d} "
    print()
    print(line)
