# 019 · Personal Portfolio Site

A personal portfolio built with **Next.js 15 (App Router)**, **React 19** and **TypeScript**:
a home page, a filterable projects page, a Markdown-powered blog, and a contact form
backed by a validated, rate-limited API route. No database, no third-party services,
no secrets: it runs immediately after `npm install`.

**Level:** Starter · **Area:** Full-Stack Apps

## Features

- **Home**: hero, skills, featured projects and the three latest posts.
- **Projects**: cards with tech chips, source/demo links, and a `?tech=` filter kept
  in the URL so filtered views are shareable and work without JavaScript.
- **Blog**: posts are plain `.md` files in `content/posts/` with front matter.
  They are pre-rendered at build time, include reading-time estimates, and skip drafts.
- **Contact form**: client-side validation for instant feedback, the same rules
  enforced on the server, a honeypot spam trap, and a sliding-window rate limit
  (5 messages / 10 min / IP, answered with `429` + `Retry-After`).
- Accessible markup (skip link, `aria-current`, `aria-invalid`, labelled fields),
  responsive layout, and automatic dark mode.

## CS concepts demonstrated

| Concept | Where |
|---|---|
| **Parsing / tokenising**: a line-oriented front-matter grammar with typed scalars | `lib/frontmatter.ts` |
| **State machines**: a block-level Markdown renderer (paragraph, list, quote and code-fence states) | `lib/markdown.ts` |
| **Injection safety**: escape-then-format, plus a URL-scheme allowlist that blocks `javascript:` links | `lib/markdown.ts` |
| **Sliding-window rate limiting**: O(limit) memory per key, with sweeping of idle keys | `lib/rateLimit.ts` |
| **Shared validation**: one module used by the browser and the server, with the server authoritative | `lib/validation.ts` |
| **Dependency injection / ports & adapters**: the request handler is framework-agnostic and takes a pluggable `MessageStore` | `lib/contactHandler.ts`, `lib/messageStore.ts` |
| **Rendering strategies**: static (`○`), SSG with `generateStaticParams` (`●`), and dynamic (`ƒ`) routes | `app/` |
| **Server vs client components**: only the nav and form ship JS to the browser | `components/` |

## Project structure

```
app/
  layout.tsx            root layout, nav, footer, metadata
  page.tsx              home
  projects/page.tsx     filterable project grid (?tech=...)
  blog/page.tsx         post index
  blog/[slug]/page.tsx  statically generated post pages
  contact/page.tsx      contact page
  api/contact/route.ts  POST endpoint (thin adapter over lib/contactHandler)
components/             Nav, ProjectCard, PostList, ContactForm (client)
content/posts/*.md      blog posts
data/site.ts            name, bio, links and skills (edit me)
data/projects.ts        project list + filter helpers
lib/                    frontmatter, markdown, posts, validation, rateLimit, store, handler
tests/                  Vitest unit and integration tests
```

## Build, run, test

Requires Node.js 18.18 or newer.

```bash
npm install
npm run dev        # http://localhost:3000 with hot reload
npm test           # 37 Vitest tests
npm run typecheck  # tsc --noEmit
npm run build      # production build
npm start          # serve the production build
```

### Example: the contact API

```bash
$ curl -X POST localhost:3000/api/contact -H 'content-type: application/json' \
    -d '{"name":"Ada","email":"ada@example.com","message":"Loved your markdown post!"}'
{"ok":true,"id":"msg_1"}

$ curl -X POST localhost:3000/api/contact -d '{"name":"","email":"x","message":"hi"}'
{"ok":false,"errors":{"name":"Please enter your name.","email":"Please enter a valid email address.","message":"Message must be at least 10 characters."}}

# the 6th request inside 10 minutes from the same IP:
HTTP/1.1 429 Too Many Requests
Retry-After: 597
```

### Example: build output

```
Route (app)                    Size  First Load JS
┌ ○ /                         161 B         106 kB
├ ƒ /api/contact              127 B         103 kB
├ ○ /blog                     170 B         106 kB
├ ● /blog/[slug]              170 B         106 kB
├   ├ /blog/rate-limiting-a-contact-form
├   ├ /blog/how-this-blog-renders-markdown
├   └ /blog/hello-world
├ ○ /contact                 1.35 kB        104 kB
└ ƒ /projects                 170 B         106 kB
```

### Writing a post

Create `content/posts/my-post.md`. The file name becomes the slug.

```markdown
---
title: My Post
date: 2026-11-01
summary: One line for the index page.
tags: [nextjs, notes]
draft: false
---

## Supports headings, **bold**, *italic*, `code`, [links](https://example.com),
lists, > quotes, --- rules and fenced code blocks.
```

## Making it yours

1. Edit `data/site.ts` (name, tagline, links, skills) and `data/projects.ts`.
2. Replace the sample posts in `content/posts/`.
3. To actually receive messages, implement `MessageStore` with an email provider
   or database, and keep credentials in `.env.local` (git-ignored).

## Possible extensions

- Email delivery via Resend/SES, with an admin page listing stored messages.
- RSS/Atom feed and `sitemap.xml` generated from posts.
- Tag pages (`/blog/tags/[tag]`) and full-text search over posts.
- Syntax highlighting for code blocks (Shiki) at build time.
- Open Graph images per post with `next/og`.
- Redis-backed rate limiting for multi-instance deployments.
- Playwright end-to-end tests for the contact flow.
