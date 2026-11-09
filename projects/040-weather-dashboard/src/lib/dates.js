/**
 * Format an API date ("2026-11-09") as a calendar date.
 *
 * `new Date("2026-11-09")` means midnight UTC, which is the previous day for
 * anyone west of Greenwich. The date is already local to the city, so it is
 * built and formatted in UTC, keeping the browser's time zone out of it.
 */
export function formatDay(isoDate, { today = false, locale = 'en-US' } = {}) {
  const [year, month, day] = isoDate.split('-').map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  const format = (options) =>
    new Intl.DateTimeFormat(locale, { timeZone: 'UTC', ...options }).format(date);
  return {
    weekday: today ? 'Today' : format({ weekday: 'short' }),
    date: format({ month: 'short', day: 'numeric' }),
  };
}
