/**
 * Boids Flocking — Craig Reynolds' 1986 model, in Processing.
 *
 * Each boid follows three local rules:
 *   separation  steer away from neighbours that are too close
 *   alignment   steer towards the neighbours' average heading
 *   cohesion    steer towards the neighbours' centre of mass
 *
 * The simulation itself lives in the plain-Java tabs (Flock, Boid, ...),
 * so this file only draws and handles input.
 *
 * Controls:
 *   click / drag   add boids          1 / 2 / 3   toggle sep / align / coh
 *   space          pause              g           show spatial grid
 *   r              reset              t           toggle trails
 *   [ / ]          perception radius  - / =       max speed
 */

final int INITIAL_BOIDS = 180;
final float BOID_SIZE = 6;

Flock flock;
boolean paused = false;
boolean showGrid = false;
boolean trails = false;

void setup() {
  size(1000, 700);
  pixelDensity(displayDensity());
  smooth(4);
  reset();
}

void reset() {
  flock = new Flock(new World(width, height), new FlockParams(), millis());
  flock.spawnRandom(INITIAL_BOIDS);
}

void draw() {
  if (trails) {
    noStroke();
    fill(14, 18, 28, 40);
    rect(0, 0, width, height);
  } else {
    background(14, 18, 28);
  }

  if (!paused) flock.step();
  if (showGrid) drawGrid();

  for (Boid b : flock.boids()) drawBoid(b);
  drawHud();
}

void drawBoid(Boid b) {
  // Hue encodes heading, so aligned sub-flocks show up as same-coloured groups.
  colorMode(HSB, TWO_PI, 1, 1);
  float h = (float) (b.velocity.heading() + PI);
  fill(h, 0.55, 1);
  colorMode(RGB, 255);
  noStroke();
  pushMatrix();
  translate((float) b.position.x, (float) b.position.y);
  rotate((float) b.velocity.heading());
  triangle(BOID_SIZE * 1.6, 0, -BOID_SIZE, BOID_SIZE * 0.8, -BOID_SIZE, -BOID_SIZE * 0.8);
  popMatrix();
}

void drawGrid() {
  stroke(255, 30);
  float cw = width / (float) flock.grid().cols();
  float ch = height / (float) flock.grid().rows();
  for (int c = 1; c < flock.grid().cols(); c++) line(c * cw, 0, c * cw, height);
  for (int r = 1; r < flock.grid().rows(); r++) line(0, r * ch, width, r * ch);
}

void drawHud() {
  FlockParams p = flock.params;
  fill(0, 160);
  noStroke();
  rect(8, 8, 250, 112, 6);
  fill(230);
  textSize(12);
  int y = 26;
  text("boids: " + flock.size() + "   fps: " + round(frameRate), 18, y); y += 16;
  text("[1] separation " + onOff(p.separationOn), 18, y); y += 16;
  text("[2] alignment  " + onOff(p.alignmentOn), 18, y); y += 16;
  text("[3] cohesion   " + onOff(p.cohesionOn), 18, y); y += 16;
  text("radius " + nf((float) p.perceptionRadius, 0, 0) + "   speed " + nf((float) p.maxSpeed, 0, 1), 18, y); y += 16;
  text("polarization " + nf((float) flock.polarization(), 0, 2) + (paused ? "   PAUSED" : ""), 18, y);
}

String onOff(boolean b) { return b ? "on" : "off"; }

void mousePressed() { flock.spawn(new Vec2(mouseX, mouseY)); }
void mouseDragged() { if (frameCount % 2 == 0) flock.spawn(new Vec2(mouseX, mouseY)); }

void keyPressed() {
  FlockParams p = flock.params;
  switch (key) {
    case '1': p.separationOn = !p.separationOn; break;
    case '2': p.alignmentOn = !p.alignmentOn; break;
    case '3': p.cohesionOn = !p.cohesionOn; break;
    case ' ': paused = !paused; break;
    case 'g': showGrid = !showGrid; break;
    case 't': trails = !trails; break;
    case 'r': reset(); break;
    case '[': p.perceptionRadius = max(10, (float) p.perceptionRadius - 5); break;
    case ']': p.perceptionRadius = min(200, (float) p.perceptionRadius + 5); break;
    case '-': p.maxSpeed = max(0.5, (float) p.maxSpeed - 0.5); break;
    case '=': p.maxSpeed = min(10, (float) p.maxSpeed + 0.5); break;
  }
}
