/**
 * A rectangular toroidal world: leaving the right edge brings you back on
 * the left. Distances must therefore take the shortest wrapped path, or
 * boids on opposite edges would ignore each other despite being adjacent.
 */
public class World {
  public final double width;
  public final double height;

  public World(double width, double height) {
    if (width <= 0 || height <= 0) throw new IllegalArgumentException("world must have positive size");
    this.width = width;
    this.height = height;
  }

  /** Map any position into [0, width) x [0, height). */
  public Vec2 wrap(Vec2 v) {
    return new Vec2(mod(v.x, width), mod(v.y, height));
  }

  /** Shortest vector from a to b on the torus. */
  public Vec2 offset(Vec2 a, Vec2 b) {
    return new Vec2(shortest(b.x - a.x, width), shortest(b.y - a.y, height));
  }

  public double distance(Vec2 a, Vec2 b) {
    return offset(a, b).mag();
  }

  private static double mod(double v, double m) {
    double r = v % m;
    return r < 0 ? r + m : r;
  }

  private static double shortest(double d, double size) {
    d = mod(d, size);
    return d > size / 2 ? d - size : d;
  }
}
