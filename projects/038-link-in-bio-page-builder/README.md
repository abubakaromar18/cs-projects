# Link-in-Bio Page Builder

A small SvelteKit app for building a shareable profile page: pick an address, add links, choose a theme and watch a live preview as you edit. Published pages count link clicks. No account is needed, because each page has its own private edit link.

## CS concepts

- **Server-side rendering and hydration:** pages arrive as complete HTML, then Svelte takes over in the browser.
- **Progressive enhancement:** form actions work as plain HTML posts, and `use:enhance` upgrades them when JavaScript is available. Editing the link list itself needs JavaScript.
- **Reactive state:** Svelte 5 runes (`$state`, `$derived`) drive the editor, and the preview reuses the public page's component.
- **Capability URLs:** a 192-bit random token in the edit link is the credential. Only its SHA-256 hash is stored.
- **Web security:**
  - An allow-list of `http` and `https` URLs blocks `javascript:` links and URLs that hide their host behind credentials.
  - Svelte escapes output, and a Content Security Policy backs that up.
  - SvelteKit's Origin check stops cross-site form posts.
  - `Referrer-Policy` keeps edit links out of Referer headers.
- **Concurrency and durability:** store writes run one at a time on a promise queue, so simultaneous clicks aren't lost. Each write goes to a temp file and is renamed into place, so a crash can't leave half a file.

## Build, run and test

Requires Node 20 or newer.

```sh
npm install

npm run dev                # development server at http://localhost:5173
npm test                   # unit and component tests (Vitest)
npm run test:e2e           # builds, then tests the real server over HTTP (macOS/Linux shell)

npm run build              # production build
npm start                  # serves it at http://localhost:3000
```

**Deploying somewhere other than `localhost:3000`:** set the public origin when you build, or the Origin check will refuse form posts with a 403.

```sh
ORIGIN=https://links.example.org npm run build
```

| Runtime variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `3000` | Port to listen on |
| `HOST` | `0.0.0.0` | Address to bind |
| `DATA_FILE` | `data/pages.json` | Where pages are stored |

## Example

1. Open `/`, enter `ada-lovelace` and `Ada Lovelace`, and select **Create my page**.
2. You land on `/edit/<secret-token>`. Bookmark it, because it can't be recovered.
3. Add links and pick a theme, then select **Save changes**.
4. Share `/ada-lovelace`. Each link goes through `/ada-lovelace/go/<link-id>`, which counts the click and redirects.

A stored page looks like this:

```json
{
  "slug": "ada-lovelace",
  "tokenHash": "9f2c…",
  "displayName": "Ada Lovelace",
  "bio": "First programmer",
  "theme": "midnight",
  "links": [
    { "id": "6f1e…", "title": "Notes", "url": "https://example.com/notes", "clicks": 3 }
  ]
}
```

## Project layout

```text
src/lib/profile.js                 validation and pure helpers
src/lib/themes.js                  theme list (colors are in src/app.css)
src/lib/server/store.js            JSON document store
src/lib/server/tokens.js           edit token creation and hashing
src/lib/components/ProfileCard.svelte   shared by public page and preview
src/routes/+page.*                 create a page
src/routes/[slug]/                 public page and click-counting redirect
src/routes/edit/[token]/           editor
tests/                             Vitest unit and component tests
e2e/                               HTTP tests against the production build
```

## Limitations

- The JSON store suits one server process. Running several would need a real database.
- A lost edit link can't be recovered.
- Click counts include bots and repeat visits.

## Possible extensions

- Move storage to SQLite, keeping the same store interface.
- Add avatar uploads with image resizing.
- Add email-based recovery for edit links.
- Add rate limiting on page creation.
- Add drag-and-drop link ordering and daily click charts.
