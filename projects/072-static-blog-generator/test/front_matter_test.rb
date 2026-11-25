# frozen_string_literal: true

require "test_helper"

class FrontMatterTest < Minitest::Test
  FM = StaticBlog::FrontMatter

  def test_parses_yaml_and_returns_body
    meta, body = FM.parse("---\ntitle: Hi\ndate: 2026-01-02\ntags: [a, b]\n---\nBody\n")
    assert_equal({ title: "Hi", date: Date.new(2026, 1, 2), tags: %w[a b] }, meta)
    assert_equal "Body\n", body
  end

  def test_no_front_matter
    assert_equal [{}, "just text"], FM.parse("just text")
  end

  def test_empty_front_matter
    assert_equal [{}, "x"], FM.parse("---\n\n---\nx")
  end

  def test_non_mapping_is_an_error
    assert_raises(FM::ParseError) { FM.parse("---\n- a\n- b\n---\n") }
  end

  def test_invalid_yaml_is_an_error
    assert_raises(FM::ParseError) { FM.parse("---\ntitle: [unclosed\n---\n") }
  end

  def test_unsafe_yaml_tags_are_rejected
    assert_raises(Psych::DisallowedClass) { FM.parse("---\nx: !ruby/object:Object {}\n---\n") }
  end
end
