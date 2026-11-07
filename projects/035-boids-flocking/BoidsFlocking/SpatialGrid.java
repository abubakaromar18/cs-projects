import java.util.ArrayList;
import java.util.List;

/**
 * Uniform-grid spatial hash for neighbour queries.
 *
 * Naively, every boid checks every other boid: O(n^2) per frame. Bucketing
 * boids into cells at least as wide as the perception radius means a boid
 * only needs to look at its own cell and the 8 around it, which is roughly
 * O(n) when boids are spread out. Cells wrap around like the world does.
 */
public class SpatialGrid {
  private final World world;
  private final int cols;
  private final int rows;
  private final double cellW;
  private final double cellH;
  private final List<List<Boid>> cells;

  public SpatialGrid(World world, double cellSize) {
    this.world = world;
    // At least 1 cell; cells are never narrower than cellSize so a 3x3 block
    // always covers the full perception radius.
    this.cols = Math.max(1, (int) Math.floor(world.width / cellSize));
    this.rows = Math.max(1, (int) Math.floor(world.height / cellSize));
    this.cellW = world.width / cols;
    this.cellH = world.height / rows;
    this.cells = new ArrayList<>(cols * rows);
    for (int i = 0; i < cols * rows; i++) cells.add(new ArrayList<>());
  }

  public int cols() { return cols; }
  public int rows() { return rows; }

  public void rebuild(List<Boid> boids) {
    for (List<Boid> c : cells) c.clear();
    for (Boid b : boids) cells.get(index(colOf(b.position.x), rowOf(b.position.y))).add(b);
  }

  /** All boids other than {@code self} within {@code radius} of it (wrapped). */
  public List<Boid> neighbours(Boid self, double radius) {
    List<Boid> out = new ArrayList<>();
    int c0 = colOf(self.position.x);
    int r0 = rowOf(self.position.y);
    // With fewer than 3 columns/rows the 3x3 block would visit a cell twice.
    int dcMax = Math.min(1, cols - 1);
    int drMax = Math.min(1, rows - 1);
    int dcMin = cols == 2 ? 0 : -dcMax;
    int drMin = rows == 2 ? 0 : -drMax;
    double r2 = radius * radius;
    for (int dr = drMin; dr <= drMax; dr++) {
      for (int dc = dcMin; dc <= dcMax; dc++) {
        int c = Math.floorMod(c0 + dc, cols);
        int r = Math.floorMod(r0 + dr, rows);
        for (Boid b : cells.get(index(c, r))) {
          if (b != self && world.offset(self.position, b.position).magSq() <= r2) out.add(b);
        }
      }
    }
    return out;
  }

  private int colOf(double x) { return Math.min(cols - 1, (int) (x / cellW)); }
  private int rowOf(double y) { return Math.min(rows - 1, (int) (y / cellH)); }
  private int index(int c, int r) { return r * cols + c; }
}
