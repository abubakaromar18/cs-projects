---
title: Writing a Markdown Parser
tags: [ruby, parsing]
summary: Two passes, one state machine and a handful of regular expressions.
---
Markdown looks simple until you try to parse it. The trick is to split the
job in two.

## Pass one: blocks

Walk the file line by line. Each line either *starts* a block (a `#`
heading, a `-` list item, a ```` ``` ```` fence) or *continues* the current
one. This is a classic state machine.

## Pass two: inlines

Inside each block, find code spans first and set them aside, escape the
rest, then apply links, **strong** and *emphasis*.

## Safety

Links are checked against an allow-list of schemes, so
`[x](javascript:alert(1))` renders as plain text.

## Further reading

See the [CommonMark spec](https://spec.commonmark.org/) for the full,
gloriously detailed rules.
