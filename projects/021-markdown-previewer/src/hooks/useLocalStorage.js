import { useEffect, useRef, useState } from 'react';

/**
 * useState that persists to localStorage.
 *
 * Storage can be unavailable (private mode, blocked cookies, quota), so every
 * access is wrapped in try/catch and the hook silently degrades to plain
 * in-memory state. Writes are debounced so typing does not hit storage on
 * every keystroke.
 */
export function useLocalStorage(key, initialValue, { debounceMs = 300 } = {}) {
  const [value, setValue] = useState(() => {
    try {
      const raw = window.localStorage.getItem(key);
      return raw === null ? initialValue : JSON.parse(raw);
    } catch {
      return initialValue;
    }
  });

  const firstRender = useRef(true);
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return undefined;
    }
    const id = setTimeout(() => {
      try {
        window.localStorage.setItem(key, JSON.stringify(value));
      } catch {
        // Ignore: persistence is a convenience, not a requirement.
      }
    }, debounceMs);
    return () => clearTimeout(id);
  }, [key, value, debounceMs]);

  return [value, setValue];
}
