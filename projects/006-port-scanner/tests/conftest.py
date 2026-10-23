"""Shared fixtures: tiny TCP servers on 127.0.0.1 ephemeral ports."""

import socket
import threading

import pytest


class _Server:
    """Accepts connections in a thread; optionally sends a greeting banner."""

    def __init__(self, banner: bytes | None = None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(64)
        self.port = self.sock.getsockname()[1]
        self.banner = banner
        self._stop = False
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        self.sock.settimeout(0.1)
        while not self._stop:
            try:
                conn, _ = self.sock.accept()
            except (socket.timeout, OSError):
                continue
            with conn:
                if self.banner:
                    try:
                        conn.sendall(self.banner)
                    except OSError:
                        pass

    def close(self):
        self._stop = True
        self.thread.join(timeout=1)
        self.sock.close()


@pytest.fixture
def server():
    s = _Server()
    yield s
    s.close()


@pytest.fixture
def banner_server():
    s = _Server(banner=b"SSH-2.0-TestServer_1.0\r\nextra line\r\n")
    yield s
    s.close()


@pytest.fixture
def closed_port():
    """A port that was just free on loopback (nothing listening)."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port
