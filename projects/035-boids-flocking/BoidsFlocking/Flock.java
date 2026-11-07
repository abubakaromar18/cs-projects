import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

/**
 * The whole simulation: a world, its boids, and a step function.
 *
 * Updates are synchronous. Every boid's acceleration is computed from the
 * same snapshot before anyone moves, so the result doesn't depend on the
 * order boids happen to be stored in.
 */
public class Flock {
  public final World world;
  public final FlockParams params;
  private final List<Boid> boids = new ArrayList<>();
  private final Random rng;
  private SpatialGrid grid;

  public Flock(World world, FlockParams params, long seed) {
    this.world = world;
    this.params = params;
    this.rng = new Random(seed);
    this.grid = new SpatialGrid(world, params.perceptionRadius);
  }

  public List<Boid> boids() { return Collections.unmodifiableList(boids); }
  public int size() { return boids.size(); }
  public SpatialGrid grid() { return grid; }

  public Boid add(Boid b) {
    b.position = world.wrap(b.position);
    boids.add(b);
    return b;
  }

  /** Add a boid at {@code pos} heading in a random direction. */
  public Boid spawn(Vec2 pos) {
    double speed = params.maxSpeed * (0.5 + 0.5 * rng.nextDouble());
    return add(new Boid(pos, Vec2.fromAngle(rng.nextDouble() * 2 * Math.PI).mult(speed)));
  }

  /** Add {@code n} boids at random positions. */
  public void spawnRandom(int n) {
    for (int i = 0; i < n; i++) {
      spawn(new Vec2(rng.nextDouble() * world.width, rng.nextDouble() * world.height));
    }
  }

  public void clear() { boids.clear(); }

  /** Rebuild the grid if the perception radius has been changed live. */
  private void ensureGrid() {
    int wantCols = Math.max(1, (int) Math.floor(world.width / params.perceptionRadius));
    int wantRows = Math.max(1, (int) Math.floor(world.height / params.perceptionRadius));
    if (grid.cols() != wantCols || grid.rows() != wantRows) {
      grid = new SpatialGrid(world, params.perceptionRadius);
    }
  }

  /** Advance the simulation by one tick. */
  public void step() {
    ensureGrid();
    grid.rebuild(boids);
    Vec2[] acc = new Vec2[boids.size()];
    for (int i = 0; i < boids.size(); i++) {
      Boid b = boids.get(i);
      acc[i] = b.computeAcceleration(grid.neighbours(b, params.perceptionRadius), world, params);
    }
    for (int i = 0; i < boids.size(); i++) {
      boids.get(i).integrate(acc[i], world, params);
    }
  }

  /**
   * Order parameter in [0, 1]: length of the mean unit heading.
   * Near 0 = everyone pointing different ways; 1 = perfectly aligned.
   * A standard way to measure how "flocky" a swarm is.
   */
  public double polarization() {
    if (boids.isEmpty()) return 0;
    Vec2 sum = Vec2.ZERO;
    for (Boid b : boids) sum = sum.add(b.velocity.normalize());
    return sum.mag() / boids.size();
  }
}
