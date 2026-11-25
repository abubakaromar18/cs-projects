# frozen_string_literal: true

require "erb"
require "cgi"

module StaticBlog
  # Compiles and renders ERB templates from a directory.
  #
  # Each render gets a fresh Context object; its instance variables and
  # helper methods are what the template can see. A template is rendered and
  # then, unless told otherwise, wrapped in layout.html.erb, which receives the
  # inner HTML via `yield`/`content`.
  class Renderer
    def initialize(template_dir, site:)
      @dir = template_dir
      @site = site
      @cache = {} # compiled ERB objects, keyed by template name
    end

    def render(name, layout: "layout", **locals)
      ctx = Context.new(self, @site, locals)
      inner = template(name).result(ctx.binding_for)
      return inner unless layout

      ctx.content = inner
      template(layout).result(ctx.binding_for { inner })
    end

    # Partials render without a layout and share the caller's locals.
    def partial(name, **locals)
      render("_#{name}", layout: nil, **locals)
    end

    private

    def template(name)
      @cache[name] ||= begin
        path = File.join(@dir, "#{name}.html.erb")
        raise ArgumentError, "missing template: #{path}" unless File.exist?(path)

        # trim_mode "-" lets templates use <%- and -%> to swallow newlines.
        ERB.new(File.read(path, encoding: "UTF-8"), trim_mode: "-").tap { |e| e.filename = path }
      end
    end

    # The object templates are evaluated against.
    class Context
      attr_accessor :content
      attr_reader :site

      def initialize(renderer, site, locals)
        @renderer = renderer
        @site = site
        locals.each { |k, v| instance_variable_set("@#{k}", v) }
      end

      # Returning a binding from inside a method that accepts a block makes
      # `yield` inside the template call that block.
      def binding_for(&) = binding

      # --- helpers available in every template ---

      def h(text) = CGI.escapeHTML(text.to_s)

      def partial(name, **locals)
        @renderer.partial(name, **instance_locals.merge(locals))
      end

      # Prefix a root-relative path with the configured base path so the site
      # works when hosted in a subdirectory (e.g. GitHub Pages project sites).
      def url_for(path) = site.url_for(path)

      def format_date(date, fmt = "%B %-d, %Y") = date&.strftime(fmt)

      def tag_url(tag) = url_for("/tags/#{tag}/")

      private

      def instance_locals
        instance_variables.each_with_object({}) do |iv, acc|
          next if %i[@renderer @site @content].include?(iv)

          acc[iv.to_s.delete_prefix("@").to_sym] = instance_variable_get(iv)
        end
      end
    end
  end
end
