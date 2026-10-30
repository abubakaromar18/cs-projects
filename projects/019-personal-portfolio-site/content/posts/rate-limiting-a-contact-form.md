---
title: Rate Limiting a Contact Form
date: 2026-10-20
summary: A sliding-window limiter and a honeypot keep spam out without CAPTCHAs.
tags: [security, algorithms]
---

Contact forms attract bots. Two cheap defences go a long way.

## Sliding-window rate limiting

For each IP, keep the timestamps of recent submissions. On a new request, drop
timestamps older than the window; if what's left is at the limit, reject with
**HTTP 429** and a `Retry-After` header.

Compared with a *fixed* window, a sliding window avoids the burst where a client
sends the full quota at 11:59 and again at 12:00.

## Honeypot fields

A hidden `website` input is invisible to people but tempting to bots. If it's
filled in, the server pretends to succeed and quietly drops the message.
