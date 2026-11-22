import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { GameStorage, MemoryStore, type KeyValueStore } from "../src/storage.js";
import { Game } from "../src/game.js";

describe("GameStorage", () => {
  test("best score only increases", () => {
    const s = new GameStorage(new MemoryStore());
    assert.equal(s.getBest(), 0);
    assert.equal(s.submitScore(120), 120);
    assert.equal(s.submitScore(40), 120);
    assert.equal(s.getBest(), 120);
  });

  test("saves and loads a game", () => {
    const s = new GameStorage(new MemoryStore());
    const g = new Game();
    g.move("left");
    s.saveGame(g.snapshot());
    const loaded = s.loadGame();
    assert.ok(loaded);
    assert.deepEqual(Game.fromSnapshot(loaded).toGrid(), g.toGrid());
    s.clearGame();
    assert.equal(s.loadGame(), null);
  });

  test("corrupt data is ignored", () => {
    const store = new MemoryStore();
    store.setItem("2048.game", "{not json");
    store.setItem("2048.best", "banana");
    const s = new GameStorage(store);
    assert.equal(s.loadGame(), null);
    assert.equal(s.getBest(), 0);
    store.setItem("2048.game", JSON.stringify({ size: 4, tiles: [{ id: "x" }] }));
    assert.equal(s.loadGame(), null);
  });

  test("throwing storage never breaks the game", () => {
    const broken: KeyValueStore = {
      getItem() { throw new Error("denied"); },
      setItem() { throw new Error("quota"); },
      removeItem() { throw new Error("denied"); },
    };
    const s = new GameStorage(broken);
    assert.equal(s.getBest(), 0);
    assert.equal(s.submitScore(10), 10);
    assert.doesNotThrow(() => s.saveGame(new Game().snapshot()));
    assert.equal(s.loadGame(), null);
    assert.doesNotThrow(() => s.clearGame());
  });
});
