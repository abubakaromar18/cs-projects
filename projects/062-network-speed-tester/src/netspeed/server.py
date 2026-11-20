"""Measurement server: a TCP command handler plus a UDP echo responder.

Uses ``socketserver``'s threading mixins: one thread per TCP connection, which
is simple and plenty for a test tool that normally has a single client.
"""

from __future__ import annotations

import socket
import socketserver
import threading
from typing import Optional

from . import protocol as p


class _TCPHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        sock: socket.socket = self.request
        # Disable Nagle's algorithm so tiny PING replies are sent immediately
        # instead of being held back to coalesce with later writes.
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        try:
            while True:
                cmd, arg = p.HEADER.unpack(p.recv_exact(sock, p.HEADER.size))
                if cmd == p.CMD_PING:
                    sock.sendall(p.HEADER.pack(cmd, arg))
                elif cmd == p.CMD_DOWNLOAD:
                    p.send_bulk(sock, min(arg, p.MAX_TRANSFER))
                elif cmd == p.CMD_UPLOAD:
                    got = p.drain(sock, min(arg, p.MAX_TRANSFER))
                    sock.sendall(p.COUNT.pack(got))
                elif cmd == p.CMD_QUIT:
                    return
                else:  # unknown command: drop the connection
                    return
        except (ConnectionError, OSError):
            return  # client went away mid-test; nothing to clean up


class _UDPHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        data, sock = self.request
        sock.sendto(data, self.client_address)


class _TCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class _UDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    allow_reuse_address = True
    daemon_threads = True


class SpeedServer:
    """Runs the TCP and UDP listeners on the same port number.

    Pass ``port=0`` to let the OS choose a free port (handy in tests); the
    chosen port is available as :attr:`port` after construction.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = p.DEFAULT_PORT):
        self.tcp = _TCPServer((host, port), _TCPHandler)
        self.host, self.port = self.tcp.server_address[:2]
        self.udp = _UDPServer((host, self.port), _UDPHandler)
        self._threads: list[threading.Thread] = []

    def start(self) -> "SpeedServer":
        """Serve in background threads and return immediately."""
        for srv in (self.tcp, self.udp):
            # A short poll interval keeps stop() snappy (default is 0.5 s).
            t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
            t.start()
            self._threads.append(t)
        return self

    def serve_forever(self) -> None:
        """Block the calling thread until interrupted."""
        self.start()
        try:
            for t in self._threads:
                t.join()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        # shutdown() waits for serve_forever() to exit, so only call it when
        # the serving threads were actually started.
        for srv in (self.tcp, self.udp):
            if self._threads:
                srv.shutdown()
            srv.server_close()
        self._threads.clear()

    def __enter__(self) -> "SpeedServer":
        return self.start()

    def __exit__(self, *exc: Optional[BaseException]) -> None:
        self.stop()
