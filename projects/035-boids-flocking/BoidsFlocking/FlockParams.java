/**
 * Tunable constants for the three Reynolds rules.
 *
 * Fields are public and mutable on purpose: the sketch tweaks them live from
 * the keyboard, and tests build exactly the configuration they need.
 */
public class FlockParams {
  /** Radius within which a boid "sees" neighbours for alignment and cohesion. */
  public double perceptionRadius = 50;
  /** Smaller radius inside which neighbours are too close and get pushed away. */
  public double separationRadius = 24;
  /** Top speed, in pixels per step. */
  public double maxSpeed = 3.5;
  /** Maximum steering force a single rule may apply per step. */
  public double maxForce = 0.08;

  public double separationWeight = 1.6;
  public double alignmentWeight = 1.0;
  public double cohesionWeight = 0.9;

  public boolean separationOn = true;
  public boolean alignmentOn = true;
  public boolean cohesionOn = true;

  public FlockParams copy() {
    FlockParams p = new FlockParams();
    p.perceptionRadius = perceptionRadius;
    p.separationRadius = separationRadius;
    p.maxSpeed = maxSpeed;
    p.maxForce = maxForce;
    p.separationWeight = separationWeight;
    p.alignmentWeight = alignmentWeight;
    p.cohesionWeight = cohesionWeight;
    p.separationOn = separationOn;
    p.alignmentOn = alignmentOn;
    p.cohesionOn = cohesionOn;
    return p;
  }
}
