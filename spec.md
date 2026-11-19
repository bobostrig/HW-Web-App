## Purpose
A crane operation game where the player uses the left tower crane to place three steel pieces in their highlighted target locations on each of five increasingly difficult levels. Each level has a three-minute time limit. The player must manage the load's changing capacity as the crane reaches farther out. This is a simple game inspired by crane load charts, not a tool for real-world crane operation.
## Inputs
Turn the crane to left and right. move the trolleyin and out and raise and lower the hook

## Calculations
Radius (ft)	Capacity (lb)
50ft-20,000
75ft-13,000
100ft-9,000
125ft-7,000
150ft-5,500
warning when load reaches 90% capacity
dramitic tip ovr when road reaches 100%

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
