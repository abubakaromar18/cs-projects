/** Starter document shown on first load (and after "Reset"). */
export const SAMPLE_MARKDOWN = `# Markdown Previewer

Type on the left, see the result on the right. Your text is saved in this
browser automatically.

## Inline formatting

You can write **bold**, *italic*, ***both***, ~~strikethrough~~ and \`inline code\`.
Links look like [this](https://commonmark.org "CommonMark") and
autolinks like <https://spec.commonmark.org>.

## Lists

- Unordered items
- Can nest
  - like this
  - and this
- [x] Task lists work
- [ ] So do unchecked tasks

1. Ordered lists
2. Count up
3. Automatically

## Code

\`\`\`js
function greet(name) {
  return \`Hello, \${name}!\`;
}
\`\`\`

## Quotes and tables

> Markdown is intended to be as easy-to-read and easy-to-write as is feasible.

| Shortcut       | Action        |
| :------------- | :-----------: |
| Ctrl/⌘ + B     | Bold          |
| Ctrl/⌘ + I     | Italic        |
| Ctrl/⌘ + K     | Insert link   |
| Tab            | Indent        |

---

Use **Export HTML** to download a standalone page.
`;
