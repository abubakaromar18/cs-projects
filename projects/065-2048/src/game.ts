/**
 * Pure 2048 game engine — no DOM, fully deterministic given an RNG.
 *
 * The board is an N×N grid of tiles. Every tile carries a stable `id` so the
 * renderer can animate it from its old position to its new one. A move
 * returns a `MoveResult` describing exactly what happened (slides, merges,
 * the spawned tile), which is all the UI needs to drive animations.
 */

export type Direction = "up" | "down" | "left" | "right";

export interface Position {
  row: number;
  col: number;
}

export interface Tile extends Position {
  id: number;
  value: number;
}

/** A tile that slid from one cell to another (possibly into a merge). */
export interface TileMove {
  id: number;
  from: Position;
  to: Position;
}

/** Two tiles that combined into a brand-new tile. */
export interface TileMerge {
  id: number;
  value: number;
  at: Position;
  sources: [number, number];
}

export interface MoveResult {
  moved: boolean;
  scoreGained: number;
  moves: TileMove[];
  merges: TileMerge[];
  spawned: Tile | null;
  /** True only on the move that first reaches the target tile. */
  justWon: boolean;
  over: boolean;
}

/** Returns a float in [0, 1), like Math.random. Injectable for tests. */
export type Rng = () => number;

export interface GameOptions {
  size?: number;
  target?: number;
  rng?: Rng;
  /** Probability that a spawned tile is a 4 rather than a 2. */
  fourProbability?: number;
}

/** Serializable game state, used for undo and save/restore. */
export interface Snapshot {
  size: number;
  target: number;
  tiles: Tile[];
  score: number;
  won: boolean;
  keepPlaying: boolean;
  nextId: number;
}

const VECTORS: Record<Direction, Position> = {
  up: { row: -1, col: 0 },
  down: { row: 1, col: 0 },
  left: { row: 0, col: -1 },
  right: { row: 0, col: 1 },
};

export class Game {
  readonly size: number;
  readonly target: number;
  private readonly rng: Rng;
  private readonly fourProbability: number;

  private tiles: Tile[] = [];
  private nextId = 1;
  private _score = 0;
  private _won = false;
  private _keepPlaying = false;
  private history: Snapshot | null = null;

  constructor(options: GameOptions = {}, startTiles = 2) {
    this.size = options.size ?? 4;
    this.target = options.target ?? 2048;
    this.rng = options.rng ?? Math.random;
    this.fourProbability = options.fourProbability ?? 0.1;
    if (!Number.isInteger(this.size) || this.size < 2) {
      throw new RangeError(`board size must be an integer >= 2, got ${this.size}`);
    }
    for (let i = 0; i < startTiles; i++) this.spawn();
  }

  /**
   * Build a game from a literal grid (0 = empty). Handy for tests and puzzles.
   * Example: Game.fromGrid([[2, 2, 0, 0], ...])
   */
  static fromGrid(grid: number[][], options: GameOptions = {}): Game {
    const game = new Game({ ...options, size: grid.length }, 0);
    grid.forEach((rowValues, row) => {
      if (rowValues.length !== grid.length) throw new RangeError("grid must be square");
      rowValues.forEach((value, col) => {
        if (value !== 0) game.tiles.push({ id: game.nextId++, value, row, col });
      });
    });
    return game;
  }

  static fromSnapshot(snapshot: Snapshot, options: Omit<GameOptions, "size" | "target"> = {}): Game {
    const game = new Game({ ...options, size: snapshot.size, target: snapshot.target }, 0);
    game.restore(snapshot);
    return game;
  }

  get score(): number {
    return this._score;
  }

  get won(): boolean {
    return this._won;
  }

  get keepPlaying(): boolean {
    return this._keepPlaying;
  }

  get over(): boolean {
    return !this.canMove();
  }

  get canUndo(): boolean {
    return this.history !== null;
  }

  /** A copy of the current tiles (safe to mutate). */
  getTiles(): Tile[] {
    return this.tiles.map((t) => ({ ...t }));
  }

  /** The board as a 2D array of values, 0 for empty. */
  toGrid(): number[][] {
    const grid = Array.from({ length: this.size }, () => new Array<number>(this.size).fill(0));
    for (const t of this.tiles) grid[t.row]![t.col] = t.value;
    return grid;
  }

  maxTile(): number {
    return this.tiles.reduce((m, t) => Math.max(m, t.value), 0);
  }

  snapshot(): Snapshot {
    return {
      size: this.size,
      target: this.target,
      tiles: this.getTiles(),
      score: this._score,
      won: this._won,
      keepPlaying: this._keepPlaying,
      nextId: this.nextId,
    };
  }

  restore(s: Snapshot): void {
    if (s.size !== this.size) throw new RangeError("snapshot size mismatch");
    this.tiles = s.tiles.map((t) => ({ ...t }));
    this._score = s.score;
    this._won = s.won;
    this._keepPlaying = s.keepPlaying;
    this.nextId = s.nextId;
  }

  /** After winning, let the player continue toward higher tiles. */
  continueAfterWin(): void {
    this._keepPlaying = true;
  }

  /** Revert the last move (one level of undo). */
  undo(): boolean {
    if (!this.history) return false;
    this.restore(this.history);
    this.history = null;
    return true;
  }

  emptyCells(): Position[] {
    const occupied = new Set(this.tiles.map((t) => t.row * this.size + t.col));
    const cells: Position[] = [];
    for (let row = 0; row < this.size; row++) {
      for (let col = 0; col < this.size; col++) {
        if (!occupied.has(row * this.size + col)) cells.push({ row, col });
      }
    }
    return cells;
  }

  /** Place a 2 (or occasionally a 4) on a random empty cell. */
  spawn(): Tile | null {
    const empty = this.emptyCells();
    if (empty.length === 0) return null;
    const cell = empty[Math.floor(this.rng() * empty.length)]!;
    const value = this.rng() < this.fourProbability ? 4 : 2;
    const tile: Tile = { id: this.nextId++, value, ...cell };
    this.tiles.push(tile);
    return { ...tile };
  }

  /** True if any move would change the board. */
  canMove(): boolean {
    if (this.tiles.length < this.size * this.size) return true;
    const grid = this.toGrid();
    for (let r = 0; r < this.size; r++) {
      for (let c = 0; c < this.size; c++) {
        const v = grid[r]![c]!;
        if (c + 1 < this.size && grid[r]![c + 1] === v) return true;
        if (r + 1 < this.size && grid[r + 1]![c] === v) return true;
      }
    }
    return false;
  }

  /**
   * Slide all tiles in `dir`. Each tile merges at most once per move, and the
   * pair nearest the leading edge merges first — so [2,2,2,2] → [4,4] and
   * [4,2,2,0] → [4,4,0,0] (not 8).
   */
  move(dir: Direction): MoveResult {
    const before = this.snapshot();
    const byCell = new Map<number, Tile>();
    for (const t of this.tiles) byCell.set(t.row * this.size + t.col, t);

    const moves: TileMove[] = [];
    const merges: TileMerge[] = [];
    const next: Tile[] = [];
    let scoreGained = 0;

    for (const line of this.lines(dir)) {
      // Tiles in this line, ordered from the leading edge backwards.
      const lineTiles = line
        .map((p) => byCell.get(p.row * this.size + p.col))
        .filter((t): t is Tile => t !== undefined);

      let slot = 0;
      let last: { tile: Tile; merged: boolean } | null = null;

      for (const tile of lineTiles) {
        if (last && !last.merged && last.tile.value === tile.value) {
          // Merge `tile` into the previously placed tile.
          const at = { row: last.tile.row, col: last.tile.col };
          moves.push({ id: tile.id, from: { row: tile.row, col: tile.col }, to: at });
          const merged: Tile = { id: this.nextId++, value: tile.value * 2, ...at };
          merges.push({ id: merged.id, value: merged.value, at, sources: [last.tile.id, tile.id] });
          next[next.indexOf(last.tile)] = merged;
          scoreGained += merged.value;
          last = { tile: merged, merged: true };
        } else {
          const to = line[slot++]!;
          if (to.row !== tile.row || to.col !== tile.col) {
            moves.push({ id: tile.id, from: { row: tile.row, col: tile.col }, to: { ...to } });
          }
          const placed: Tile = { ...tile, row: to.row, col: to.col };
          next.push(placed);
          last = { tile: placed, merged: false };
        }
      }
    }

    const moved = moves.length > 0;
    let spawned: Tile | null = null;
    let justWon = false;

    if (moved) {
      this.history = before;
      this.tiles = next;
      this._score += scoreGained;
      if (!this._won && merges.some((m) => m.value >= this.target)) {
        this._won = true;
        justWon = true;
      }
      spawned = this.spawn();
    }

    return { moved, scoreGained, moves, merges, spawned, justWon, over: !this.canMove() };
  }

  /** True when the player has won and hasn't chosen to keep playing. */
  get paused(): boolean {
    return this._won && !this._keepPlaying;
  }

  /**
   * The rows/columns to process for a direction, each listed from the cell
   * tiles slide *toward* (the leading edge) to the far edge.
   */
  private lines(dir: Direction): Position[][] {
    const v = VECTORS[dir];
    const n = this.size;
    const forward = [...Array(n).keys()];
    const reversed = [...forward].reverse();
    // Moving toward +1 means the leading edge is index n-1.
    const order = (delta: number) => (delta > 0 ? reversed : forward);
    const result: Position[][] = [];
    for (let i = 0; i < n; i++) {
      if (v.row === 0) result.push(order(v.col).map((col) => ({ row: i, col })));
      else result.push(order(v.row).map((row) => ({ row, col: i })));
    }
    return result;
  }
}
