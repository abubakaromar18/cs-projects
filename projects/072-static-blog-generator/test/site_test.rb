# frozen_string_literal: true

require "test_helper"

class SiteTest < Minitest::Test
  include TestHelpers

  def post_md(title, tags: [], draft: false)
    "---\ntitle: #{title}\ntags: #{tags.inspect}\ndraft: #{draft}\n---\nAbout #{title}.\n"
  end

  def sample_files
    {
      "site.yml" => "title: Test Blog\nauthor: Ada\nper_page: 2\nbase_url: https://ex.com\n",
      "content/posts/2026-01-01-first.md" => post_md("First", tags: %w[ruby]),
      "content/posts/2026-02-01-second.md" => post_md("Second <&>", tags: %w[ruby web]),
      "content/posts/2026-03-01-third.md" => post_md("Third"),
      "content/posts/2026-04-01-secret.md" => post_md("Secret", draft: true),
      "content/pages/about.md" => "# About me\n",
      "static/style.css" => "body{}",
      "static/img/logo.svg" => "<svg/>"
    }
  end

  def test_build_writes_expected_files
    with_site(sample_files) do |dir|
      files = StaticBlog::Site.new(dir).build
      assert_equal %w[
        2026/01/first/index.html 2026/02/second/index.html 2026/03/third/index.html
        about/index.html feed.xml img/logo.svg index.html page/2/index.html style.css
        tags/ruby/index.html tags/web/index.html
      ], files
      assert File.exist?(File.join(dir, "_site/index.html"))
    end
  end

  def test_posts_newest_first_and_drafts_hidden
    with_site(sample_files) do |dir|
      site = StaticBlog::Site.new(dir).load
      assert_equal %w[third second first], site.posts.map(&:slug)
    end
  end

  def test_drafts_included_on_request
    with_site(sample_files) do |dir|
      site = StaticBlog::Site.new(dir, drafts: true).load
      assert_equal "secret", site.posts.first.slug
    end
  end

  def test_tags_index
    with_site(sample_files) do |dir|
      tags = StaticBlog::Site.new(dir).load.tags
      assert_equal %w[ruby web], tags.keys
      assert_equal %w[second first], tags["ruby"].map(&:slug)
    end
  end

  def test_pagination_links
    with_site(sample_files) do |dir|
      StaticBlog::Site.new(dir).build
      page1 = File.read(File.join(dir, "_site/index.html"))
      page2 = File.read(File.join(dir, "_site/page/2/index.html"))
      assert_includes page1, %(href="/page/2/")
      assert_includes page1, "Page 1 of 2"
      assert_includes page2, %(rel="prev" href="/")
      assert_includes page2, "First"
      refute_includes page1, ">First<"
    end
  end

  def test_titles_are_escaped_in_templates
    with_site(sample_files) do |dir|
      StaticBlog::Site.new(dir).build
      html = File.read(File.join(dir, "_site/2026/02/second/index.html"))
      assert_includes html, "<h1>Second &lt;&amp;&gt;</h1>"
      refute_includes html, "Second <&>"
    end
  end

  def test_post_navigation_links_neighbours
    with_site(sample_files) do |dir|
      StaticBlog::Site.new(dir).build
      html = File.read(File.join(dir, "_site/2026/02/second/index.html"))
      assert_includes html, %(href="/2026/01/first/")
      assert_includes html, %(href="/2026/03/third/")
    end
  end

  def test_layout_lists_pages_in_nav
    with_site(sample_files) do |dir|
      StaticBlog::Site.new(dir).build
      assert_includes File.read(File.join(dir, "_site/index.html")), %(<a href="/about/">About me</a>)
    end
  end

  def test_base_path_prefixes_urls
    files = sample_files.merge("site.yml" => "title: T\nbase_path: /blog/\n")
    with_site(files) do |dir|
      StaticBlog::Site.new(dir).build
      html = File.read(File.join(dir, "_site/index.html"))
      assert_includes html, %(href="/blog/style.css")
      assert_includes html, %(href="/blog/2026/03/third/")
    end
  end

  def test_feed_is_valid_atom
    with_site(sample_files) do |dir|
      StaticBlog::Site.new(dir).build
      xml = File.read(File.join(dir, "_site/feed.xml"))
      require "rexml/document"
      doc = REXML::Document.new(xml)
      entries = REXML::XPath.match(doc, "//entry")
      assert_equal 3, entries.size
      assert_equal "https://ex.com/2026/03/third/", entries.first.elements["id"].text
      assert_equal "Second <&>", entries[1].elements["title"].text
      assert_equal "2026-03-01T00:00:00Z", doc.root.elements["updated"].text
    rescue LoadError
      skip "rexml not available"
    end
  end

  def test_empty_site_still_builds
    with_site("site.yml" => "title: Empty\n") do |dir|
      files = StaticBlog::Site.new(dir).build
      assert_equal %w[feed.xml index.html], files
      assert_includes File.read(File.join(dir, "_site/index.html")), "No posts yet"
    end
  end

  def test_slug_collisions_are_reported
    files = { "content/posts/2026-01-01-a.md" => "x", "content/posts/2026-01-02-b.md" => "---\nslug: a\n---\n" }
    with_site(files) do |dir|
      err = assert_raises(ArgumentError) { StaticBlog::Site.new(dir).load }
      assert_match(/both write/, err.message)
    end
  end

  def test_rebuild_removes_stale_output
    with_site(sample_files) do |dir|
      site = StaticBlog::Site.new(dir)
      site.build
      File.delete(File.join(dir, "content/posts/2026-01-01-first.md"))
      StaticBlog::Site.new(dir).build
      refute File.exist?(File.join(dir, "_site/2026/01/first/index.html"))
    end
  end

  def test_example_site_builds
    Dir.mktmpdir do |out|
      files = StaticBlog::Site.new(TestHelpers::EXAMPLE_ROOT, output_dir: out).build
      assert_includes files, "index.html"
      refute files.any? { |f| f.include?("unfinished-thoughts") }, "drafts must not be published"
    end
  end
end
