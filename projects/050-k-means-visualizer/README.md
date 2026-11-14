# 050 · K-Means Visualizer

An interactive, step-by-step visualisation of **k-means clustering** in vanilla JavaScript (ES modules + `<canvas>`, zero dependencies). Watch Lloyd's algorithm alternate between assigning points to the nearest centroid and moving each centroid to the mean of its cluster, until nothing changes.



## Features

- **Step / Back / Play / Finish**: the algorithm is a generator of events, so you can step forward, rewind through history, or animate at adjustable speed (keys: `→`, `←`, `space`, `R`).
- **Three initialisation strategies**: k-means++, Forgy (random data points) and random partition. Press *Restart* to try a new random initialisation and see how it changes the local minimum you land in.
- **Hand-placed centroids**: shift-click `k` times to choose the starting centroids yourself.
- **Draw your own data**: click anywhere to add points (or start from the *Empty* dataset).
- **Datasets that show where k-means works and where it fails**: Gaussian blobs, uneven-size clusters, uniform noise, two moons, concentric rings.
- **Voronoi regions** show the decision boundary of the current centroids; optional point→centroid lines and dashed trails showing how far each centroid moved.
- **Choosing k**: an elbow curve (best-of-restarts inertia for k = 1…10) with an automatic elbow pick, plus the silhouette score.

## CS concepts demonstrated

| Concept | Where |
|---|---|
| Lloyd's algorithm as coordinate descent (E-step / M-step), O(n·k·d) per iteration | `src/kmeans.js` |
| Monotone decrease of the objective (inertia / WCSS) and convergence to a local minimum | `kmeansSteps`, tested in `test/kmeans.test.js` |
| k-means++ seeding: D²-weighted sampling (Arthur & Vassilvitskii 2007) | `initKMeansPlusPlus` |
| Random restarts to escape poor local minima | `kmeansBestOf` |
| Empty-cluster handling | `computeCentroids` |
| Voronoi tessellation induced by the centroids | `voronoiCells` in `src/renderer.js` |
| Model selection: elbow method (kneedle-style, on log inertia) and silhouette coefficient | `src/metrics.js` |
| Seeded PRNG (mulberry32) + Box–Muller Gaussian sampling for reproducibility | `src/rng.js` |
| Generators as a way to expose an algorithm's intermediate state; replayable history | `kmeansSteps`, `src/player.js` |
| Inductive bias: k-means assumes convex, similarly-sized clusters (see *moons* / *rings*) | `src/datasets.js` |

## Project layout

```
index.html          UI shell
styles.css          layout + light/dark theme
src/
  rng.js            seeded PRNG, Gaussian sampling
  datasets.js       synthetic 2-D datasets in the unit square
  kmeans.js         init strategies, Lloyd's algorithm as a step generator, restarts
  metrics.js        silhouette, elbow curve, elbow detection
  player.js         StepPlayer: forward/back/toEnd over a generator (pure, testable)
  renderer.js       canvas drawing, Voronoi sampling, elbow chart
  app.js            DOM wiring and playback timer
test/               node:test suites (no browser required)
```

## Run

ES modules need to be served over HTTP (not `file://`):

```bash
npm start            # serves on http://localhost:5173 via `npx serve`
# or
python3 -m http.server 5173
```

## Test

Requires Node 18+. No install step — tests use the built-in `node:test` runner.

```bash
npm test
```

```
# tests 25
# pass 25
# fail 0
```

The tests cover: nearest-centroid ties, mean computation and empty clusters, correct event ordering, snapshot independence, **inertia never increasing** across phases for every init method, determinism under a fixed seed, `maxIter`, argument validation, k-means++ on duplicate points, k-means++ vs. Forgy on average, best-of-restarts, silhouette bounds and behaviour, a non-increasing elbow curve, the elbow detector recovering 3/4/5 true clusters, dataset bounds, the step player, and Voronoi labelling.

## Example (Node)

```js
import { blobs } from './src/datasets.js';
import { kmeans } from './src/kmeans.js';
import { silhouette } from './src/metrics.js';

const pts = blobs({ n: 300, centers: 4, spread: 0.03, seed: 7 });
const res = kmeans(pts, { k: 4, init: 'kmeans++', seed: 1 });
console.log(res.iterations, res.reason, res.inertia.toFixed(3));
console.log('silhouette', silhouette(pts, res.assignments, 4).toFixed(3));
```

## Things to try

1. Pick **Forgy** with k = 6 on blobs and hit *Restart* a few times — different seeds converge to visibly different (worse) local minima.
2. Run **Two moons** or **Concentric rings** with k = 2: k-means slices them with a straight line because each Voronoi cell is convex.
3. Shift-click to put all centroids in one corner and watch how many iterations it takes to recover.
4. Compute the elbow curve on **Uniform noise** — there is no real elbow, yet k-means still returns k clusters.

## Possible extensions

- k-medoids (PAM) or k-medians for robustness to outliers.
- Mini-batch k-means and a comparison of convergence speed.
- Gaussian Mixture Models via EM, drawing covariance ellipses (fixes the *uneven clusters* case).
- DBSCAN side-by-side to handle moons/rings.
- Elkan's or Hamerly's triangle-inequality acceleration with a "distance computations saved" counter.
- Upload a CSV, or cluster image pixels in RGB space for colour quantisation.
