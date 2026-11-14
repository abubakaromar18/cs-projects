/**
 * A tape-deck over a step generator: step forward lazily, step back through
 * recorded history, and know when the run has finished.
 * Pure logic (no DOM), so it is unit-testable in Node.
 */
export class StepPlayer {
  /** @param {() => Generator} makeGenerator - factory so the run can be restarted */
  constructor(makeGenerator) {
    this.makeGenerator = makeGenerator;
    this.reset();
  }

  reset() {
    this.gen = this.makeGenerator();
    this.history = [];
    this.index = -1;
    this.exhausted = false;
    return this.forward();
  }

  /** Current event (or null before the first step). */
  get current() {
    return this.index >= 0 ? this.history[this.index] : null;
  }

  get atEnd() {
    return this.exhausted && this.index === this.history.length - 1;
  }

  get atStart() {
    return this.index <= 0;
  }

  forward() {
    if (this.index < this.history.length - 1) {
      this.index++;
      return this.current;
    }
    if (this.exhausted) return this.current;
    const { value, done } = this.gen.next();
    if (done || value === undefined) {
      this.exhausted = true;
      return this.current;
    }
    this.history.push(value);
    this.index++;
    if (value.type === 'done') this.exhausted = true;
    return value;
  }

  back() {
    if (this.index > 0) this.index--;
    return this.current;
  }

  /** Jump to the end of the run (bounded to avoid runaway loops). */
  toEnd(limit = 10_000) {
    for (let i = 0; i < limit && !this.atEnd; i++) this.forward();
    return this.current;
  }
}
