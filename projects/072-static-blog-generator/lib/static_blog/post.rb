# frozen_string_literal: true

require "date"

module StaticBlog
  # A single Markdown source file (a dated post or an undated page),
  # parsed into metadata and rendered HTML.
  class Post
    # Posts are named YYYY-MM-DD-slug.md; pages are just slug.md.
    FILENAME = /\A(?:(\d{4}-\d{2}-\d{2})-)?(.+)\.(?:md|markdown)\z/

    attr_reader :path, :meta, :body, :slug, :date, :kind

    def self.load(path, kind: :post)
      new(path, File.read(path, encoding: "UTF-8"), kind: kind)
    end

    def initialize(path, source, kind: :post)
      @path = path
      @kind = kind
      @meta, @body = FrontMatter.parse(source)
      name = FILENAME.match(File.basename(path)) or raise ArgumentError, "not a Markdown file: #{path}"

      @slug = (@meta[:slug] || slugify(name[2])).to_s
      @date = coerce_date(@meta[:date] || name[1])
      raise ArgumentError, "post #{path} needs a date (filename or front matter)" if post? && @date.nil?

      @markdown = Markdown.new(@body)
    end

    def post? = kind == :post
    def draft? = meta[:draft] == true

    def title
      (meta[:title] || markdown_title || slug.tr("-", " ").capitalize).to_s
    end

    def tags
      Array(meta[:tags]).map { |t| t.to_s.strip.downcase }.reject(&:empty?).uniq.sort
    end

    def summary = (meta[:summary] || @markdown.excerpt).to_s
    def html = @markdown.to_html
    def headings = (@markdown.to_html && @markdown.headings)

    # Rough reading time at 200 words per minute, minimum one minute.
    def reading_minutes
      [(body.split(/\s+/).count { |w| w.match?(/\w/) } / 200.0).ceil, 1].max
    end

    # Output path relative to the site root, e.g. "2026/11/hello-world/index.html".
    # "Pretty" URLs: every page is a directory with an index.html inside.
    def output_path
      post? ? format("%04d/%02d/%s/index.html", date.year, date.month, slug) : "#{slug}/index.html"
    end

    def url = "/#{output_path.delete_suffix('index.html')}"

    private

    def markdown_title
      first = body.lines.find { |l| l.start_with?("# ") }
      first && Markdown::Inline.plain_text(first.sub(/\A#\s+/, ""))
    end

    def slugify(text)
      text.downcase.gsub(/[^a-z0-9]+/, "-").gsub(/\A-|-\z/, "")
    end

    def coerce_date(value)
      case value
      when nil then nil
      when Date then value.is_a?(DateTime) ? value.to_date : value
      when Time then value.to_date
      else Date.iso8601(value.to_s)
      end
    rescue Date::Error
      raise ArgumentError, "bad date #{value.inspect} in #{path}"
    end
  end
end
