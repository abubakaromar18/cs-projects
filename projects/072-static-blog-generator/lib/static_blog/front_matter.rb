# frozen_string_literal: true

require "yaml"
require "date"

module StaticBlog
  # Splits a document into YAML front matter and a body.
  #
  #   ---
  #   title: Hello
  #   date: 2026-11-25
  #   ---
  #   Body text...
  #
  # Front matter is optional; a document without it yields an empty hash.
  module FrontMatter
    class ParseError < StandardError; end

    DELIMITER = /\A---\s*\n(.*?)\n---\s*(?:\n|\z)/m

    # Returns [metadata_hash, body_string]. Keys are symbolised.
    def self.parse(text)
      match = DELIMITER.match(text)
      return [{}, text] unless match

      data = YAML.safe_load(match[1], permitted_classes: [Date, Time], aliases: false) || {}
      raise ParseError, "front matter must be a mapping" unless data.is_a?(Hash)

      [data.transform_keys(&:to_sym), match.post_match]
    rescue Psych::SyntaxError => e
      raise ParseError, "invalid YAML front matter: #{e.message}"
    end
  end
end
