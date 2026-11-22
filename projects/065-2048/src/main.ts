/**
 * Browser entry point: wires the engine, renderer, input and storage together.
 */
import { Game, type Direction } from "./game.js";
import { detectSwipe, keyToDirection, type Point } from "./input.js";
import { Renderer } from "./renderer.js";
import { GameStorage, MemoryStore, type KeyValueStore } from "./storage.js";

function $(id: string): HTMLElement {
  const el = document.getElementById(id);
  if (!el) throw new Error(`missing #${id}`);
  return el;
}

function pickStore(): KeyValueStore {
  try {
    const probe = "__2048_probe__";
    localStorage.setItem(probe, "1");
    localStorage.removeItem(probe);
    return localStorage;
  } catch {
    return new MemoryStore();
  }
}

const storage = new GameStorage(pickStore());
const board = $("board");
const gridEl = $("grid");
const tileLayer = $("tiles");
const scoreEl = $("score");
const bestEl = $("best");
const overlay = $("overlay");
const overlayText = $("overlay-text");
const continueBtn = $("continue") as HTMLButtonElement;
const undoBtn = $("undo") as HTMLButtonElement;

const saved = storage.loadGame();
let game = saved && saved.size === 4 ? Game.fromSnapshot(saved) : new Game();
const renderer = new Renderer(tileLayer, game.size);
renderer.drawGrid(gridEl);
renderer.sync(game.getTiles());

function showScore(gained = 0): void {
  scoreEl.textContent = String(game.score);
  bestEl.textContent = String(storage.submitScore(game.score));
  if (gained > 0) {
    // Floating "+N" animation next to the score.
    const pop = document.createElement("span");
    pop.className = "score-add";
    pop.textContent = `+${gained}`;
    scoreEl.parentElement?.appendChild(pop);
    pop.addEventListener("animationend", () => pop.remove());
  }
  undoBtn.disabled = !game.canUndo;
}

function showOverlay(kind: "won" | "over" | null): void {
  overlay.hidden = kind === null;
  overlay.className = kind ? `overlay ${kind}` : "overlay";
  continueBtn.hidden = kind !== "won";
  overlayText.textContent = kind === "won" ? "You win!" : kind === "over" ? "Game over" : "";
}

function refreshOverlay(): void {
  if (game.paused) showOverlay("won");
  else if (game.over) showOverlay("over");
  else showOverlay(null);
}

function play(dir: Direction): void {
  if (game.paused || game.over) return;
  const result = game.move(dir);
  if (!result.moved) {
    board.classList.remove("shake");
    void board.offsetWidth; // restart the CSS animation
    board.classList.add("shake");
    return;
  }
  renderer.animate(result, game.getTiles());
  showScore(result.scoreGained);
  storage.saveGame(game.snapshot());
  if (result.justWon || result.over) setTimeout(refreshOverlay, 300);
}

function newGame(): void {
  game = new Game();
  storage.clearGame();
  renderer.sync(game.getTiles());
  showScore();
  showOverlay(null);
  storage.saveGame(game.snapshot());
}

// ---- Keyboard ----
document.addEventListener("keydown", (e) => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (e.key === "u" || e.key === "U") {
    $("undo").click();
    return;
  }
  const dir = keyToDirection(e.key);
  if (dir) {
    e.preventDefault();
    play(dir);
  }
});

// ---- Touch / pointer swipes ----
let start: Point | null = null;
let startTime = 0;
board.addEventListener("pointerdown", (e) => {
  start = { x: e.clientX, y: e.clientY };
  startTime = performance.now();
});
board.addEventListener("pointerup", (e) => {
  if (!start) return;
  const dir = detectSwipe(start, { x: e.clientX, y: e.clientY }, performance.now() - startTime);
  start = null;
  if (dir) play(dir);
});
board.addEventListener("pointercancel", () => (start = null));
// Stop the page from scrolling while swiping on the board.
board.addEventListener("touchmove", (e) => e.preventDefault(), { passive: false });

// ---- Buttons ----
$("new-game").addEventListener("click", newGame);
$("retry").addEventListener("click", newGame);
continueBtn.addEventListener("click", () => {
  game.continueAfterWin();
  storage.saveGame(game.snapshot());
  showOverlay(null);
});
undoBtn.addEventListener("click", () => {
  if (game.undo()) {
    renderer.sync(game.getTiles());
    showScore();
    refreshOverlay();
    storage.saveGame(game.snapshot());
  }
});

showScore();
refreshOverlay();
