# 072 · Static Blog Generator

A small, dependency-free static site generator in plain Ruby. Write posts as Markdown with YAML front matter, lay them out with ERB templates, and `bin/blog build` turns the lot into a folder of HTML with tag pages, pagination, a table of contents and an Atom feed, ready to host anywhere that serves files.

The Markdown engine is written from scratch (no `kramdown`/`redcarpet`), so the whole pipeline is readable in about 800 lines.

```
content/posts/2026-11-01-writing-a-markdown-parser.md
        │  FrontMatter.parse  (YAML → metadata, rest → body)
        ▼
      Post ── Markdown (block pass → inline pass) ──► HTML + headings
        │
        ▼
   Renderer (ERB: post.html.erb wrapped in layout.html.erb)
        │
        ▼
_site/2026/11/writing-a-markdown-parser/index.html
```

## Features

- **Posts** named `YYYY-MM-DD-slug.md`; **pages** (`content/pages/about.md`) show up in the nav
- **YAML front matter**: `title`, `date`, `tags`, `summary`, `slug`, `draft`
- **Markdown**: headings (with slug ids), paragraphs, hard breaks, `-`/`*`/`+` and numbered lists, blockquotes, fenced code with language classes, rules, `code`, **strong**, *emphasis*, links, images, backslash escapes
- **Safe by default**: raw HTML is escaped, and `javascript:`/`data:` links are dropped
- **ERB templates** with a layout, partials and helpers (`h`, `url_for`, `format_date`, `tag_url`, `partial`)
- Pretty URLs (`/2026/11/slug/`), pagination (`/page/2/`), tag pages (`/tags/ruby/`), newer/older links, auto table of contents, reading time, excerpts
- Atom 1.0 feed at `/feed.xml`
- `base_path` setting for hosting in a subdirectory (e.g. GitHub Pages project sites)
- Drafts, hidden unless you pass `--drafts`
- `bin/blog new "Title"` scaffolds a post; `bin/blog serve` previews on `127.0.0.1` only
- Clear errors for bad YAML, bad dates and two files that would write the same URL

## CS concepts

- **Two-pass parsing.** A line-oriented *state machine* groups lines into blocks, then an inline scanner handles spans in each block. This is how real Markdown engines are built.
- **Tokenise, then protect.** Code spans and escapes are swapped out for placeholder tokens before HTML-escaping and regex rewriting, then swapped back in. This stops `**` inside `` `code` `` from turning bold.
- **Context-sensitive escaping and URL allow-listing** to prevent XSS. Text is escaped and URL schemes are checked against an allow-list.
- **Templates as compiled code.** ERB compiles each template into Ruby once (cached). It is evaluated against a `binding` from a `Context` object, which works as a sandboxed scope, and `yield` inside the layout calls back into the inner page.
- **Pure, deterministic builds.** The output is wiped and fully regenerated. Posts are sorted by `(date desc, slug)` so rebuilding identical input gives identical output.
- **Inverted index.** Tags turn the post → tags relation into tag → posts.
- **Pagination** with `each_slice` and prev/next bookkeeping.
- **A minimal HTTP/1.1 server** on `TCPServer`, with path-traversal protection (`File.expand_path` plus a prefix check, and NUL bytes rejected).
- **Safe deserialisation.** `YAML.safe_load` refuses arbitrary Ruby objects in front matter.

## Layout

```
bin/blog                    CLI entry point
lib/static_blog/
  front_matter.rb           YAML front matter splitter
  markdown.rb               Markdown → HTML (block + inline passes)
  post.rb                   one source file: metadata, URL, summary, reading time
  renderer.rb               ERB compile cache, layouts, partials, helpers
  site.rb                   load content, build output tree, tags, pagination
  feed.rb                   Atom feed
  server.rb                 localhost preview server
  cli.rb                    build / new / serve
templates/                  layout, index, post, page, tag, partials
content/                    example posts and pages
static/                     copied verbatim (style.css)
site.yml                    site configuration
test/                       Minitest suite (72 tests)
```

## Build, run, test

Requires Ruby ≥ 3.1. The generator uses only the standard library; `rake` and `minitest` ship with Ruby, and you can also get them with `bundle install`.

```sh
rake test                 # run the test suite
bin/blog build            # render the example site into _site/
bin/blog build --drafts   # include draft posts
bin/blog serve            # build, then open http://127.0.0.1:4000/
bin/blog new "My first post"
bin/blog build -s path/to/site -o /tmp/out
```

## Example

```
$ bin/blog build
Built 4 posts, 1 pages, 5 tags -> 14 files in 21 ms
Output: /…/072-static-blog-generator/_site

$ find _site -type f | sort
_site/2026/09/why-static-sites/index.html
_site/2026/10/erb-in-ten-minutes/index.html
_site/2026/11/tags-and-pagination/index.html
_site/2026/11/writing-a-markdown-parser/index.html
_site/about/index.html
_site/feed.xml
_site/index.html
_site/page/2/index.html
_site/style.css
_site/tags/architecture/index.html
_site/tags/parsing/index.html
_site/tags/ruby/index.html
_site/tags/templates/index.html
_site/tags/web/index.html
```

A post's source and output:

```markdown
---
title: Writing a Markdown Parser
tags: [ruby, parsing]
---
## Safety

Links are checked against an allow-list, so [x](javascript:alert(1)) is plain text.
```

```html
<h2 id="safety">Safety</h2>
<p>Links are checked against an allow-list, so x is plain text.</p>
```

## Configuration (`site.yml`)

| Key           | Default                 | Meaning                                  |
|---------------|-------------------------|------------------------------------------|
| `title`       | `My Blog`               | Site name in header, `<title>` and feed  |
| `description` | `""`                    | Default meta description                 |
| `author`      | `Anonymous`             | Footer and feed author                   |
| `base_url`    | `http://localhost:4000` | Used for absolute URLs in the feed       |
| `base_path`   | `""`                    | Prefix for every link, e.g. `/blog`      |
| `per_page`    | `5`                     | Posts per index page                     |
| `drafts`      | `false`                 | Publish `draft: true` posts              |

## Possible extensions

- Nested lists, tables and footnotes in the Markdown engine
- Syntax highlighting (e.g. with Rouge) for fenced code
- Incremental builds: hash each source and its templates and skip unchanged pages
- A file watcher that rebuilds and live-reloads while `serve` runs
- Yearly/monthly archive pages and a sitemap.xml
- Client-side search from a generated JSON index
- Theme support: pick a `templates/` directory from `site.yml`
