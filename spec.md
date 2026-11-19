## Purpose
A crane operation game where the player uses the left tower crane to place three steel pieces in their highlighted target locations on each of five increasingly difficult levels. Each level has a three-minute time limit. The player must manage the load's changing capacity as the crane reaches farther out. This is a simple game inspired by crane load charts, not a tool for real-world crane operation.
## Inputs

Use either the arrow keys or WASD to move the crane controls. Move the crane left and right, move the trolley along the boom, and raise or lower the hook. The trolley cannot travel past the boom's ends, and the hook can move from ground level up to the boom. The crane moves at a steady, moderate speed. Press Space to pick up a beam when the hook is positioned to do so, or to release a carried beam. Only one beam can be carried at a time. When a target location is highlighted, releasing the beam with Space places it there automatically. The player cannot steady a swaying load.
## Calculations

### Crane capacity by load radius

Measure load radius horizontally from the crane�s center of rotation to the beam. Let `r` be the radius in feet, and let `C(r)` be the maximum permitted beam weight in pounds.

| Load radius | Maximum beam weight |
|---:|---:|
| 0�50 ft | 20,000 lb |
| Over 50�75 ft | 13,000 lb |
| Over 75�100 ft | 9,000 lb |
| Over 100�125 ft | 7,000 lb |
| Over 125�150 ft | 5,500 lb |

Use the next larger listed distance�s capacity for radii between chart values. For example, `C(112) = 7,000 lb`.

```text
C(r) =
  20,000 lb, if 0 <= r <= 50
  13,000 lb, if 50 < r <= 75
   9,000 lb, if 75 < r <= 100
   7,000 lb, if 100 < r <= 125
   5,500 lb, if 125 < r <= 150
```

Update the radius and capacity continuously as the trolley moves. Only the beam�s weight counts; the cable�s weight is excluded.

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

the crane falls over dramatically, crashes into the tower being built, and the tower collapses.

### Beam generation and route feasibility

At the start of each level, generate three beams, each with a weight `W_i`, a pickup radius `r_p,i`, and a target radius `r_t,i`, where `i` is 1, 2, or 3.

For each beam, check capacity at pickup and continuously along the trolley�s route to its target. Let `R_i` be the set of radii the beam passes through while being carried. The beam is feasible only if:

```text
W_i / C(r) < 1 for every r in R_i
```

Equivalently:

```text
W_i < min(C(r) for r in R_i)
```

Generate beam weights and locations so this condition holds for all three beams. This keeps each generated task below the 100% tip-over threshold.
## Outputs
3 miute timer
score
capacity in %

## Look and feel
tower crane to be operated on left with loads to the left of the tower crane and uncompleted steel tower to put loads in designated locations. Tower crane on the right side of the tower also placing loads that the operated crane can't hit

## Validation
74.99 ft: the next radius ≥ 74.99 is 75, so the capacity is 13,000 and 0.9 × 13,000 = 11,700.
75.01 ft: 75 < 75.01, so the next row is 100 ft, giving 9,000 and 0.9 × 9,000 = 8,100.
112 ft: the next row is 125 ft, giving 7,000 and 0.9 × 7,000 = 6,300.
Interpolation at 112 ft: 9,000 + (12/25) × (7,000 − 9,000) = 9,000 − 960 = 8,040.

## Out of scope
Not for communication just for fun and simple. Not for real world use

## Features
1. There will be a guy walking on the uncompleted tower in red that you can't hit
2. There will be birds flying in the sky that when they hit the cable holding the load it sways a lot



