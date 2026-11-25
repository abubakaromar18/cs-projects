# frozen_string_literal: true

$LOAD_PATH.unshift File.expand_path("../lib", __dir__)
require "static_blog"
require "minitest/autorun"
require "tmpdir"
require "fileutils"
require "stringio"

module TestHelpers
  EXAMPLE_ROOT = File.expand_path("..", __dir__)

  # Creates a throwaway site with the real templates and the given files.
  def with_site(files = {})
    Dir.mktmpdir("static-blog") do |dir|
      FileUtils.cp_r(File.join(EXAMPLE_ROOT, "templates"), dir)
      files.each do |rel, body|
        path = File.join(dir, rel)
        FileUtils.mkdir_p(File.dirname(path))
        File.write(path, body)
      end
      yield dir
    end
  end
end
