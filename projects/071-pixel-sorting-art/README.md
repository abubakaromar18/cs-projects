# 071 · Pixel Sorting Art

A glitch-art generator that **sorts runs of pixels** by brightness, hue or another key, the effect made famous by Kim Asendorf's pixel-sorting scripts. Built with NumPy and Pillow, with a small CLI and built-in procedural source images so you can try it without supplying a photo.

```
source (plasma)            hue · threshold · 90°        lightness · random · 30°
┌──────────────┐           ┌──────────────┐            ┌──────────────┐
│ ◌  ●   ◌  ●  │    ──►    │ ║▓▓║  ▓▓║ ▓  │            │ ╱╱ ╱╱╱ ╱ ╱╱  │
│   ●  ◌   ●   │           │ ║██║  ██║ █  │            │╱ ╱╱ ╱╱╱ ╱╱ ╱ │
└──────────────┘           └──────────────┘            └──────────────┘
```
(Run `make demo` to see the real thing.)

## How it works

1. **Rotate** the image so the sort direction is horizontal. Right angles use lossless transposes. Other angles use a nearest-neighbour rotation, and the padding it adds is masked out.
2. **Key**: map each pixel to a scalar in `[0, 1]` (`lightness`, `luminance`, `hue`, `saturation`, `red`, `green`, `blue`).
3. **Interval mask**: decide which pixels may move:
   - `threshold`: only pixels whose key is in `[lower, upper]`
   - `edges`: break runs wherever the key jumps by more than `edge_threshold` (a 1-D gradient edge detector)
   - `random`: runs of geometric random length with mean `mean_length`
   - `full`: whole rows
4. **Sort**: find contiguous `True` runs (a vectorised diff trick) and stable-`argsort` each run by key.
5. **Rotate back** and centre-crop to the original size. Alpha is kept as-is.

## CS concepts

- Image data as an `(H, W, 3)` tensor; vectorised NumPy colour-space conversions (RGB→HSV/HSL, Rec. 709 luma)
- Stable sorting and permutation indexing (`argsort`) applied to a segment of an array
- Run-length detection in O(n) with `np.diff` on a padded mask
- Geometric distributions for random segmentation, seeded for reproducibility
- Rotations as change of basis, with lossless transposes vs. resampling
- Strategy pattern: pluggable key and interval functions held in registries

Complexity: each run of length k costs O(k log k), so the whole image costs O(N log L), where L is the longest run.

## Usage

```bash
make install            # pip install -e ".[dev]"
make test               # run the pytest suite
make demo               # writes out/demo.png from a generated plasma

pixelsort photo.jpg -o glitch.png -k hue -i threshold --lower 0.3 --upper 0.7 --angle 90
pixelsort --demo stripes -o out/s.png --save-source out/src.png -i random --mean-length 60 --seed 1
python -m pixelsort --demo plasma -o out/p.png -i edges --edge-threshold 0.02 -r
```

| Option | Meaning |
|---|---|
| `-k/--key` | sort key |
| `-i/--interval` | `threshold`, `edges`, `random`, `full` |
| `-a/--angle` | direction in degrees (0 = left→right, 90 = top→bottom) |
| `-r/--reverse` | sort descending |
| `--lower/--upper` | threshold band |
| `--edge-threshold`, `--mean-length`, `--seed` | interval tuning |

Example output:

```
$ pixelsort --demo plasma -o out/demo.png -k hue --angle 90 --seed 7
wrote out/demo.png (480x320, key=hue, interval=threshold, angle=90.0)
```

Library use:

```python
from PIL import Image
from pixelsort import SortConfig, sort_image

sort_image(Image.open("in.png"), SortConfig(key="saturation", interval="edges", angle=45)).save("out.png")
```

## Tests

16 pytest tests. They check that the hue and saturation keys match `colorsys`, that interval masks and run detection behave correctly, that sorted runs are monotonic and each row keeps the same set of pixels, that out-of-band pixels stay put, that vertical and arbitrary-angle sorting work, that alpha is preserved, and they run the CLI end to end.

## Possible extensions

- Mask images (sort only inside a painted region)
- Sorting along curves or in spirals instead of straight lines
- Animated GIFs that sweep the threshold band
- Numba or vectorised segmented sort for large images
- A Tkinter or web UI with live sliders
