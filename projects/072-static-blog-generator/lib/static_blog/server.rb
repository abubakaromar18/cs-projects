# frozen_string_literal: true

require "socket"
require "uri"

module StaticBlog
  # A minimal HTTP/1.1 file server for previewing the built site.
  # It binds to 127.0.0.1 only, handles GET/HEAD, and refuses any path that
  # resolves outside the site directory (no ../ traversal).
  class Server
    MIME = {
      ".html" => "text/html; charset=utf-8", ".css" => "text/css; charset=utf-8",
      ".js" => "text/javascript", ".xml" => "application/atom+xml; charset=utf-8",
      ".svg" => "image/svg+xml", ".png" => "image/png", ".jpg" => "image/jpeg",
      ".jpeg" => "image/jpeg", ".gif" => "image/gif", ".ico" => "image/x-icon",
      ".txt" => "text/plain; charset=utf-8"
    }.freeze

    def initialize(dir, port: 4000, out: $stdout)
      @dir = File.expand_path(dir)
      @port = port
      @out = out
    end

    def start
      server = TCPServer.new("127.0.0.1", @port)
      @out.puts "Serving #{@dir} at http://127.0.0.1:#{@port}/ (Ctrl-C to stop)"
      loop { handle(server.accept) }
    rescue Interrupt
      @out.puts "\nStopped."
    ensure
      server&.close
    end

    # Maps a request target to [status, headers, body]. Public for tests.
    def respond(method, target)
      return [405, { "Allow" => "GET, HEAD" }, "Method Not Allowed\n"] unless %w[GET HEAD].include?(method)

      path = resolve(target)
      return [404, {}, "Not Found\n"] unless path

      body = File.binread(path)
      headers = { "Content-Type" => MIME.fetch(File.extname(path).downcase, "application/octet-stream") }
      [200, headers, method == "HEAD" ? "" : body]
    end

    # Returns an absolute file path inside @dir, or nil.
    def resolve(target)
      raw = URI.decode_www_form_component(target.to_s.split("?", 2).first.to_s)
      return nil if raw.include?("\0")

      candidate = File.expand_path(File.join(@dir, raw))
      return nil unless candidate == @dir || candidate.start_with?(@dir + File::SEPARATOR)

      candidate = File.join(candidate, "index.html") if File.directory?(candidate)
      File.file?(candidate) ? candidate : nil
    rescue ArgumentError
      nil
    end

    private

    REASONS = { 200 => "OK", 404 => "Not Found", 405 => "Method Not Allowed", 400 => "Bad Request" }.freeze

    def handle(client)
      request_line = client.gets.to_s
      # Drain headers; we don't need them.
      while (line = client.gets) && line != "\r\n"; end
      method, target, = request_line.split(" ")
      status, headers, body = method && target ? respond(method, target) : [400, {}, "Bad Request\n"]
      headers = { "Content-Type" => "text/plain; charset=utf-8" }.merge(headers)
      headers["Content-Length"] = (method == "HEAD" && status == 200 ? File.size(resolve(target)) : body.bytesize).to_s
      headers["Connection"] = "close"
      client.write("HTTP/1.1 #{status} #{REASONS[status]}\r\n")
      headers.each { |k, v| client.write("#{k}: #{v}\r\n") }
      client.write("\r\n", body)
      @out.puts "#{status} #{method} #{target}"
    rescue StandardError => e
      @out.puts "error: #{e.message}"
    ensure
      client.close
    end
  end
end
