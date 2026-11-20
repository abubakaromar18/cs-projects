"""Wire protocol shared by the client and server.

TCP control/data channel
------------------------
Every request is a fixed 9-byte header::

    +--------+---------------------------+
    | cmd 1B | argument 8B (unsigned BE) |
    +--------+---------------------------+

Commands:

``P`` PING      argument = client nonce. Server echoes the same 9 bytes back.
``D`` DOWNLOAD  argument = byte count. Server streams that many bytes.
``U`` UPLOAD    argument = byte count. Client streams that many bytes; the
                server answers with an 8-byte count of bytes it received,
                which doubles as an application-level acknowledgement.
``Q`` QUIT      server closes the connection.

UDP probe channel
-----------------
Each datagram is ``seq (4B) + client send time in ns (8B) + padding``. The
server echoes datagrams unchanged, so the client can compute round-trip time,
loss and reordering without trusting the server's clock.

Big-endian ("network byte order") is used throughout, as is conventional for
network protocols.
"""

from __future__ import annotations

import socket
import struct

HEADER = struct.Struct("!cQ")  # 1-byte command + 8-byte unsigned argument
COUNT = struct.Struct("!Q")
UDP_PROBE = struct.Struct("!IQ")  # sequence number + send timestamp (ns)

CMD_PING = b"P"
CMD_DOWNLOAD = b"D"
CMD_UPLOAD = b"U"
CMD_QUIT = b"Q"

DEFAULT_PORT = 5201
CHUNK = 64 * 1024  # 64 KiB application buffer for bulk transfers

# Hard cap on a single transfer so a malformed request can't make the server
# stream forever (defence in depth for a test tool).
MAX_TRANSFER = 4 * 1024 * 1024 * 1024


def recv_exact(sock: socket.socket, n: int) -> bytes:
    """Read exactly ``n`` bytes or raise ``ConnectionError``.

    TCP is a byte stream, not a message stream: a single ``recv`` may return
    fewer bytes than were sent, so framed protocols must loop.
    """
    buf = bytearray(n)
    view = memoryview(buf)
    got = 0
    while got < n:
        k = sock.recv_into(view[got:], n - got)
        if k == 0:
            raise ConnectionError(f"peer closed after {got}/{n} bytes")
        got += k
    return bytes(buf)


def drain(sock: socket.socket, n: int) -> int:
    """Receive and discard ``n`` bytes; return the number actually read."""
    buf = bytearray(CHUNK)
    view = memoryview(buf)
    remaining = n
    while remaining:
        k = sock.recv_into(view, min(CHUNK, remaining))
        if k == 0:
            break
        remaining -= k
    return n - remaining


def send_bulk(sock: socket.socket, n: int, payload: bytes | None = None) -> None:
    """Send ``n`` bytes of filler data using a reusable chunk."""
    chunk = payload or (b"\xa5" * CHUNK)
    view = memoryview(chunk)
    remaining = n
    while remaining:
        k = min(len(chunk), remaining)
        sock.sendall(view[:k])
        remaining -= k
