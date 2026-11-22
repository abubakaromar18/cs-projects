import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { detectSwipe, keyToDirection } from "../src/input.js";

describe("keyToDirection", () => {
  test("arrows, WASD and HJKL", () => {
    assert.equal(keyToDirection("ArrowUp"), "up");
    assert.equal(keyToDirection("ArrowLeft"), "left");
    assert.equal(keyToDirection("d"), "right");
    assert.equal(keyToDirection("S"), "down");
    assert.equal(keyToDirection("k"), "up");
    assert.equal(keyToDirection("h"), "left");
  });
  test("unrelated keys", () => {
    assert.equal(keyToDirection("Enter"), null);
    assert.equal(keyToDirection("x"), null);
  });
});

describe("detectSwipe", () => {
  const o = { x: 100, y: 100 };
  test("four cardinal swipes (screen y grows downward)", () => {
    assert.equal(detectSwipe(o, { x: 200, y: 110 }), "right");
    assert.equal(detectSwipe(o, { x: 10, y: 90 }), "left");
    assert.equal(detectSwipe(o, { x: 105, y: 20 }), "up");
    assert.equal(detectSwipe(o, { x: 95, y: 220 }), "down");
  });
  test("too short is a tap", () => {
    assert.equal(detectSwipe(o, { x: 110, y: 105 }), null);
  });
  test("ambiguous diagonal is rejected", () => {
    assert.equal(detectSwipe(o, { x: 160, y: 160 }), null);
  });
  test("slow drags are rejected", () => {
    assert.equal(detectSwipe(o, { x: 300, y: 100 }, 5000), null);
  });
  test("options are configurable", () => {
    assert.equal(detectSwipe(o, { x: 115, y: 100 }, 0, { minDistance: 10 }), "right");
    assert.equal(detectSwipe(o, { x: 160, y: 150 }, 0, { axisRatio: 1.1 }), "right");
  });
});
