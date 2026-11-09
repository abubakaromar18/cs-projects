/** Lowest and highest temperatures across all days, or null if none exist. */
export function overallRange(days) {
  const values = days.flatMap((d) => [d.low, d.high]).filter((v) => typeof v === 'number');
  return values.length ? { min: Math.min(...values), max: Math.max(...values) } : null;
}

/**
 * Position one day's low-to-high bar on the shared scale, in percent.
 * Returns null if the day has no usable readings, so no bar is drawn.
 */
export function barGeometry(day, range) {
  if (!range || typeof day.low !== 'number' || typeof day.high !== 'number') return null;
  const span = range.max - range.min;
  if (span === 0) return { left: 0, width: 100 };
  return {
    left: ((day.low - range.min) / span) * 100,
    width: ((day.high - day.low) / span) * 100,
  };
}
