/**
 * Alert sounds synthesised with the Web Audio API — no audio files needed.
 * Each sound is a short sequence of notes: [frequencyHz, startSec, lengthSec].
 */

const MELODIES = {
  workDone: [[523.25, 0, 0.18], [659.25, 0.2, 0.18], [783.99, 0.4, 0.35]], // C-E-G up
  breakDone: [[783.99, 0, 0.18], [659.25, 0.2, 0.18], [523.25, 0.4, 0.35]], // G-E-C down
};

let ctx = null;

function audioContext() {
  const AC = globalThis.AudioContext ?? globalThis.webkitAudioContext;
  if (!AC) return null;
  ctx ??= new AC();
  return ctx;
}

/**
 * Browsers only allow audio after a user gesture; call this from a click
 * handler (e.g. the Start button) so later alerts can play.
 */
export function unlockAudio() {
  const ac = audioContext();
  if (ac?.state === 'suspended') ac.resume();
}

/** Play a named melody at the given volume (0..1). Silently no-ops without audio support. */
export function playAlert(name = 'workDone', volume = 0.4) {
  const ac = audioContext();
  const notes = MELODIES[name];
  if (!ac || !notes || volume <= 0) return;
  const t0 = ac.currentTime;
  for (const [freq, start, len] of notes) {
    const osc = ac.createOscillator();
    const gain = ac.createGain();
    osc.type = 'sine';
    osc.frequency.value = freq;
    // Quick attack and exponential release avoid audible clicks.
    gain.gain.setValueAtTime(0.0001, t0 + start);
    gain.gain.exponentialRampToValueAtTime(volume, t0 + start + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + start + len);
    osc.connect(gain).connect(ac.destination);
    osc.start(t0 + start);
    osc.stop(t0 + start + len + 0.05);
  }
}
