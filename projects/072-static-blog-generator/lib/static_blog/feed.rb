# frozen_string_literal: true

require "cgi"
require "time"

module StaticBlog
  # Builds an Atom 1.0 feed (RFC 4287) of the most recent posts.
  class Feed
    LIMIT = 20

    def initialize(site)
      @site = site
    end

    def to_xml
      posts = @site.posts.first(LIMIT)
      updated = posts.first&.date || Date.new(1970, 1, 1)
      entries = posts.map { |p| entry(p) }.join

      <<~XML
        <?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <title>#{x(@site.title)}</title>
          <link href="#{x(@site.absolute_url('/'))}"/>
          <link rel="self" href="#{x(@site.absolute_url('/feed.xml'))}"/>
          <id>#{x(@site.absolute_url('/'))}</id>
          <updated>#{stamp(updated)}</updated>
          <author><name>#{x(@site.author)}</name></author>
        #{entries}</feed>
      XML
    end

    private

    def entry(post)
      url = @site.absolute_url(post.url)
      <<-XML
  <entry>
    <title>#{x(post.title)}</title>
    <link href="#{x(url)}"/>
    <id>#{x(url)}</id>
    <updated>#{stamp(post.date)}</updated>
    <summary>#{x(post.summary)}</summary>
    <content type="html">#{x(post.html)}</content>
  </entry>
      XML
    end

    def x(text) = CGI.escapeHTML(text.to_s)

    # Atom wants full RFC 3339 timestamps; posts only have dates.
    def stamp(date) = Time.utc(date.year, date.month, date.day).iso8601
  end
end
