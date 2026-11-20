## Purpose
A crane operation game where the player uses the left tower crane to place three steel pieces in their highlighted target locations on each of five increasingly difficult levels. Each level changes the tower layout and tightens the target spaces. The time limits are 2:00, 1:30, 1:00, 0:45, and 0:30. The player must manage the load's changing capacity as the crane reaches farther out. This is a simple game inspired by crane load charts, not a tool for real-world crane operation.
## Inputs

Use either the arrow keys or WASD. Left and right move the trolley along the player's crane boom; up and down raise and lower the hook. When the trolley reaches the mast center, continuing to press toward the other side slowly turns the player crane around the mast so the trolley can reach the opposite side. The trolley cannot travel past the boom's ends, and the hook can move from boom height to ground level. The crane and trolley move at a steady, moderate speed. Press Space to pick up a beam when the hook is close enough, or release a carried beam. Only one beam can be carried at a time. When the carried beam is over an unfilled highlighted target, pressing Space places it there automatically. Use the upper-left Pause button to freeze the game; press Resume to continue. Pausing freezes the timer, cranes, worker, birds, and load sway. The player cannot steady a swaying load.
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

If the player exceeds the load limit or the level timer expires, the player crane falls into the unfinished tower, then its boom and mast sections detach. The tower's columns, crossbeams, and braces also detach and fall as separate steel members. The red-clothed worker falls from the tower and bounces on the ground during either failure scene. After an overload, show a Level Failed screen with a Restart Level button. After a timeout, show a Level Failed screen with a Restart Game button that returns to level 1 and resets the score to zero.

### Beam generation and route feasibility

At the start of each level, generate three beams, each with a weight `W_i`, a pickup radius `r_p,i`, and a target radius `r_t,i`, where `i` is 1, 2, or 3. Spawn one beam well to the left of the tower and the other two to the right. Keep the challenge beam on the right so the player can carry it to the full 150 ft radius. Randomize pickup positions within the left and right boom areas while keeping all three positions reachable.

For each beam, check capacity at pickup and continuously along the trolley�s route to its target. Let `R_i` be the set of radii the beam passes through while being carried. The beam is feasible only if:

```text
W_i / C(r) < 1 for every r in R_i
```

Equivalently:

```text
W_i < min(C(r) for r in R_i)
```

Make each beam heavier on every successive level. For beam 1, use `3,250 + 500 * (level - 1)` lb plus a random 0 or 250 lb; for beam 2, use `4,250 + 500 * (level - 1)` lb plus a random 0 or 250 lb. The right-side challenge beam weighs `5,750 + 250 * (level - 1)` lb. Keep every generated weight below the minimum capacity along its pickup-to-target route. This preserves safe placement while making the later levels progressively harder and leaving the challenge beam above the crane's 150 ft capacity.
## Outputs

Display these outputs in separate, compact boxes along the bottom of the scene over the ground beneath the cranes and tower:

- **Timer:** Time remaining in the current level's limit: 2:00, 1:30, 1:00, 0:45, or 0:30 depending on the level.
- **Score:** Player’s current score.
- **High score:** Highest score achieved, saved locally in the current browser and retained between visits.
- **Level:** Current level out of five.
- **Radius:** Current load radius in feet.
- **Capacity:** Show the carried beam's weight as a percentage of the crane's interpolated capacity, along with the current maximum capacity in pounds.
- **Beam weights:** Show each beam’s weight on or next to that individual beam.
## Level progression and scoring

Show a start screen and begin the first level only after the player clicks Start Game. Set level time limits to 2:00, 1:30, 1:00, 0:45, and 0:30. Placing all three beams completes the level and starts the next one, with a total of five levels. Increase beam weights at every level, change the tower's bay spacing and target positions, and make the target openings narrower each level. If time reaches zero before all three beams are placed, play the crane and tower collapse scene, make the worker fall and bounce on the ground, then show a Level Failed screen with a Restart Game button. Restarting after a timeout returns to level 1 and resets the score to zero. Completing level five ends the game with a completion screen.

Award 100 points for each beam placed and a 200-point bonus for completing a level. Keep the score across levels and display the current level and number of beams remaining.

Whenever the current score exceeds the saved high score, store the new record in browser local storage and briefly highlight the high-score box. Flash the timer box during the final 10 seconds of a level.

If the player's hook or carried beam hits the walking worker or the automatic crane's moving beam, subtract 10 points and briefly show a large red “-10” on screen. These collisions do not stop the level. The score may drop below zero.
## Look and feel

Show the game in a 2D side view. The ground runs along the bottom of the screen, with a city skyline in the background. Place the unfinished steel tower in the middle, with one tower crane on each side. Change the tower's bay spacing, target positions, and target widths on each level while keeping the tower within the cranes' reach.

The player operates the crane on the left. It has a long boom, a box-shaped trolley that moves along the boom, and a cable hanging from the trolley. Show three empty spaces between the tower’s steel beams as the beam placement targets.

The crane on the right is also in the foreground and clearly visible. It moves automatically, continuously placing its own beams. Those beams can sometimes get in the way of the player’s crane as the player places beams.

Use realistic graphics and colors with a medium level of detail. Show a worker wearing red clothing and a hardhat, carrying a hammer, as he walks on the unfinished tower. If the player's hook or beam hits the worker or the automatic crane's moving beam, subtract 10 points and show a large red “-10” popup without stopping the level. The worker falls from the tower and bounces on the ground when the crane overloads or time expires.

Show black 2D birds flying across the sky at varying altitudes. When a bird hits the cable, make the cable and hook sway strongly whether or not a beam is attached; an attached beam sways with them.

When capacity reaches 90%, make the capacity percentage box flash red. Make the timer box flash red during the final 10 seconds of a level and briefly highlight the high-score box when a new record is set.
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

1. **Worker hazard:** A worker wearing red clothing, a hardhat, and carrying a hammer walks along the unfinished tower. If the player's hook or carried beam hits him, subtract 10 points and show a large red “-10” popup without ending the level. Timeout and overload failures still make him fall and bounce on the ground.
2. **Birds and load sway:** Black 2D birds occasionally fly across the sky at varying altitudes and may hit the load cable. When a bird hits, the cable buckles and the hook sways wildly, even when no beam is attached. Any carried beam swings with the hook. The player cannot control or steady the load; it settles on its own.
## Implementation Plan

1. **Build the game scene and layout.** Create the 2D side view with the ground, city skyline, central unfinished tower, both cranes, three target spaces, and compact output boxes along the bottom of the scene.
2. **Make the player crane controllable.** Add arrow-key and WASD controls for crane and trolley movement, plus hook raising and lowering. Implement Space to pick up or release one beam at a time, with the trolley and hook movement limits.
3. **Add load capacity and beam generation.** Calculate radius and capacity continuously. Generate three beams and pickup and target locations per level so every beam can be moved along its full route without reaching the tip-over threshold. Add the 90% warning and crane collapse at 100%.
4. **Add the level objective and progression.** Make highlighted target spaces accept a released beam. Track the three placements, level timers of 2:00, 1:30, 1:00, 0:45, and 0:30, score, and progress through five increasingly difficult levels with a new tower layout and narrower target spaces at each level.
5. **Add hazards and failure behavior.** Animate the automatic crane moving its trolley and placing beams at the lower, middle, and upper parts of the tower so its load sometimes blocks a player target until it moves clear. Animate the red worker walking on the tower. If the player's hook or beam collides with the worker or the automatic crane's moving beam, subtract 10 points and show a large red “-10” popup without stopping the level. Fly birds across the scene at varying altitudes; a bird strike makes the cable and hook sway wildly whether or not a beam is attached, and any carried beam swings until it settles.
6. **Add the high score and finish the presentation.** Save and display the high score locally in the browser. Refine the realistic, medium-detail visuals, animations, feedback, and screen layout.
