import static org.junit.jupiter.api.Assertions.*;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Random;
import java.util.Set;
import org.junit.jupiter.api.Test;

class SpatialGridTest {

  /** The O(n^2) reference the grid must agree with. */
  private static Set<Boid> bruteForce(World w, List<Boid> all, Boid self, double r) {
    Set<Boid> out = new HashSet<>();
    for (Boid b : all) if (b != self && w.distance(self.position, b.position) <= r) out.add(b);
    return out;
  }

  private static void checkAgainstBruteForce(double width, double height, double radius, long seed) {
    World w = new World(width, height);
    Random rng = new Random(seed);
    List<Boid> boids = new ArrayList<>();
    for (int i = 0; i < 400; i++) {
      boids.add(new Boid(new Vec2(rng.nextDouble() * width, rng.nextDouble() * height), Vec2.ZERO));
    }
    SpatialGrid grid = new SpatialGrid(w, radius);
    grid.rebuild(boids);
    for (Boid b : boids) {
      List<Boid> found = grid.neighbours(b, radius);
      assertEquals(found.size(), new HashSet<>(found).size(), "no duplicates");
      assertEquals(bruteForce(w, boids, b, radius), new HashSet<>(found));
    }
  }

  @Test
  void matchesBruteForce() {
    checkAgainstBruteForce(800, 600, 50, 1);
  }

  @Test
  void matchesBruteForceWithNonDividingCellSize() {
    checkAgainstBruteForce(777, 333, 47.3, 2);
  }

  @Test
  void handlesTinyGridsWithoutDuplicates() {
    // radius large relative to world -> 1x1 and 2x2 grids
    checkAgainstBruteForce(100, 100, 60, 3);
    checkAgainstBruteForce(100, 100, 45, 4);
  }

  @Test
  void findsNeighboursAcrossTheWrap() {
    World w = new World(500, 500);
    Boid a = new Boid(new Vec2(2, 250), Vec2.ZERO);
    Boid b = new Boid(new Vec2(497, 250), Vec2.ZERO);
    SpatialGrid grid = new SpatialGrid(w, 50);
    grid.rebuild(List.of(a, b));
    assertEquals(List.of(b), grid.neighbours(a, 50));
  }
}
