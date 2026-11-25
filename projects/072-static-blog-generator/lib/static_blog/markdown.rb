# frozen_string_literal: true

require "cgi"

module StaticBlog
  # A small, dependency-free Markdown-to-HTML converter.
  #
  # It works in two passes, the way most real Markdown engines do:
  #
  # 1. **Block pass** — a line-oriented state machine groups lines into
  #    blocks (headings, paragraphs, lists, quotes, fenced code, rules).
  # 2. **Inline pass** — each block's text is scanned for spans
  #    (code, emphasis, links, images) and HTML-escaped.
  #
  # Supported syntax is a practical subset of CommonMark; see README.md.
  class Markdown
    # Result of a conversion: the HTML plus the table of contents that was
    # collected while rendering headings.
    Heading = Struct.new(:level, :text, :id)

    attr_reader :headings

    def self.render(source)
      new(source).to_html
    end

    def initialize(source)
      @lines = source.to_s.gsub("\r\n", "\n").split("\n", -1)
      @headings = []
      @used_ids = Hash.new(0)
    end

    def to_html
      @to_html ||= parse_blocks(@lines).join("\n") + "\n"
    end

    # A one-paragraph plain-text summary, handy for index pages and feeds.
    def excerpt(limit = 160)
      para = @lines.chunk_while { |a, b| !a.strip.empty? && !b.strip.empty? }
                   .map { |chunk| chunk.join(" ").strip }
                   .find { |t| !t.empty? && !t.start_with?("#", "```", ">", "-", "*", "|") }
      return "" unless para

      text = Inline.plain_text(para)
      text.length > limit ? "#{text[0, limit].rstrip.sub(/\W+\z/, '')}…" : text
    end

    private

    HEADING   = /\A(\#{1,6})\s+(.*?)\s*#*\s*\z/
    FENCE     = /\A(```|~~~)\s*([\w+-]*)\s*\z/
    RULE      = /\A\s{0,3}([-*_])(\s*\1){2,}\s*\z/
    QUOTE     = /\A\s{0,3}>\s?(.*)\z/
    UL_ITEM   = /\A\s{0,3}[-*+]\s+(.*)\z/
    OL_ITEM   = /\A\s{0,3}(\d{1,9})[.)]\s+(.*)\z/

    # Walks the lines and returns an array of HTML block strings.
    def parse_blocks(lines)
      out = []
      i = 0
      while i < lines.length
        line = lines[i]

        if line.strip.empty?
          i += 1
        elsif (m = FENCE.match(line))
          i = fenced_code(lines, i, m, out)
        elsif (m = HEADING.match(line))
          out << heading(m[1].length, m[2])
          i += 1
        elsif RULE.match?(line)
          out << "<hr>"
          i += 1
        elsif QUOTE.match?(line)
          i = blockquote(lines, i, out)
        elsif UL_ITEM.match?(line)
          i = list(lines, i, UL_ITEM, "ul", out)
        elsif OL_ITEM.match?(line)
          i = list(lines, i, OL_ITEM, "ol", out)
        else
          i = paragraph(lines, i, out)
        end
      end
      out
    end

    def fenced_code(lines, i, match, out)
      fence, lang = match[1], match[2]
      body = []
      i += 1
      while i < lines.length && !lines[i].strip.start_with?(fence)
        body << lines[i]
        i += 1
      end
      klass = lang.empty? ? "" : %( class="language-#{CGI.escapeHTML(lang)}")
      out << "<pre><code#{klass}>#{CGI.escapeHTML(body.join("\n"))}</code></pre>"
      i + 1 # skip closing fence (or run off the end if unterminated)
    end

    def heading(level, raw)
      id = unique_id(Inline.plain_text(raw))
      @headings << Heading.new(level, Inline.plain_text(raw), id)
      %(<h#{level} id="#{id}">#{Inline.render(raw)}</h#{level}>)
    end

    # GitHub-style slug: lowercase, strip punctuation, spaces -> dashes,
    # and de-duplicate with -1, -2 suffixes.
    def unique_id(text)
      base = text.downcase.gsub(/[^\p{Alnum}\s-]/, "").strip.gsub(/\s+/, "-")
      base = "section" if base.empty?
      n = @used_ids[base]
      @used_ids[base] += 1
      n.zero? ? base : "#{base}-#{n}"
    end

    def blockquote(lines, i, out)
      inner = []
      while i < lines.length && (m = QUOTE.match(lines[i]))
        inner << m[1]
        i += 1
      end
      # Quotes contain blocks, so recurse; heading ids stay unique site-wide per doc.
      out << "<blockquote>\n#{parse_blocks(inner).join("\n")}\n</blockquote>"
      i
    end

    # Flat (non-nested) lists. Indented continuation lines join the item.
    def list(lines, i, pattern, tag, out)
      items = []
      start = nil
      while i < lines.length
        if (m = pattern.match(lines[i]))
          start ||= m[1].to_i if tag == "ol"
          items << m[-1].dup
        elsif !lines[i].strip.empty? && lines[i].start_with?("  ") && items.any?
          items.last << " " << lines[i].strip
        else
          break
        end
        i += 1
      end
      attr = tag == "ol" && start && start != 1 ? %( start="#{start}") : ""
      body = items.map { |t| "  <li>#{Inline.render(t)}</li>" }.join("\n")
      out << "<#{tag}#{attr}>\n#{body}\n</#{tag}>"
      i
    end

    def paragraph(lines, i, out)
      buf = []
      while i < lines.length
        line = lines[i]
        break if line.strip.empty?
        break if buf.any? && block_start?(line)

        buf << line.lstrip # keep trailing spaces: two of them mean <br>
        i += 1
      end
      out << "<p>#{Inline.render(buf.join("\n").rstrip)}</p>"
      i
    end

    def block_start?(line)
      [FENCE, HEADING, RULE, QUOTE, UL_ITEM].any? { |re| re.match?(line) }
    end

    # Inline span rendering. Kept as a separate module so templates can call
    # it directly (e.g. for titles that contain `code` or *emphasis*).
    module Inline
      # A URL may contain one level of balanced parentheses: /wiki/Foo_(bar)
      URL = /((?:[^()\s]|\([^()\s]*\))+)/
      SAFE_URL = %r{\A(?:https?://|mailto:|/|\./|\.\./|#|[\w.-]+(?:[/?#]|\z))}i

      module_function

      def render(text)
        stash = []
        hold = ->(html) { stash << html; "\u0000#{stash.length - 1}\u0000" }

        # 1. Protect code spans and backslash escapes from further processing.
        s = text.gsub(/(`+)(.+?)\1/m) { hold.call("<code>#{CGI.escapeHTML(Regexp.last_match(2).strip)}</code>") }
        s = s.gsub(/\\([\\`*_\[\]()#+\-.!>])/) { hold.call(CGI.escapeHTML(Regexp.last_match(1))) }

        # 2. Escape everything else; raw HTML is not passed through.
        s = CGI.escapeHTML(s)

        # 3. Images before links, since ![alt](src) contains [alt](src).
        s = s.gsub(/!\[([^\]]*)\]\(#{URL}(?:\s+&quot;(.*?)&quot;)?\)/o) do
          alt, src, title = Regexp.last_match.captures
          next Regexp.last_match(0) unless safe_url?(src)

          t = title ? %( title="#{title}") : ""
          hold.call(%(<img src="#{src}" alt="#{alt}"#{t}>))
        end
        s = s.gsub(/\[([^\]]+)\]\(#{URL}\)/o) do
          label, href = Regexp.last_match.captures
          safe_url?(href) ? %(<a href="#{href}">#{label}</a>) : label
        end

        # 4. Emphasis: strong first so ** is not eaten as two *.
        s = s.gsub(/(\*\*|__)(?=\S)(.+?)(?<=\S)\1/, '<strong>\2</strong>')
        s = s.gsub(/(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])/, '<em>\1</em>')
        s = s.gsub(/(?<!\w)_(?=\S)(.+?)(?<=\S)_(?!\w)/, '<em>\1</em>')

        # 5. Hard line breaks: two trailing spaces; otherwise newline -> space.
        s = s.gsub(/ {2,}\n/, "<br>\n")

        # 6. Restore protected spans (repeat for nesting, e.g. code in links).
        s = s.gsub(/\u0000(\d+)\u0000/) { stash[Regexp.last_match(1).to_i] } while s.include?("\u0000")
        s
      end

      # Strip markup to get readable text (for ids, excerpts, <title>).
      def plain_text(text)
        text.gsub(/!\[([^\]]*)\]\([^)]*\)/, '\1')
            .gsub(/\[([^\]]+)\]\([^)]*\)/, '\1')
            .gsub(/[`*_]/, "")
            .gsub(/\\(.)/, '\1')
            .gsub(/\s+/, " ")
            .strip
      end

      # Block javascript:, data:, vbscript: and other surprising schemes.
      def safe_url?(url)
        SAFE_URL.match?(CGI.unescapeHTML(url))
      end
    end
  end
end
