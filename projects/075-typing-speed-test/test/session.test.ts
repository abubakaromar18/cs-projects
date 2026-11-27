import { test } from "node:test";
import assert from "node:assert/strict";
import { TypingSession, wpm, consistency } from "../src/core/session.js";

/** Type a string with a fixed gap between keystrokes, starting at t0. */
function typeAll(s: TypingSession, text: string, t0 = 0, gap = 100): number {
  let t = t0;
  for (const ch of text) {
    if (ch === "\b") s.backspace(t);
    else s.type(ch, t);
    t += gap;
  }
  return t - gap;
}

test("wpm uses 5 chars per word", () => {
  assert.equal(wpm(50, 60_000), 10);
  assert.equal(wpm(25, 30_000), 10);
  assert.equal(wpm(10, 0), 0);
});

test("state machine: ready → running → finished", () => {
  const s = new TypingSession("ab");
  assert.equal(s.state, "ready");
  s.type("a", 0);
  assert.equal(s.state, "running");
  s.type("b", 100);
  assert.equal(s.state, "finished");
  assert.equal(s.type("x", 200), false, "typing after finish is ignored");
  assert.equal(s.typed, "ab");
});

test("perfect run: net == raw, 100% accuracy", () => {
  const text = "hello world";
  const s = new TypingSession(text);
  const end = typeAll(s, text, 1000, 120);
  const st = s.stats(end);
  assert.equal(st.elapsedMs, 120 * (text.length - 1));
  assert.equal(st.accuracy, 100);
  assert.equal(st.correctChars, text.length);
  assert.equal(st.incorrectChars, 0);
  assert.equal(st.netWpm, st.rawWpm);
  assert.ok(Math.abs(st.consistency - 100) < 1e-9, "perfectly even rhythm");
});

test("uncorrected error lowers net WPM and accuracy", () => {
  const s = new TypingSession("abcd");
  typeAll(s, "abxd");
  const st = s.stats(0);
  assert.equal(st.correctChars, 3);
  assert.equal(st.incorrectChars, 1);
  assert.equal(st.accuracy, 75);
  assert.ok(st.netWpm < st.rawWpm);
  assert.equal(st.correctedErrors, 0);
  assert.equal(s.charStatus(2), "incorrect");
});

test("corrected error keeps net WPM but costs accuracy", () => {
  const s = new TypingSession("abcd");
  typeAll(s, "abx\bcd");
  const st = s.stats(0);
  assert.equal(s.typed, "abcd");
  assert.equal(st.correctChars, 4);
  assert.equal(st.incorrectChars, 0);
  assert.equal(st.correctedErrors, 1);
  assert.equal(st.accuracy, 80); // 4 of 5 char keystrokes correct
  assert.equal(st.netWpm, st.rawWpm);
});

test("backspace before start and at position 0 is a no-op", () => {
  const s = new TypingSession("abc");
  s.backspace(0);
  assert.equal(s.state, "ready");
  s.type("a", 10);
  s.backspace(20);
  s.backspace(30);
  assert.equal(s.cursor, 0);
  assert.equal(s.keystrokes.filter((k) => k.kind === "backspace").length, 1);
});

test("backspaceWord deletes back to previous space", () => {
  const s = new TypingSession("one two three");
  typeAll(s, "one tw");
  s.backspaceWord(1000);
  assert.equal(s.typed, "one ");
  s.backspaceWord(1100);
  assert.equal(s.typed, "");
});

test("finish() stops a timed test early", () => {
  const s = new TypingSession("a long passage of text");
  typeAll(s, "a lo", 0, 250);
  s.finish(30_000);
  assert.equal(s.state, "finished");
  assert.equal(s.stats(99_999).elapsedMs, 30_000, "clock frozen at finish");
});

test("keyStats aggregates by physical key and records misses on the expected key", () => {
  const s = new TypingSession("Aa!");
  s.type("A", 0);
  s.type("s", 100); // wanted "a"
  s.backspace(200);
  s.type("a", 300);
  s.type("!", 3500); // long pause: latency excluded
  const ks = s.keyStats(2000);
  assert.deepEqual(ks["a"], { attempts: 3, misses: 1, latencyTotal: 100, latencyCount: 1 });
  assert.deepEqual(ks["1"], { attempts: 1, misses: 0, latencyTotal: 0, latencyCount: 0 });
});

test("timeline replays backspaces and ends at finish", () => {
  const s = new TypingSession("abcdefghij");
  // 5 chars in first second, then an error fixed, then the rest
  typeAll(s, "abcde", 0, 200);         // t=0..800
  typeAll(s, "x\bfghij", 1100, 200);   // t=1100..2300
  const tl = s.timeline(1000);
  assert.equal(tl.length, 3);
  assert.equal(tl[0]!.errors, 0);
  assert.equal(tl[1]!.errors, 1);
  assert.equal(tl[2]!.second, 2.3);
  const final = s.stats(0).netWpm;
  assert.ok(Math.abs(tl[2]!.wpm - final) < 1e-9, "last point equals final net wpm");
});

test("consistency maps coefficient of variation to 0–100", () => {
  assert.equal(consistency([100, 100, 100]), 100);
  assert.equal(consistency([1]), 100);
  const c = consistency([50, 150]); // cv = 0.5
  assert.ok(Math.abs(c - 50) < 1e-9);
  assert.equal(consistency([1, 1000, 1, 1000, 1, 5000]), 0);
});

test("rejects empty target and multi-char input", () => {
  assert.throws(() => new TypingSession(""));
  assert.throws(() => new TypingSession("a").type("ab", 0));
});
