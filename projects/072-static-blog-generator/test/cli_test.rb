# frozen_string_literal: true

require "test_helper"


class CLITest < Minitest::Test
  include TestHelpers

  def run_cli(*args, today: Date.new(2026, 11, 25))
    out, err = StringIO.new, StringIO.new
    status = StaticBlog::CLI.new(args, out: out, err: err, today: today).run
    [status, out.string, err.string]
  end

  def test_help
    status, out, = run_cli("--help")
    assert_equal 0, status
    assert_includes out, "Usage: blog"
  end

  def test_unknown_command
    status, _, err = run_cli("explode")
    assert_equal 2, status
    assert_includes err, "Unknown command"
  end

  def test_new_creates_draft_post
    with_site do |dir|
      status, out, = run_cli("new", "Hello, World!", "-s", dir)
      assert_equal 0, status
      path = File.join(dir, "content/posts/2026-11-25-hello-world.md")
      assert_includes out, path
      meta, = StaticBlog::FrontMatter.parse(File.read(path))
      assert_equal "Hello, World!", meta[:title]
      assert_equal true, meta[:draft]
    end
  end

  def test_new_refuses_to_overwrite
    with_site do |dir|
      run_cli("new", "Dup", "-s", dir)
      status, _, err = run_cli("new", "Dup", "-s", dir)
      assert_equal 1, status
      assert_includes err, "already exists"
    end
  end

  def test_new_requires_title
    status, _, err = run_cli("new")
    assert_equal 1, status
    assert_includes err, "title"
  end

  def test_build_reports_counts
    with_site("content/posts/2026-01-01-a.md" => "---\ntags: [x]\n---\nHi") do |dir|
      status, out, = run_cli("build", "-s", dir)
      assert_equal 0, status
      assert_match(/Built 1 posts, 0 pages, 1 tags -> 4 files/, out)
    end
  end

  def test_build_surfaces_content_errors
    with_site("content/posts/2026-01-01-a.md" => "---\ntitle: [oops\n---\n") do |dir|
      status, _, err = run_cli("build", "-s", dir)
      assert_equal 1, status
      assert_includes err, "invalid YAML"
    end
  end
end
