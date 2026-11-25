# frozen_string_literal: true

require "test_helper"

class PostTest < Minitest::Test
  def post(name, src, kind: :post) = StaticBlog::Post.new("/x/#{name}", src, kind: kind)

  def test_date_and_slug_from_filename
    p = post("2026-03-04-Hello-World.md", "Hi")
    assert_equal Date.new(2026, 3, 4), p.date
    assert_equal "hello-world", p.slug
    assert_equal "2026/03/hello-world/index.html", p.output_path
    assert_equal "/2026/03/hello-world/", p.url
  end

  def test_front_matter_overrides_filename
    p = post("2026-03-04-a.md", "---\ndate: 2025-12-31\nslug: custom\n---\n")
    assert_equal Date.new(2025, 12, 31), p.date
    assert_equal "custom", p.slug
  end

  def test_title_falls_back_to_first_h1_then_slug
    assert_equal "From H1", post("2026-01-01-x.md", "# From *H1*\n").title
    assert_equal "Some slug", post("2026-01-01-some-slug.md", "text").title
  end

  def test_tags_are_normalised
    p = post("2026-01-01-x.md", "---\ntags: [Ruby, ' web ', ruby]\n---\n")
    assert_equal %w[ruby web], p.tags
  end

  def test_single_tag_string
    assert_equal %w[solo], post("2026-01-01-x.md", "---\ntags: solo\n---\n").tags
  end

  def test_post_without_date_is_an_error
    assert_raises(ArgumentError) { post("undated.md", "x") }
  end

  def test_bad_date_is_an_error
    assert_raises(ArgumentError) { post("x.md", "---\ndate: tomorrow\n---\n") }
  end

  def test_pages_do_not_need_dates
    page = post("about.md", "# About", kind: :page)
    assert_nil page.date
    assert_equal "about/index.html", page.output_path
  end

  def test_reading_time
    assert_equal 1, post("2026-01-01-x.md", "short").reading_minutes
    assert_equal 3, post("2026-01-01-x.md", "word " * 401).reading_minutes
  end

  def test_summary_from_meta_or_excerpt
    assert_equal "Given", post("2026-01-01-x.md", "---\nsummary: Given\n---\nBody").summary
    assert_equal "Body text.", post("2026-01-01-x.md", "Body text.").summary
  end

  def test_draft_flag
    assert post("2026-01-01-x.md", "---\ndraft: true\n---\n").draft?
    refute post("2026-01-01-x.md", "x").draft?
  end
end
