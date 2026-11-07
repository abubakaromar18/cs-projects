# 035 · Boids Flocking

A Processing sketch of Craig Reynolds' **boids** (1986): a few hundred agents that each follow
three local rules, and together move like a flock of birds or a school of fish. Nobody leads
and nothing is scripted. The flocking *emerges*.

| Rule | What a boid does |
|------|------------------|
| **Separation** | steers away from neighbours that are too close |
| **Alignment** | steers towards the average heading of nearby boids |
| **Cohesion** | steers towards the centre of mass of nearby boids |

Boids are coloured by heading, so groups that have lined up show as one colour.

## CS concepts

- **Emergent behaviour / agent-based modelling.** Global order comes from purely local rules.
- **Steering behaviours.** `steer = desired − velocity`, clamped to a max force, gives smooth,
  momentum-like turns instead of instant snapping (`Boid.steerTowards`).
- **Spatial hashing.** A uniform grid with cells ≥ the perception radius cuts neighbour search
  from O(n²) to about O(n). Each boid scans only its own cell and the 8 around it
  (`SpatialGrid`). Tests check it against a brute-force search.
- **Toroidal geometry.** The world wraps at the edges, so distances use the shortest wrapped
  offset (`World.offset`). Boids on opposite edges are neighbours.
- **Synchronous updates.** All accelerations are computed from one snapshot before anyone
  moves, so the result doesn't depend on list order.
- **Numerical integration.** Explicit Euler with a speed cap.
- **Order parameter.** *Polarization* = length of the mean unit heading, from 0 (disordered)
  to 1 (everyone aligned). A standard measure from collective-motion physics.

## Layout

```
BoidsFlocking/            ← the Processing sketch folder (open this in the IDE)
  BoidsFlocking.pde       drawing, HUD, mouse and keyboard input
  Flock.java              simulation loop, spawning, polarization
  Boid.java               the three rules + integration
  SpatialGrid.java        uniform-grid neighbour queries (with wrap-around)
  World.java              toroidal bounds and shortest-path offsets
  FlockParams.java        tunable radii, speeds, weights, rule toggles
  Vec2.java               immutable 2D vector
test/                     JUnit 5 tests for the simulation core
pom.xml                   Maven build for the tests
Makefile
```

The simulation lives in plain `.java` tabs with no Processing imports. Processing compiles them
along with the sketch, and they also build with plain `javac`/Maven, so they can be unit
tested. The `.pde` file only draws.

## Run

**Processing IDE (4.x):** open `BoidsFlocking/BoidsFlocking.pde` and press ▶.

**Command line:** with `processing-java` on your `PATH` (IDE menu *Tools → Install
"processing-java"*):

```bash
make run        # or: processing-java --sketch=$PWD/BoidsFlocking --run
make export     # standalone app in ./out
```

### Controls

| Input | Action |
|-------|--------|
| click / drag | add boids |
| `1` `2` `3` | toggle separation / alignment / cohesion |
| `[` `]` | shrink / grow perception radius |
| `-` `=` | lower / raise max speed |
| `g` | show the spatial-hash grid |
| `t` | motion trails |
| `space` | pause |
| `r` | reset |

Things to try: turn off separation (`1`) and the flock collapses into tight clumps. Turn off
alignment (`2`) and you get a buzzing swarm with no shared direction. Turn off cohesion (`3`)
and flocks drift apart and never re-form.

## Test

```bash
make test       # or: mvn test   (JDK 17+, Maven 3.8+)
```

19 tests cover:

- vector maths
- toroidal wrapping and shortest-path offsets
- the spatial grid against brute force, including non-dividing cell sizes, 1×1 and 2×2
  grids (no duplicates), and neighbours across the wrap
- each rule in isolation: separation pushes apart, cohesion pulls together, alignment turns
  towards the neighbours' heading
- the steering-force bound
- straight-line motion with all rules off
- speed and bounds invariants over 500 steps
- polarization rising from disorder (< 0.3) to order (> 0.7)
- seeded determinism
- changing the perception radius live

> **Note:** this project was built in a sandbox that couldn't reach Maven Central or install
> Processing. There, the core and the tests were compiled with `javac --release 17` and run
> against a minimal stand-in for the JUnit 5 API: all 19 tests passed. On a normal machine,
> `mvn test` runs them with real JUnit 5. The `.pde` sketch wasn't run in the sandbox.

## Example: order emerging

180 boids in a 1000×700 world with the default parameters (seed 1):

```
step    0  polarization 0.06
step  200  polarization 0.57
step  400  polarization 0.79
step  600  polarization 0.92
step  800  polarization 0.97
step 1000  polarization 0.96
```

## Possible extensions

- **Predators and obstacles:** a flee rule for predators, plus obstacle avoidance by ray-casting ahead
- **Field of view:** ignore neighbours behind the boid (a blind-spot cone)
- **3D boids** with `P3D` and a camera orbit
- **On-screen sliders** for the weights, e.g. with the ControlP5 library
- **Plotting:** polarization and clustering over time, sweeping noise to show the order/disorder
  phase transition (the Vicsek model)
- **Better integration:** semi-implicit Euler or a fixed-timestep loop independent of frame rate
- **Better spatial structures:** compare the uniform grid with a quadtree or k-d tree on
  clustered data
