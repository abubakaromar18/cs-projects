//! Minimal UTC timestamp formatting without external crates.

/// Formats Unix milliseconds as an RFC 3339 UTC string, e.g.
/// `2026-10-28T01:41:52.123Z`.
pub fn rfc3339_utc(unix_ms: u64) -> String {
    let secs = unix_ms / 1000;
    let millis = unix_ms % 1000;
    let days = (secs / 86_400) as i64;
    let sod = secs % 86_400;
    let (y, m, d) = civil_from_days(days);
    format!(
        "{y:04}-{m:02}-{d:02}T{:02}:{:02}:{:02}.{millis:03}Z",
        sod / 3600,
        (sod / 60) % 60,
        sod % 60
    )
}

/// Converts days since 1970-01-01 to a (year, month, day) civil date.
///
/// Howard Hinnant's algorithm: shift the year to start in March so the leap
/// day falls at the end, then work in 400-year "eras" of 146 097 days.
fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z.rem_euclid(146_097); // day of era [0, 146096]
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365; // [0, 399]
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100); // [0, 365]
    let mp = (5 * doy + 2) / 153; // March-based month [0, 11]
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    let y = yoe + era * 400 + i64::from(m <= 2);
    (y, m, d)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn known_dates() {
        assert_eq!(rfc3339_utc(0), "1970-01-01T00:00:00.000Z");
        assert_eq!(
            rfc3339_utc(crate::layout::DEFAULT_EPOCH_MS),
            "2020-01-01T00:00:00.000Z"
        );
        assert_eq!(rfc3339_utc(951_782_400_000), "2000-02-29T00:00:00.000Z"); // leap day
        assert_eq!(rfc3339_utc(1_700_000_000_123), "2023-11-14T22:13:20.123Z");
    }
}
