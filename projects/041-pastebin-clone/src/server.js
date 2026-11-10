/**
 * Entry point: start the pastebin on localhost.
 *
 *   PORT=3000 HOST=127.0.0.1 npm start
 */
import { createApp } from './app.js';
import { PasteStore } from './store.js';

const port = Number(process.env.PORT) || 3000;
// Bind to loopback by default; set HOST=0.0.0.0 deliberately to expose it.
const host = process.env.HOST || '127.0.0.1';

const store = new PasteStore({ maxPastes: Number(process.env.MAX_PASTES) || 10_000 });
const app = createApp({ store, sweepIntervalMs: 60_000 });

const server = app.listen(port, host, () => {
  console.log(`Pastebin listening on http://${host}:${port}`);
});

// Graceful shutdown so Ctrl-C / container stops finish in-flight requests.
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    console.log(`\n${signal} received, shutting down`);
    server.close(() => process.exit(0));
  });
}
