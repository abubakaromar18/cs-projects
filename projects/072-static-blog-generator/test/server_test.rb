# frozen_string_literal: true

require "test_helper"

class ServerTest < Minitest::Test
  def setup
    @dir = Dir.mktmpdir
    FileUtils.mkdir_p(File.join(@dir, "post"))
    File.write(File.join(@dir, "index.html"), "<h1>home</h1>")
    File.write(File.join(@dir, "post/index.html"), "post")
    File.write(File.join(@dir, "style.css"), "body{}")
    File.write(File.join(File.dirname(@dir), "secret-#{File.basename(@dir)}.txt"), "nope")
    @server = StaticBlog::Server.new(@dir)
  end

  def teardown
    FileUtils.rm_rf(@dir)
    FileUtils.rm_f(File.join(File.dirname(@dir), "secret-#{File.basename(@dir)}.txt"))
  end

  def test_serves_index_for_directories
    status, headers, body = @server.respond("GET", "/")
    assert_equal 200, status
    assert_equal "text/html; charset=utf-8", headers["Content-Type"]
    assert_equal "<h1>home</h1>", body
    assert_equal "post", @server.respond("GET", "/post/?q=1")[2]
  end

  def test_content_types
    assert_equal "text/css; charset=utf-8", @server.respond("GET", "/style.css")[1]["Content-Type"]
  end

  def test_missing_is_404
    assert_equal 404, @server.respond("GET", "/nope.html")[0]
  end

  def test_path_traversal_is_blocked
    name = "secret-#{File.basename(@dir)}.txt"
    assert_equal 404, @server.respond("GET", "/../#{name}")[0]
    assert_equal 404, @server.respond("GET", "/%2e%2e/#{name}")[0]
    assert_equal 404, @server.respond("GET", "/a%00b")[0]
  end

  def test_only_get_and_head
    assert_equal 405, @server.respond("POST", "/")[0]
    status, _, body = @server.respond("HEAD", "/")
    assert_equal [200, ""], [status, body]
  end

  def test_real_socket_round_trip
    port = TCPServer.open("127.0.0.1", 0) { |s| s.addr[1] }
    log = StringIO.new
    thread = Thread.new { StaticBlog::Server.new(@dir, port: port, out: log).start }
    response = nil
    20.times do
      response = TCPSocket.open("127.0.0.1", port) do |sock|
        sock.write("GET /style.css HTTP/1.1\r\nHost: x\r\n\r\n")
        sock.read
      end
      break
    rescue Errno::ECONNREFUSED
      sleep 0.05
    end
    assert_match(%r{\AHTTP/1.1 200 OK\r\n}, response)
    assert_includes response, "Content-Length: 6\r\n"
    assert response.end_with?("\r\n\r\nbody{}")
  ensure
    thread&.kill
  end
end
