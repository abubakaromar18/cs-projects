# frozen_string_literal: true

require "test_helper"

class MarkdownTest < Minitest::Test
  def md(src) = StaticBlog::Markdown.render(src)

  def test_paragraphs_are_separated_by_blank_lines
    assert_equal "<p>one\ntwo</p>\n<p>three</p>\n", md("one\ntwo\n\nthree")
  end

  def test_headings_get_slug_ids
    assert_equal %(<h2 id="hello-world">Hello, World!</h2>\n), md("## Hello, World!")
  end

  def test_duplicate_heading_ids_are_suffixed
    html = md("## Intro\n\n## Intro\n\n## Intro")
    assert_includes html, 'id="intro"'
    assert_includes html, 'id="intro-1"'
    assert_includes html, 'id="intro-2"'
  end

  def test_closing_hashes_are_stripped
    assert_equal %(<h1 id="title">Title</h1>\n), md("# Title ##")
  end

  def test_headings_are_collected_for_toc
    m = StaticBlog::Markdown.new("# A\n\n## B `c`\n")
    m.to_html
    assert_equal [[1, "A", "a"], [2, "B c", "b-c"]], m.headings.map(&:to_a)
  end

  def test_fenced_code_is_escaped_and_not_parsed
    html = md("```ruby\nputs \"<b>**not bold**</b>\"\n```")
    assert_equal %(<pre><code class="language-ruby">puts &quot;&lt;b&gt;**not bold**&lt;/b&gt;&quot;</code></pre>\n), html
  end

  def test_unterminated_fence_runs_to_end
    assert_includes md("~~~\ncode"), "<pre><code>code</code></pre>"
  end

  def test_unordered_list
    assert_equal "<ul>\n  <li>a</li>\n  <li><em>b</em></li>\n</ul>\n", md("- a\n* *b*")
  end

  def test_ordered_list_keeps_start_number
    assert_equal %(<ol start="3">\n  <li>x</li>\n  <li>y</li>\n</ol>\n), md("3. x\n4. y")
  end

  def test_list_item_continuation_lines
    assert_includes md("- first\n  continued\n- second"), "<li>first continued</li>"
  end

  def test_blockquote_contains_blocks
    html = md("> # Quote\n> body")
    assert_includes html, "<blockquote>"
    assert_includes html, %(<h1 id="quote">Quote</h1>)
    assert_includes html, "<p>body</p>"
  end

  def test_horizontal_rule
    assert_equal "<p>a</p>\n<hr>\n<p>b</p>\n", md("a\n\n---\n\nb")
  end

  def test_heading_interrupts_paragraph
    assert_equal %(<p>text</p>\n<h2 id="h">H</h2>\n), md("text\n## H")
  end

  def test_strong_and_emphasis
    assert_equal "<p><strong>bold</strong> and <em>it</em> and <em>u</em></p>\n", md("**bold** and *it* and _u_")
  end

  def test_intraword_underscores_are_literal
    assert_equal "<p>snake_case_name</p>\n", md("snake_case_name")
  end

  def test_code_span_protects_markup
    assert_equal "<p><code>**x** &lt;y&gt;</code></p>\n", md("`**x** <y>`")
  end

  def test_double_backtick_code_span_can_contain_backtick
    assert_equal "<p><code>a ` b</code></p>\n", md("`` a ` b ``")
  end

  def test_links_and_images
    html = md(%(![cat](/cat.png "A cat") see [docs](https://example.com/a?b=1&c=2)))
    assert_includes html, %(<img src="/cat.png" alt="cat" title="A cat">)
    assert_includes html, %(<a href="https://example.com/a?b=1&amp;c=2">docs</a>)
  end

  def test_raw_html_is_escaped
    assert_equal "<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>\n", md("<script>alert(1)</script>")
  end

  def test_javascript_urls_are_dropped
    assert_equal "<p>click</p>\n", md("[click](javascript:alert(1))")
    refute_includes md("![x](data:text/html,hi)"), "<img"
  end

  def test_urls_with_balanced_parentheses
    assert_includes md("[w](https://en.wikipedia.org/wiki/Ruby_(language))"),
                    %(<a href="https://en.wikipedia.org/wiki/Ruby_(language)">w</a>)
  end

  def test_relative_urls_are_allowed
    assert_includes md("[about](about/)"), %(<a href="about/">about</a>)
    assert_includes md("[top](#top)"), %(<a href="#top">top</a>)
  end

  def test_backslash_escapes
    assert_equal "<p>*not em*</p>\n", md("\\*not em\\*")
  end

  def test_hard_line_break
    assert_equal "<p>a<br>\nb</p>\n", md("a  \nb")
  end

  def test_crlf_input
    assert_equal "<p>a</p>\n<p>b</p>\n", md("a\r\n\r\nb")
  end

  def test_empty_input
    assert_equal "\n", md("")
  end

  def test_excerpt_skips_headings_and_strips_markup
    m = StaticBlog::Markdown.new("# Title\n\nThe **first** [para](/x).\n\nSecond.")
    assert_equal "The first para.", m.excerpt
  end

  def test_excerpt_truncates_on_word_boundary_ish
    m = StaticBlog::Markdown.new("word " * 100)
    assert_operator m.excerpt(20).length, :<=, 21
    assert m.excerpt(20).end_with?("…")
  end
end
