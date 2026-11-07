import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

class Vec2Test {
  private static final double EPS = 1e-9;

  @Test
  void arithmetic() {
    Vec2 a = new Vec2(1, 2), b = new Vec2(3, -4);
    assertTrue(a.add(b).approx(new Vec2(4, -2), EPS));
    assertTrue(a.sub(b).approx(new Vec2(-2, 6), EPS));
    assertTrue(a.mult(3).approx(new Vec2(3, 6), EPS));
    assertEquals(-5, a.dot(b), EPS);
    assertEquals(5, b.mag(), EPS);
  }

  @Test
  void normalizeAndLimit() {
    assertEquals(1, new Vec2(3, 4).normalize().mag(), EPS);
    assertSame(Vec2.ZERO, Vec2.ZERO.normalize());
    assertEquals(2, new Vec2(30, 40).limit(2).mag(), EPS);
    Vec2 small = new Vec2(0.1, 0.1);
    assertSame(small, small.limit(2), "short vectors are untouched");
  }

  @Test
  void headingRoundTrips() {
    double theta = 1.234;
    assertEquals(theta, Vec2.fromAngle(theta).heading(), EPS);
  }
}
