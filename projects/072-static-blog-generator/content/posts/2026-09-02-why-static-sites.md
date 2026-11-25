---
title: Why Static Sites Are Back
tags: [web, architecture]
---
Static sites trade runtime flexibility for speed, security and simplicity.
When every page is a file, the "server" is just a CDN.

## The trade-off

A dynamic CMS renders on every request. A static generator renders **once**,
at build time, so the work moves from the hot path to the developer's laptop.

## What you give up

1. Per-request personalisation
2. Server-side search
3. Comments, unless you embed a third-party service

## What you get

> The fastest code is the code that never runs.

Caching becomes trivial, the attack surface shrinks to "a web server serving
files", and the whole site fits in `git`.
