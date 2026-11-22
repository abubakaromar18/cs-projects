/**
 * DOM renderer. Tiles are absolutely-positioned elements keyed by tile id;
 * their cell is set through the CSS custom properties --row / --col, and a
 * CSS transition on `transform` produces the slide animation for free.
 *
 * Animation sequence for one move:
 *   1. slide every moved tile to its destination (CSS transition)
 *   2. after the slide, delete merge sources and add the merged tile ("pop")
 *   3. add the newly spawned tile ("appear")
 */
import type { MoveResult, Tile } from "./game.js";

export const SLIDE_MS = 110;

export class Renderer {
  private readonly elements = new Map<number, HTMLElement>();
  private pending: ReturnType<typeof setTimeout> | null = null;
  private latest: Tile[] = [];

  constructor(
    private readonly layer: HTMLElement,
    private readonly size: number,
  ) {
    layer.style.setProperty("--size", String(size));
  }

  /** Draw the background grid cells. */
  drawGrid(container: HTMLElement): void {
    container.replaceChildren();
    container.style.setProperty("--size", String(this.size));
    for (let i = 0; i < this.size * this.size; i++) {
      const cell = document.createElement("div");
      cell.className = "cell";
      container.appendChild(cell);
    }
  }

  /** Reconcile the DOM with `tiles` immediately, without slide animations. */
  sync(tiles: Tile[]): void {
    this.flush();
    this.latest = tiles;
    const live = new Set(tiles.map((t) => t.id));
    for (const [id, el] of this.elements) {
      if (!live.has(id)) {
        el.remove();
        this.elements.delete(id);
      }
    }
    for (const t of tiles) {
      const el = this.elements.get(t.id) ?? this.create(t, "");
      this.place(el, t.row, t.col);
    }
  }

  /** Animate a move, ending in the state described by `tiles`. */
  animate(result: MoveResult, tiles: Tile[]): void {
    this.flush(); // finish any in-flight animation instantly
    this.latest = tiles;

    for (const m of result.moves) {
      const el = this.elements.get(m.id);
      if (el) this.place(el, m.to.row, m.to.col);
    }

    this.pending = setTimeout(() => {
      this.pending = null;
      for (const merge of result.merges) {
        for (const src of merge.sources) {
          this.elements.get(src)?.remove();
          this.elements.delete(src);
        }
        const t = tiles.find((x) => x.id === merge.id);
        if (t) this.create(t, "merged");
      }
      if (result.spawned) {
        const t = tiles.find((x) => x.id === result.spawned!.id);
        if (t) this.create(t, "new");
      }
      this.sync(tiles); // safety net: guarantees DOM === state
    }, SLIDE_MS);
  }

  private flush(): void {
    if (this.pending !== null) {
      clearTimeout(this.pending);
      this.pending = null;
      this.sync(this.latest);
    }
  }

  private create(t: Tile, animClass: string): HTMLElement {
    const el = document.createElement("div");
    const inner = document.createElement("div");
    el.className = `tile tile-${t.value > 2048 ? "super" : t.value}`;
    inner.className = `tile-inner ${animClass}`.trim();
    inner.textContent = String(t.value);
    if (t.value >= 1024) el.classList.add("small-text");
    el.appendChild(inner);
    el.dataset.id = String(t.id);
    this.place(el, t.row, t.col);
    this.layer.appendChild(el);
    this.elements.set(t.id, el);
    return el;
  }

  private place(el: HTMLElement, row: number, col: number): void {
    el.style.setProperty("--row", String(row));
    el.style.setProperty("--col", String(col));
  }
}
