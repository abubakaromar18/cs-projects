export function StatusBar({ stats, message }) {
  return (
    <footer className="status-bar">
      <span>
        {stats.words} {stats.words === 1 ? 'word' : 'words'} · {stats.characters} characters · {stats.readingMinutes} min
        read
      </span>
      <span role="status" aria-live="polite" className="status-message">
        {message}
      </span>
    </footer>
  );
}
