# Mazes

Dungeon generator for a daily puzzle game. Each day, a fixed seed produces a maze-like dungeon that every player shares. Players get unlimited attempts to find the shortest route from entrance to exit; their score is their best result (fewest steps).

The final UI and game shell live in a separate project. This repo is the generation logic only.

## How it plays

- Start at the **entrance**, reach the **exit** by moving through corridors on an orthogonal grid.
- **Doors** block some passages until you hold the matching **key**.
- **Section gates** lock entire side regions behind keys (not just shortcuts).
- Keys sit on floor squares. Detours to collect keys count toward your step total.
- **Blocking monsters** must be fought to pass (costs extra steps on the main route).
- **Optional monsters**, **traps**, and **treasures** are side content with separate scoring in the host app.
- You can open doors in any order. The puzzle is finding which keys are worth fetching.

Good dungeons offer multiple routes. Some doors are **shortcuts** — the full path (entrance → key → door → exit) is shorter than going without them. Others are **red herrings** — collecting the key and using the door does not beat the simpler route.

Each seed also picks a **difficulty** tier (`easy`, `medium`, or `hard`) that controls maze size, door count, and how much optional content appears.

Because the dungeon is fully determined by the seed, players can learn the layout over repeated attempts within the same day.

## Quick start

```bash
python maze.py
```

Generates a maze with a random seed, saves a debug image (`finished.png`), and prints door/key placement.

To generate a specific dungeon:

```python
from maze import Maze
from export import maze_to_json

maze = Maze(seed="your-seed-here")
print(maze_to_json(maze))
```

## Project layout

| File | Purpose |
|------|---------|
| `maze.py` | Maze generation, placement orchestration, debug drawing |
| `pathfinding.py` | BFS routing, optimal step calculation |
| `difficulty.py` | Easy / medium / hard presets |
| `content.py` | Monsters, traps, treasures, door kinds |
| `topology.py` | Bridge detection for section gates |
| `export.py` | JSON export for host integration |
| `numbercombos.py` | Key pickup order enumeration |
| `numbercombos_data.py` | Precomputed combinations for performance |
| `AGENTS.md` | Detailed design and implementation guide for AI agents |

## Generation overview

1. Derive difficulty tier from seed.
2. Build a seeded random grid with walls.
3. Ensure the maze is fully connected.
4. Place entrance and exit far apart.
5. Add section gates on bridge edges and shortcut doors on high-value walls.
6. Optimize key positions so some key combinations genuinely shorten the route.
7. Place blocking monsters on chokepoints; optional monsters, traps, and treasures off the optimal route.
8. Tuck keys into dead ends where possible.
9. Validate and export structured JSON.

See [AGENTS.md](AGENTS.md) for the full design goals, algorithms, and guidance for contributors.

## Out of scope

- Player-facing UI, input, animations, sound
- Daily scheduling, accounts, leaderboards
- Production rendering (pygame is used only for debug output)
