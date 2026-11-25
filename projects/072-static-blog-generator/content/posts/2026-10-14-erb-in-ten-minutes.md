---
title: ERB in Ten Minutes
tags: [ruby, templates]
---
ERB (Embedded Ruby) is Ruby's built-in templating language. It turns a text
file with `<%= %>` tags into a Ruby method that builds a string.

## The three tags

- `<% code %>` runs Ruby and outputs nothing
- `<%= expr %>` outputs the value of `expr`
- `<%# comment %>` is ignored

## Compiling a template

```ruby
require "erb"
template = ERB.new("Hello, <%= name %>!")
name = "world"
puts template.result(binding)   # => Hello, world!
```

## Bindings

A *binding* captures local variables, `self` and the block of a method call.
StaticBlog hands each template a binding from a small `Context` object, so
templates see `@post`, `site` and helpers like `h()` and nothing else.

## Escaping

Always escape user data with `CGI.escapeHTML` (StaticBlog's `h` helper) —
otherwise a title like `<script>` becomes code.
