/**
 * An immutable 2D vector.
 *
 * Processing ships its own PVector, but keeping the simulation core free of
 * any Processing dependency lets it compile with plain javac and be unit
 * tested. Immutability keeps the steering maths free of aliasing bugs:
 * no method ever changes a vector another boid is still reading.
 */
public final class Vec2 {
  public static final Vec2 ZERO = new Vec2(0, 0);

  public final double x;
  public final double y;

  public Vec2(double x, double y) {
    this.x = x;
    this.y = y;
  }

  /** A unit vector pointing at the given angle (radians). */
  public static Vec2 fromAngle(double theta) {
    return new Vec2(Math.cos(theta), Math.sin(theta));
  }

  public Vec2 add(Vec2 o)        { return new Vec2(x + o.x, y + o.y); }
  public Vec2 sub(Vec2 o)        { return new Vec2(x - o.x, y - o.y); }
  public Vec2 mult(double s)     { return new Vec2(x * s, y * s); }
  public Vec2 div(double s)      { return new Vec2(x / s, y / s); }
  public double dot(Vec2 o)      { return x * o.x + y * o.y; }
  public double magSq()          { return x * x + y * y; }
  public double mag()            { return Math.sqrt(magSq()); }
  public double heading()        { return Math.atan2(y, x); }

  /** Unit vector in the same direction; the zero vector stays zero. */
  public Vec2 normalize() {
    double m = mag();
    return m == 0 ? ZERO : div(m);
  }

  /** Same direction, scaled to length {@code len}. */
  public Vec2 withMag(double len) {
    return normalize().mult(len);
  }

  /** Clamp the length to at most {@code max}, keeping the direction. */
  public Vec2 limit(double max) {
    double m2 = magSq();
    return m2 > max * max ? withMag(max) : this;
  }

  public boolean approx(Vec2 o, double eps) {
    return Math.abs(x - o.x) <= eps && Math.abs(y - o.y) <= eps;
  }

  @Override
  public String toString() {
    return String.format("(%.3f, %.3f)", x, y);
  }
}
