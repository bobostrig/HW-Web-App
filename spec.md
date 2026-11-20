## Purpose
A crane operation game where the player uses the left tower crane to place three steel pieces in their highlighted target locations on each of five increasingly difficult levels. Each level has a three-minute time limit. The player must manage the load's changing capacity as the crane reaches farther out. This is a simple game inspired by crane load charts, not a tool for real-world crane operation.
## Inputs

Use either the arrow keys or WASD. Left and right move the trolley along the player's crane boom; up and down raise and lower the hook. When the trolley reaches the mast center, continuing to press toward the other side slowly turns the player crane around the mast so the trolley can reach the opposite side. The trolley cannot travel past the boom's ends, and the hook can move from boom height to ground level. The crane and trolley move at a steady, moderate speed. Press Space to pick up a beam when the hook is close enough, or release a carried beam. Only one beam can be carried at a time. When the carried beam is over an unfilled highlighted target, pressing Space places it there automatically. The player cannot steady a swaying load.
## Calculations

### Crane capacity by load radius

Measure the horizontal distance from the crane's center of rotation to the beam. Let `r` be the radius in feet and `C(r)` the maximum permitted beam weight in pounds. In the game scene, 500 horizontal scene units represent the full 150 ft boom reach: `r = min(150, |x - x_mast| * 150 / 500)`.

| Load radius | Maximum beam weight |
|---:|---:|
| 0–50 ft | 20,000 lb |
| 50 ft | 20,000 lb |
| 75 ft | 13,000 lb |
| 100 ft | 9,000 lb |
| 125 ft | 7,000 lb |
| 150 ft | 5,500 lb |

Capacity is constant at 20,000 lb from 0 through 50 ft. Between each pair of chart distances, calculate capacity with linear interpolation:

```text
C(r) = C1 + ((r - r1) / (r2 - r1)) * (C2 - C1)
```

Here `(r1, C1)` and `(r2, C2)` are the chart points immediately below and above the current radius. For example, at 112 ft:

```text
C(112) = 9,000 + ((112 - 100) / (125 - 100)) * (7,000 - 9,000)
       = 8,040 lb
```

Update radius and capacity continuously as the trolley moves. Display the interpolated maximum capacity in pounds and the beam's capacity percentage. Only the beam's weight counts; the cable's weight is excluded.
### Capacity percentage and warning

Let `W` be the beam�s weight in pounds. Calculate the capacity percentage at the current radius as:

```text
P(r) = (W / C(r)) * 100%
```

Show a warning when:

```text
P(r) >= 90%
```

If the beam reaches or exceeds 100% capacity:

```text
P(r) >= 100%
```

the player crane falls into the unfinished tower, then its boom and mast sections detach. The tower's columns, crossbeams, and braces also detach and fall as separate steel members. After the collapse, show a Level Failed screen with a Restart Level button that resets the current level.

### Beam generation and route feasibility

At the start of each level, generate three beams, each with a weight `W_i`, a pickup radius `r_p,i`, and a target radius `r_t,i`, where `i` is 1, 2, or 3. Spawn one beam on the left side of the player crane mast and the other two on the right. Keep the challenge beam on the right so the player can carry it to the full 150 ft radius. Randomize pickup positions within the left and right boom areas while keeping all three positions reachable.

For each beam, check capacity at pickup and continuously along the trolley�s route to its target. Let `R_i` be the set of radii the beam passes through while being carried. The beam is feasible only if:

```text
W_i / C(r) < 1 for every r in R_i
```

Equivalently:

```text
W_i < min(C(r) for r in R_i)
```

Generate the first two beam weights in 250 lb increments between 50% and a level-dependent upper fraction of their route capacity. Let `C_route,i = min(C(r) for r in R_i)` and `f_max(level) = min(0.94, 0.82 + 0.03 * (level - 1))`; choose each ordinary beam weight so `0.50 * C_route,i <= W_i <= f_max(level) * C_route,i`. The third, right-side beam is the challenge beam. Choose its weight in 250 lb increments so `C(150) < W_risk <= f_max(level) * C_route,risk`. This guarantees that every level has a beam that is safe along its generated pickup-to-target route but exceeds crane capacity if carried to a sufficiently far radius. Generate all beam weights and locations so every pickup-to-target route remains below the 100% tip-over threshold.
## Outputs

Display these outputs in boxes that remain visible at the top of the screen during play:

- **Timer:** Time remaining in the current level’s three-minute limit.
- **Score:** Player’s current score.
- **High score:** Highest score achieved.
- **Level:** Current level out of five.
- **Radius:** Current load radius in feet.
- **Capacity:** Show the carried beam's weight as a percentage of the crane's interpolated capacity, along with the current maximum capacity in pounds.
- **Beam weights:** Show each beam’s weight on or next to that individual beam.
## Look and feel

Show the game in a 2D side view. The ground runs along the bottom of the screen, with a city skyline in the background. Place the unfinished steel tower in the middle, with one tower crane on each side.

The player operates the crane on the left. It has a long boom, a box-shaped trolley that moves along the boom, and a cable hanging from the trolley. Show three empty spaces between the tower’s steel beams as the beam placement targets.

The crane on the right is also in the foreground and clearly visible. It moves automatically, continuously placing its own beams. Those beams can sometimes get in the way of the player’s crane as the player places beams.

Use realistic graphics and colors with a medium level of detail. Show a worker wearing red clothing and a hardhat, carrying a hammer, as he walks on the unfinished tower. If a beam hits the worker, show the worker falling and immediately mark the level as failed.

Show black 2D birds flying in the sky. When a bird hits the cable, make the cable buckle and the load sway strongly.

When capacity reaches 90%, make the capacity percentage box at the top of the screen flash red.
## Validation

- 50 ft: capacity is 20,000 lb.
- 62.5 ft: halfway between 50 ft (20,000 lb) and 75 ft (13,000 lb), so capacity is 16,500 lb.
- 74.99 ft: interpolate between 50 ft and 75 ft, giving approximately 13,003 lb.
- 75.01 ft: interpolate between 75 ft and 100 ft, giving approximately 12,998 lb.
- 112 ft: interpolate between 100 ft and 125 ft, giving 8,040 lb; the 90% warning threshold is 7,236 lb.
- 150 ft: capacity is 5,500 lb. A 5,750 lb challenge beam exceeds capacity at 150 ft, but remains below the approximately 7,160 lb route capacity at a 123 ft target radius.
## Out of scope

- This is a simple game for fun, not a real crane simulator, operator training tool, or source of real-world safety guidance.
- Crane capacities and movement are simplified for gameplay and do not represent engineering calculations or certified load charts.
- The game is a 2D side view; 3D graphics and camera controls are not included.
- The game includes five levels; extra game modes and a level editor are not included.
- No accounts or online features; the high score is saved locally in the player's browser.
## Features

1. **Worker hazard:** A worker wearing red clothing, a hardhat, and carrying a hammer walks on the unfinished tower. The player must avoid hitting him with a beam. If a beam hits the worker, show him falling and immediately fail the level.
2. **Birds and load sway:** Black 2D birds occasionally fly across the sky and may hit the load cable. When a bird hits, the cable buckles and the beam swings wildly. The player cannot control or steady the load; it settles on its own.
## Implementation Plan

1. **Build the game scene and layout.** Create the 2D side view with the ground, city skyline, central unfinished tower, both cranes, three target spaces, and the top-of-screen output boxes.
2. **Make the player crane controllable.** Add arrow-key and WASD controls for crane and trolley movement, plus hook raising and lowering. Implement Space to pick up or release one beam at a time, with the trolley and hook movement limits.
3. **Add load capacity and beam generation.** Calculate radius and capacity continuously. Generate three beams and pickup and target locations per level so every beam can be moved along its full route without reaching the tip-over threshold. Add the 90% warning and crane collapse at 100%.
4. **Add the level objective and progression.** Make highlighted target spaces accept a released beam. Track the three placements, three-minute timer, score, and progress through five increasingly difficult levels.
5. **Add hazards and failure behavior.** Animate the other crane placing beams that can obstruct the player. Add the walking worker and level failure if a beam hits him. Add birds that can hit the cable and make the beam swing wildly.
6. **Add the high score and finish the presentation.** Save and display the high score locally in the browser. Refine the realistic, medium-detail visuals, animations, feedback, and screen layout.