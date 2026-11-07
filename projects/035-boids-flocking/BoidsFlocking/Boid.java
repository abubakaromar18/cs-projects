/**
 * A single agent. A boid has no global knowledge: everything it does is a
 * reaction to the neighbours it can see. Flocking emerges from that.
 */
public class Boid {
  public Vec2 position;
  public Vec2 velocity;

  public Boid(Vec2 position, Vec2 velocity) {
    this.position = position;
    this.velocity = velocity;
  }

  /**
   * Reynolds-style steering: turn a desired direction into a bounded force.
   * desired = direction at full speed; steer = desired - current velocity.
   * Clamping the force is what gives boids smooth, momentum-like turns.
   */
  static Vec2 steerTowards(Vec2 direction, Vec2 velocity, FlockParams p) {
    if (direction.magSq() == 0) return Vec2.ZERO;
    Vec2 desired = direction.withMag(p.maxSpeed);
    return desired.sub(velocity).limit(p.maxForce);
  }

  /**
   * Compute this boid's acceleration from its neighbours.
   *
   * @param neighbours boids within the perception radius (excluding this one)
   * @param world      used for wrap-around (toroidal) offsets
   */
  public Vec2 computeAcceleration(Iterable<Boid> neighbours, World world, FlockParams p) {
    Vec2 separation = Vec2.ZERO;
    Vec2 velocitySum = Vec2.ZERO;
    Vec2 offsetSum = Vec2.ZERO;
    int seen = 0;
    int tooClose = 0;

    for (Boid other : neighbours) {
      // Offset from me to the other boid along the shortest wrapped path.
      Vec2 offset = world.offset(position, other.position);
      double d = offset.mag();
      if (d == 0 || d > p.perceptionRadius) continue;
      seen++;
      velocitySum = velocitySum.add(other.velocity);
      offsetSum = offsetSum.add(offset);
      if (d < p.separationRadius) {
        // Push away, weighted by 1/d so the closest neighbours dominate.
        separation = separation.sub(offset.normalize().div(d));
        tooClose++;
      }
    }

    Vec2 acc = Vec2.ZERO;
    if (p.separationOn && tooClose > 0) {
      acc = acc.add(steerTowards(separation, velocity, p).mult(p.separationWeight));
    }
    if (seen > 0) {
      if (p.alignmentOn) {
        // Match the average heading of the neighbours.
        acc = acc.add(steerTowards(velocitySum.div(seen), velocity, p).mult(p.alignmentWeight));
      }
      if (p.cohesionOn) {
        // Head for the neighbours' centre of mass (as a relative offset).
        acc = acc.add(steerTowards(offsetSum.div(seen), velocity, p).mult(p.cohesionWeight));
      }
    }
    return acc;
  }

  /** Euler integration step, then wrap the position back into the world. */
  public void integrate(Vec2 acceleration, World world, FlockParams p) {
    velocity = velocity.add(acceleration).limit(p.maxSpeed);
    position = world.wrap(position.add(velocity));
  }
}
