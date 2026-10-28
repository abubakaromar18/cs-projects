//! The [`SnowflakeId`] value type: packing, unpacking, parsing and display.

use std::fmt;
use std::str::FromStr;

use crate::layout::*;

/// A 64-bit, time-ordered unique identifier.
///
/// `SnowflakeId` is a thin newtype over `u64`; its ordering is the numeric
/// ordering of the underlying integer, which is (mostly) creation order.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct SnowflakeId(u64);

/// The three fields of an ID, plus the absolute time they decode to.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Parts {
    /// Milliseconds since the generator's custom epoch.
    pub timestamp: u64,
    /// Node (worker) id that produced the ID.
    pub node_id: u16,
    /// Position within its millisecond.
    pub sequence: u16,
}

impl SnowflakeId {
    /// Packs the three fields into an ID.
    ///
    /// Returns `None` if any field is out of range for the layout.
    pub fn from_parts(timestamp: u64, node_id: u16, sequence: u16) -> Option<Self> {
        if timestamp > MAX_TIMESTAMP || node_id > MAX_NODE_ID || u64::from(sequence) > MAX_SEQUENCE
        {
            return None;
        }
        Some(Self(
            (timestamp << TIMESTAMP_SHIFT)
                | (u64::from(node_id) << NODE_SHIFT)
                | u64::from(sequence),
        ))
    }

    /// Wraps a raw integer. Fails if the sign bit is set (not a valid Snowflake).
    pub fn from_raw(raw: u64) -> Option<Self> {
        (raw >> 63 == 0).then_some(Self(raw))
    }

    /// The raw 64-bit value.
    pub fn as_u64(self) -> u64 {
        self.0
    }

    /// The value as a signed integer (always non-negative), handy for databases.
    pub fn as_i64(self) -> i64 {
        self.0 as i64
    }

    /// Milliseconds since the custom epoch.
    pub fn timestamp(self) -> u64 {
        self.0 >> TIMESTAMP_SHIFT
    }

    /// The node id field.
    pub fn node_id(self) -> u16 {
        ((self.0 >> NODE_SHIFT) & u64::from(MAX_NODE_ID)) as u16
    }

    /// The sequence field.
    pub fn sequence(self) -> u16 {
        (self.0 & MAX_SEQUENCE) as u16
    }

    /// All fields at once.
    pub fn parts(self) -> Parts {
        Parts {
            timestamp: self.timestamp(),
            node_id: self.node_id(),
            sequence: self.sequence(),
        }
    }

    /// Absolute Unix time in milliseconds, given the epoch the ID was made with.
    pub fn unix_millis(self, epoch_ms: u64) -> u64 {
        epoch_ms + self.timestamp()
    }

    /// Encodes the ID in base-62 (`0-9A-Za-z`), at most 11 characters.
    ///
    /// Shorter than decimal (up to 19 digits) and URL-safe. Note that the
    /// encoding is *not* fixed-width, so compare decoded IDs, not strings.
    pub fn to_base62(self) -> String {
        const ALPHABET: &[u8; 62] =
            b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
        let mut n = self.0;
        if n == 0 {
            return "0".into();
        }
        let mut buf = Vec::with_capacity(11);
        while n > 0 {
            buf.push(ALPHABET[(n % 62) as usize]);
            n /= 62;
        }
        buf.reverse();
        String::from_utf8(buf).expect("alphabet is ASCII")
    }

    /// Decodes a base-62 string produced by [`to_base62`](Self::to_base62).
    pub fn from_base62(s: &str) -> Option<Self> {
        if s.is_empty() {
            return None;
        }
        let mut n: u64 = 0;
        for c in s.bytes() {
            let digit = match c {
                b'0'..=b'9' => c - b'0',
                b'A'..=b'Z' => c - b'A' + 10,
                b'a'..=b'z' => c - b'a' + 36,
                _ => return None,
            };
            n = n.checked_mul(62)?.checked_add(u64::from(digit))?;
        }
        Self::from_raw(n)
    }
}

impl fmt::Display for SnowflakeId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// Error returned when parsing a decimal ID string fails.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ParseIdError(String);

impl fmt::Display for ParseIdError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "invalid snowflake id: {}", self.0)
    }
}

impl std::error::Error for ParseIdError {}

impl FromStr for SnowflakeId {
    type Err = ParseIdError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let raw: u64 = s
            .trim()
            .parse()
            .map_err(|e| ParseIdError(format!("{s:?}: {e}")))?;
        Self::from_raw(raw).ok_or_else(|| ParseIdError(format!("{s:?}: sign bit set")))
    }
}

impl From<SnowflakeId> for u64 {
    fn from(id: SnowflakeId) -> u64 {
        id.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pack_unpack_roundtrip() {
        let id = SnowflakeId::from_parts(123_456_789, 513, 4001).unwrap();
        assert_eq!(
            id.parts(),
            Parts {
                timestamp: 123_456_789,
                node_id: 513,
                sequence: 4001
            }
        );
    }

    #[test]
    fn extreme_values_roundtrip() {
        let id = SnowflakeId::from_parts(MAX_TIMESTAMP, MAX_NODE_ID, MAX_SEQUENCE as u16).unwrap();
        assert_eq!(id.as_u64(), i64::MAX as u64, "all 63 payload bits set");
        assert!(id.as_i64() > 0);
        assert_eq!(id.timestamp(), MAX_TIMESTAMP);
        assert_eq!(id.node_id(), MAX_NODE_ID);
        assert_eq!(id.sequence(), MAX_SEQUENCE as u16);
    }

    #[test]
    fn out_of_range_fields_rejected() {
        assert!(SnowflakeId::from_parts(MAX_TIMESTAMP + 1, 0, 0).is_none());
        assert!(SnowflakeId::from_parts(0, MAX_NODE_ID + 1, 0).is_none());
        assert!(SnowflakeId::from_parts(0, 0, 4096).is_none());
        assert!(SnowflakeId::from_raw(1 << 63).is_none());
    }

    #[test]
    fn ordering_follows_timestamp_first() {
        let a = SnowflakeId::from_parts(10, 1023, 4095).unwrap();
        let b = SnowflakeId::from_parts(11, 0, 0).unwrap();
        assert!(a < b);
    }

    #[test]
    fn decimal_parse_and_display() {
        let id = SnowflakeId::from_parts(42, 7, 3).unwrap();
        let s = id.to_string();
        assert_eq!(s.parse::<SnowflakeId>().unwrap(), id);
        assert!("abc".parse::<SnowflakeId>().is_err());
        assert!("18446744073709551615".parse::<SnowflakeId>().is_err()); // sign bit
    }

    #[test]
    fn base62_roundtrip() {
        for raw in [0u64, 1, 61, 62, 3843, 1 << 40, i64::MAX as u64] {
            let id = SnowflakeId::from_raw(raw).unwrap();
            let enc = id.to_base62();
            assert!(enc.len() <= 11);
            assert_eq!(
                SnowflakeId::from_base62(&enc),
                Some(id),
                "raw={raw} enc={enc}"
            );
        }
        assert_eq!(SnowflakeId::from_base62(""), None);
        assert_eq!(SnowflakeId::from_base62("hello-world"), None);
        assert_eq!(SnowflakeId::from_base62("zzzzzzzzzzzz"), None); // overflow
    }
}
