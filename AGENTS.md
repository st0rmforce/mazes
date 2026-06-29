# Mazes — agent guide

This repository contains the **dungeon generator** for a daily puzzle game. It does not include the final player-facing UI; that will live in a separate integration project. Focus here is on producing a fair, interesting, seed-deterministic maze each day.

## What this project is for

Each calendar day, the generator runs with a fixed seed and produces a maze-like dungeon. Players get unlimited attempts that day to explore it and find the **shortest complete route** from start to finish. Their score is their **best result** (fewest steps) across all attempts.

Because everything is derived from the seed, the dungeon is identical for every player on that day. Repeated attempts are about learning the layout, which keys matter, and which doors are worth opening.

## Game design goals

### Core loop

1. Player starts at the **entrance** and must reach the **exit**.
2. Movement is step-by-step through passable corridors (orthogonal grid).
3. Some passages are blocked by **doors**. Each door requires a specific **key** (identified by index / colour).
4. Keys are placed on floor squares. Picking up a key is part of the path and counts toward step total.
5. The player may open doors in any order; the optimal solution is the route that minimizes total steps, including detours to collect keys.

### Multiple paths and meaningful choices

The maze should offer **several viable routes** from start to finish, not a single obvious corridor. Doors create branching decisions:

- **Shortcut doors** — Opening the door (after fetching its key) makes the full start→finish path **shorter**, even after counting steps to reach the key. These are the “correct” strategic choices.
- **Red herring doors** — A door and key exist, but the full path through that door (entrance → key → door → exit) is **not shorter** than skipping it. These tempt the player into wasted detours.

A good daily puzzle mixes both: enough shortcuts that discovery feels rewarding, enough red herrings that blind key-collecting fails.

### Determinism

Given the same seed, generation must always produce the same:

- Grid size and wall layout
- Entrance and exit positions
- Door locations and key indices
- Key placements

The seed is the canonical daily puzzle identifier (e.g. derived from the date in the host application).

### Out of scope for this repo

- Final web/mobile UI, input handling, animations, sound
- Daily scheduling, leaderboards, user accounts
- Rendering beyond debug/visualization aids

The host project should call the generator, receive structured maze data, and handle presentation.

## Repository layout

| File | Role |
|------|------|
| `maze.py` | Main generator: `Maze` and `Square` classes, placement orchestration, debug drawing |
| `pathfinding.py` | BFS distance search, `shortest_routes()`, extended state (keys, monsters, traps) |
| `difficulty.py` | Named difficulty presets (`easy` / `medium` / `hard`), seed-derived selection |
| `content.py` | Content types: `DoorKind`, `Monster`, `Trap`, `Treasure` |
| `topology.py` | Bridge and articulation-point detection for section gates and monsters |
| `export.py` | `maze_to_dict()` / `maze_to_json()` for host integration |
| `numbercombos.py` | Enumerates key pickup orders (permutations of which keys to collect) |
| `numbercombos_data.py` | Precomputed combination tables for 1–8 keys (performance) |
| `README.md` | Short human-oriented summary |

## How generation works (current implementation)

Entry point: `Maze(seed=None, save_snapshots=False)` in `maze.py`.

### 0. Difficulty tier

`difficulty_for_seed(rng)` picks `easy`, `medium`, or `hard` from the seed. The tier controls grid size, door counts, wall density, section gates, monsters, traps, treasures, and key-distribution time. Each daily puzzle has one fixed difficulty baked into the seed.

### 1. Seeded random grid

- Size: from difficulty preset (roughly `16×16`–`28×28`).
- Each cell is a `Square` with four directional edges (up/right/down/left).
- Walls (`blocked`) are assigned with tunable density (`tightness`).
- Neighbouring cells agree on shared walls.

### 2. Connectivity

Blocked regions are opened until the grid is fully reachable from the initial entrance with no keys (`keys=0` bitmask).

### 3. Entrance and exit

`choose_start_end()` picks an entrance on the grid perimeter with high reach, then sets exit to the square furthest from entrance (by unkeyed distance). This pushes start and finish apart.

### 4. Section gates (key-gated regions)

`place_section_gates()` finds **bridge edges** in the maze graph (Tarjan) and places doors on bridges that gate side regions without disconnecting entrance from exit. These use key indices `0…section_gate_count-1` and `DoorKind.SECTION_GATE`.

### 5. Shortcut doors

`find_shortcuts()` places `DoorKind.SHORTCUT` doors on wall segments where opening would bridge areas whose shortest-path distances differ by more than a difficulty-specific threshold. Key indices start after section gates.

Doors are stored on both adjacent squares (`doors[direction] = key_index`). A player with key bitmask `K` may pass if `(1 << key_index) & K` is non-zero.

### 6. Key placement optimization

`distribute_keys()` runs for a difficulty-specific time budget. Each trial:

1. Randomly places one key per door on distinct floor squares.
2. Evaluates all key pickup orders via `shortest_routes()`.
3. Keeps the layout that maximizes **savings** vs the no-keys baseline.

`shortest_routes()` in `pathfinding.py` uses `numbercombos.get_combinations(door_count)` to try every order in which keys may be collected (empty set = no keys). For each order it sums: entrance→key₁→key₂→…→exit, using cached BFS distances for each state.

A keyset is recorded in `good_keysets` when it saves more than one-third of the baseline length (`base_len * 0.66 > base_len - count`). The best trial’s key positions are kept.

### 7. Blocking and optional monsters

- **Blocking monsters** sit on articulation points or chokepoints. Fighting costs `fight_steps` (from difficulty) and is included in the optimal route calculation. They behave like doors you must “pay steps” to pass.
- **Optional monsters** are placed off the optimal route (dead ends, gated regions). The host scores them separately; they do not affect `optimal_steps`.

### 8. Traps and treasures

- **Treasures** are placed off the optimal route (prefer dead ends). Bonus points are exported; they do not change the main step score.
- **Traps** are placed on optional branches. One-shot traps add a step penalty if stepped on; placement avoids the optimal route where possible.

### 9. Dead-end key placement

`move_keys_into_dead_ends()` relocates keys into dead ends (cells with three walls) when possible, so keys feel tucked into cul-de-sacs rather than sitting on main corridors.

### 10. Distance model

BFS in `pathfinding.py` floods from a start square with state `(start_x, start_y, key_bitmask, monster_bitmask, trap_bitmask)`. Distances depend on which doors are passable, which monsters have been fought, and which traps triggered. This powers both generation and route evaluation.

### 11. Validation and export

`validate_maze()` checks exit reachability and that optional content is not on the optimal route. `maze.to_dict()` / `export.maze_to_json()` expose the full dungeon for the host app.

### Debug visualization

`draw_maze()` uses pygame to write a PNG (walls, coloured doors/keys, cyan section gates, gold treasures, orange traps, purple/gray monsters, green entrance, red exit). This is a development aid, not the production renderer.

## Scoring model

| Content | Affects `optimal_steps`? | Notes |
|---------|--------------------------|-------|
| Movement, keys, shortcut doors | Yes | Core daily puzzle |
| Section gates | Yes | Required keys for gated regions |
| Blocking monsters | Yes | `fight_steps` added on mandatory path |
| Optional monsters | No | Side content; host tracks separately |
| Treasures | No | `bonus_points` for separate treasure score |
| Traps (off-route) | No | Penalty only if player detours onto them |

## Key types and conventions

```python
# Direction indices
UP, RIGHT, DOWN, LEFT = 0, 1, 2, 3

# Key bitmask: bit i set means key index i is held
keys = 0
keys |= 1 << key_index   # pick up key
```

## What agents should optimize for

When changing this code, preserve or improve:

1. **Seed determinism** — Same seed → same dungeon. Do not introduce non-deterministic sources outside `random.Random(seed)`.
2. **Puzzle quality** — Interesting tradeoffs between shortcut and red-herring doors; avoid trivial “collect every key” solutions.
3. **Generation time** — Key distribution is already time-boxed; avoid exponential blowups (hence precomputed combos and the 5+ key pruning in `numbercombos_data`).
4. **Separation from UI** — Prefer exposing maze data structures over baking in pygame or web assumptions. Visualization helpers are fine for debugging.

## Likely future work

- **Explicit red herrings** — Stronger guarantees that some doors never appear in optimal routes.
- **Daily seed helper** — Function that maps a date → seed string (currently `find_seed()` brute-forces size/key counts for testing).
- **Section-gate key ordering** — Stronger validation that gated-region keys are reachable before their gates.
- **Remove pygame dependency** from the core library path if the host project never needs it.

## Running locally

```bash
python maze.py
```

Builds one maze with a random seed, saves `finished.png`, and verifies `shortest_routes` is stable for the chosen keysets.

## Glossary

| Term | Meaning |
|------|---------|
| **Seed** | String passed to `random.Random`; defines the entire dungeon |
| **Door** | Wall segment that blocks passage until the matching key is held |
| **Key index** | Integer 0…`door_count-1`; door and key share an index |
| **Key bitmask** | Integer whose bits represent which keys the player holds |
| **Good keyset** | An ordered list of key indices whose collection meaningfully shortens the route |
| **Baseline** | Shortest entrance→exit path with no keys |
| **Steps** | Unit of movement; each grid move counts; key pickup logic should match host game rules |
| **Difficulty** | Named tier (`easy` / `medium` / `hard`) derived from seed; controls density and content counts |
| **Section gate** | Door on a bridge edge that locks off a side region until its key is held |
| **Blocking monster** | Must be fought (costs `fight_steps`) to pass; included in optimal route |
| **Optional monster** | Side content off the optimal route; separate scoring in host |
| **Trap** | One-shot cell penalty on detour routes |
| **Treasure** | Optional collectible with `bonus_points`; separate scoring in host |
