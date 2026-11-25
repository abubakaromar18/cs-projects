# frozen_string_literal: true

# StaticBlog — a tiny static site generator: Markdown + YAML front matter in,
# ERB-templated HTML, tag pages, pagination and an Atom feed out.
module StaticBlog
  VERSION = "1.0.0"
end

require_relative "static_blog/front_matter"
require_relative "static_blog/markdown"
require_relative "static_blog/post"
require_relative "static_blog/renderer"
require_relative "static_blog/feed"
require_relative "static_blog/site"
require_relative "static_blog/server"
require_relative "static_blog/cli"
