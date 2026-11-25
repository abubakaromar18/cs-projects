---
title: Tags and Pagination
tags: [ruby, web]
---
Two features turn a pile of posts into a browsable blog.

**Tags** invert the post → tags relation into tag → posts, a one-line
`each_with_object` in Ruby. **Pagination** is `each_slice(per_page)` plus a
little bookkeeping for the previous and next links.
