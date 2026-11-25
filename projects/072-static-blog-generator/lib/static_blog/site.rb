# frozen_string_literal: true

require "fileutils"
require "yaml"
require "time"

module StaticBlog
  # Loads a site's content, renders it and writes the output tree.
  #
  #   site/
  #     site.yml              title, author, base_url, per_page ...
  #     content/posts/*.md    2026-11-25-hello.md
  #     content/pages/*.md    about.md
  #     templates/*.html.erb  layout, index, post, page, tag, _post_card
  #     static/               copied verbatim
  #
  # Build is a pure function of the inputs: output is wiped and regenerated,
  # and posts are processed in a deterministic order.
  class Site
    DEFAULTS = {
      "title" => "My Blog",
      "description" => "",
      "author" => "Anonymous",
      "base_url" => "http://localhost:4000",
      "base_path" => "",
      "per_page" => 5,
      "drafts" => false
    }.freeze

    attr_reader :root, :config, :posts, :pages, :output_dir

    def initialize(root, output_dir: nil, drafts: nil)
      @root = File.expand_path(root)
      cfg_path = File.join(@root, "site.yml")
      user_cfg = File.exist?(cfg_path) ? (YAML.safe_load_file(cfg_path) || {}) : {}
      @config = DEFAULTS.merge(user_cfg)
      @config["drafts"] = drafts unless drafts.nil?
      @output_dir = File.expand_path(output_dir || File.join(@root, "_site"))
    end

    def title = config["title"]
    def description = config["description"]
    def author = config["author"]

    def url_for(path) = "#{config['base_path'].chomp('/')}#{path}"
    def absolute_url(path) = "#{config['base_url'].chomp('/')}#{url_for(path)}"

    # Reads every source file. Separate from #build so tests can inspect.
    def load
      @posts = glob("content/posts").map { |f| Post.load(f, kind: :post) }
      @posts.reject!(&:draft?) unless config["drafts"]
      # Newest first; slug breaks ties so the order is stable.
      @posts.sort_by! { |p| [-p.date.jd, p.slug] }
      @pages = glob("content/pages").map { |f| Post.load(f, kind: :page) }.sort_by(&:slug)
      check_collisions!
      self
    end

    # tag => [posts], tags sorted alphabetically.
    def tags
      posts.each_with_object(Hash.new { |h, k| h[k] = [] }) { |p, acc| p.tags.each { |t| acc[t] << p } }
           .sort.to_h
    end

    # Writes the whole site; returns the list of files written (relative).
    def build
      load if posts.nil?
      FileUtils.rm_rf(output_dir)
      @written = []
      renderer = Renderer.new(File.join(root, "templates"), site: self)

      posts.each_with_index do |post, i|
        # posts are newest-first, so "newer" is the previous index.
        newer = i.positive? ? posts[i - 1] : nil
        older = posts[i + 1]
        write(post.output_path, renderer.render("post", post: post, newer: newer, older: older))
      end

      pages.each { |page| write(page.output_path, renderer.render("page", page: page)) }

      paginate(posts).each do |pager|
        path = pager[:number] == 1 ? "index.html" : "page/#{pager[:number]}/index.html"
        write(path, renderer.render("index", posts: pager[:posts], pager: pager))
      end

      tags.each do |tag, tagged|
        write("tags/#{tag}/index.html", renderer.render("tag", tag: tag, posts: tagged))
      end

      write("feed.xml", Feed.new(self).to_xml)
      copy_static
      @written.sort
    end

    private

    def glob(dir)
      Dir.glob(File.join(root, dir, "*.{md,markdown}")).sort
    end

    # Splits posts into pages of `per_page`, with prev/next URLs.
    def paginate(list)
      per = [config["per_page"].to_i, 1].max
      chunks = list.each_slice(per).to_a
      chunks = [[]] if chunks.empty?
      url = ->(n) { n == 1 ? url_for("/") : url_for("/page/#{n}/") }
      chunks.each_with_index.map do |chunk, idx|
        n = idx + 1
        { number: n, total: chunks.length, posts: chunk,
          prev_url: n > 1 ? url.call(n - 1) : nil,
          next_url: n < chunks.length ? url.call(n + 1) : nil }
      end
    end

    def check_collisions!
      seen = {}
      (posts + pages).each do |doc|
        if (other = seen[doc.output_path])
          raise ArgumentError, "#{doc.path} and #{other.path} both write #{doc.output_path}"
        end

        seen[doc.output_path] = doc
      end
    end

    def write(rel, contents)
      dest = File.join(output_dir, rel)
      FileUtils.mkdir_p(File.dirname(dest))
      File.write(dest, contents)
      @written << rel
    end

    def copy_static
      src = File.join(root, "static")
      return unless Dir.exist?(src)

      Dir.glob("**/*", File::FNM_DOTMATCH, base: src).sort.each do |rel|
        from = File.join(src, rel)
        next unless File.file?(from)

        dest = File.join(output_dir, rel)
        FileUtils.mkdir_p(File.dirname(dest))
        FileUtils.cp(from, dest)
        @written << rel
      end
    end
  end
end
