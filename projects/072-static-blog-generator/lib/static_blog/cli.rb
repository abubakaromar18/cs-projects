# frozen_string_literal: true

require "optparse"
require "date"
require "fileutils"

module StaticBlog
  # Command-line entry point: `blog build | new | serve`.
  class CLI
    USAGE = <<~TEXT
      Usage: blog <command> [options]

      Commands:
        build              Render the site into _site/
        new "Post title"   Create content/posts/YYYY-MM-DD-post-title.md
        serve              Build, then serve _site/ on 127.0.0.1

      Options:
        -s, --source DIR   Site directory (default: current directory)
        -o, --output DIR   Output directory (default: SOURCE/_site)
        -d, --drafts       Include posts marked `draft: true`
        -p, --port N       Port for `serve` (default: 4000)
    TEXT

    def initialize(argv, out: $stdout, err: $stderr, today: Date.today)
      @argv = argv.dup
      @out = out
      @err = err
      @today = today
      @opts = { source: ".", output: nil, drafts: nil, port: 4000 }
    end

    # Returns a process exit status.
    def run
      parse_options!
      return usage if @opts[:help]

      case (cmd = @argv.shift)
      when "build" then build
      when "new"   then new_post(@argv.join(" "))
      when "serve" then build.zero? ? serve : 1
      when nil, "help" then usage
      else
        @err.puts "Unknown command: #{cmd}\n\n#{USAGE}"
        2
      end
    rescue OptionParser::ParseError, ArgumentError, FrontMatter::ParseError => e
      @err.puts "error: #{e.message}"
      1
    end

    private

    def parse_options!
      OptionParser.new do |o|
        o.on("-s", "--source DIR") { |v| @opts[:source] = v }
        o.on("-o", "--output DIR") { |v| @opts[:output] = v }
        o.on("-d", "--drafts") { @opts[:drafts] = true }
        o.on("-p", "--port N", Integer) { |v| @opts[:port] = v }
        o.on("-h", "--help") { @opts[:help] = true }
      end.parse!(@argv)
    end

    def usage
      @out.puts USAGE
      0
    end

    def site
      @site ||= Site.new(@opts[:source], output_dir: @opts[:output], drafts: @opts[:drafts])
    end

    def build
      started = Process.clock_gettime(Process::CLOCK_MONOTONIC)
      files = site.load.build
      ms = ((Process.clock_gettime(Process::CLOCK_MONOTONIC) - started) * 1000).round
      @out.puts "Built #{site.posts.size} posts, #{site.pages.size} pages, " \
                "#{site.tags.size} tags -> #{files.size} files in #{ms} ms"
      @out.puts "Output: #{site.output_dir}"
      0
    end

    def new_post(title)
      raise ArgumentError, "give the post a title: blog new \"My title\"" if title.strip.empty?

      slug = title.downcase.gsub(/[^a-z0-9]+/, "-").gsub(/\A-|-\z/, "")
      path = File.join(@opts[:source], "content", "posts", "#{@today.iso8601}-#{slug}.md")
      raise ArgumentError, "#{path} already exists" if File.exist?(path)

      FileUtils.mkdir_p(File.dirname(path))
      File.write(path, <<~MD)
        ---
        title: #{title.inspect}
        date: #{@today.iso8601}
        tags: []
        draft: true
        ---

        Write something wonderful.
      MD
      @out.puts "Created #{path}"
      0
    end

    def serve
      Server.new(site.output_dir, port: @opts[:port], out: @out).start
      0
    end
  end
end
