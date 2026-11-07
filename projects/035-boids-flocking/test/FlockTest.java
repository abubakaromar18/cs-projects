import static org.junit.jupiter.api.Assertions.*;

import java.util.List;
import org.junit.jupiter.api.Test;

class FlockTest {

  private static FlockParams only(boolean sep, boolean ali, boolean coh) {
    FlockParams p = new FlockParams();
    p.separationOn = sep;
    p.alignmentOn = ali;
    p.cohesionOn = coh;
    return p;
  }

  @Test
  void separationPushesCloseBoidsApart() {
    Flock f = new Flock(new World(400, 400), only(true, false, false), 0);
    Boid a = f.add(new Boid(new Vec2(200, 200), Vec2.ZERO));
    Boid b = f.add(new Boid(new Vec2(205, 200), Vec2.ZERO));
    double before = f.world.distance(a.position, b.position);
    for (int i = 0; i < 20; i++) f.step();
    assertTrue(f.world.distance(a.position, b.position) > before);
    assertTrue(a.velocity.x < 0 && b.velocity.x > 0, "they move in opposite directions");
  }

  @Test
  void cohesionPullsBoidsTogether() {
    Flock f = new Flock(new World(400, 400), only(false, false, true), 0);
    Boid a = f.add(new Boid(new Vec2(180, 200), Vec2.ZERO));
    Boid b = f.add(new Boid(new Vec2(220, 200), Vec2.ZERO));
    for (int i = 0; i < 10; i++) f.step();
    assertTrue(f.world.distance(a.position, b.position) < 40);
  }

  @Test
  void alignmentTurnsBoidTowardsNeighbourHeading() {
    FlockParams p = only(false, true, false);
    Flock f = new Flock(new World(400, 400), p, 0);
    Boid lone = f.add(new Boid(new Vec2(200, 200), new Vec2(0, 1)));
    for (int i = 0; i < 4; i++) f.add(new Boid(new Vec2(190 + 5 * i, 215), new Vec2(p.maxSpeed, 0)));
    double before = lone.velocity.normalize().dot(new Vec2(1, 0));
    f.step();
    assertTrue(lone.velocity.normalize().dot(new Vec2(1, 0)) > before);
  }

  @Test
  void steeringForceIsBounded() {
    FlockParams p = new FlockParams();
    Boid b = new Boid(new Vec2(0, 0), new Vec2(-p.maxSpeed, 0));
    Vec2 steer = Boid.steerTowards(new Vec2(1, 0), b.velocity, p);
    assertEquals(p.maxForce, steer.mag(), 1e-9);
  }

  @Test
  void withNoRulesBoidsFlyStraight() {
    Flock f = new Flock(new World(1000, 1000), only(false, false, false), 0);
    Boid a = f.add(new Boid(new Vec2(100, 100), new Vec2(1, 0.5)));
    f.add(new Boid(new Vec2(101, 101), new Vec2(-1, 0)));
    for (int i = 0; i < 10; i++) f.step();
    assertTrue(a.position.approx(new Vec2(110, 105), 1e-9));
  }

  @Test
  void invariantsHoldOverLongRun() {
    Flock f = new Flock(new World(600, 400), new FlockParams(), 42);
    f.spawnRandom(150);
    for (int i = 0; i < 500; i++) {
      f.step();
      for (Boid b : f.boids()) {
        assertTrue(b.velocity.mag() <= f.params.maxSpeed + 1e-9, "speed limit");
        assertTrue(b.position.x >= 0 && b.position.x < 600 && b.position.y >= 0 && b.position.y < 400);
      }
    }
  }

  @Test
  void flockingIncreasesPolarization() {
    Flock f = new Flock(new World(300, 300), new FlockParams(), 7);
    f.spawnRandom(120);
    double start = f.polarization();
    for (int i = 0; i < 600; i++) f.step();
    assertTrue(start < 0.3, "random headings start disordered: " + start);
    assertTrue(f.polarization() > 0.7, "alignment emerges: " + f.polarization());
  }

  @Test
  void sameSeedIsDeterministic() {
    List<Boid> a = run(99), b = run(99);
    for (int i = 0; i < a.size(); i++) assertTrue(a.get(i).position.approx(b.get(i).position, 0));
  }

  private static List<Boid> run(long seed) {
    Flock f = new Flock(new World(500, 500), new FlockParams(), seed);
    f.spawnRandom(60);
    for (int i = 0; i < 100; i++) f.step();
    return f.boids();
  }

  @Test
  void changingPerceptionRadiusLiveStillWorks() {
    Flock f = new Flock(new World(500, 500), new FlockParams(), 3);
    f.spawnRandom(50);
    f.step();
    f.params.perceptionRadius = 150;
    f.step();
    assertEquals(3, f.grid().cols());
  }
}
