import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

class WorldTest {
  private final World world = new World(100, 50);

  @Test
  void wrapsIntoBounds() {
    assertTrue(world.wrap(new Vec2(105, -5)).approx(new Vec2(5, 45), 1e-9));
    assertTrue(world.wrap(new Vec2(-250, 120)).approx(new Vec2(50, 20), 1e-9));
  }

  @Test
  void offsetTakesShortestPathAcrossEdges() {
    // 2 and 98 are 4 apart through the edge, not 96 across the middle.
    Vec2 off = world.offset(new Vec2(98, 10), new Vec2(2, 10));
    assertTrue(off.approx(new Vec2(4, 0), 1e-9), off.toString());
    assertEquals(4, world.distance(new Vec2(2, 1), new Vec2(98, 1)), 1e-9);
    assertEquals(6, world.distance(new Vec2(10, 47), new Vec2(10, 3)), 1e-9);
  }

  @Test
  void rejectsEmptyWorld() {
    assertThrows(IllegalArgumentException.class, () -> new World(0, 10));
  }
}
