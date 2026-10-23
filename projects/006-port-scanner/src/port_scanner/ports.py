"""Port specification parsing and well-known service names.

A port spec is a comma-separated list of single ports and inclusive ranges,
e.g. ``"22,80,8000-8010"``. The keyword ``top`` expands to a curated list of
commonly used ports, which is handy for a quick look at your own machine.
"""

from __future__ import annotations

MIN_PORT = 1
MAX_PORT = 65535

# A small, readable subset of IANA assignments. Only used for display.
SERVICES: dict[int, str] = {
    20: "ftp-data", 21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp",
    53: "dns", 67: "dhcp", 80: "http", 110: "pop3", 111: "rpcbind",
    123: "ntp", 135: "msrpc", 139: "netbios", 143: "imap", 161: "snmp",
    389: "ldap", 443: "https", 445: "smb", 465: "smtps", 587: "submission",
    631: "ipp", 993: "imaps", 995: "pop3s", 1433: "mssql", 1521: "oracle",
    1883: "mqtt", 2049: "nfs", 2375: "docker", 3000: "dev-http",
    3306: "mysql", 3389: "rdp", 5000: "dev-http", 5432: "postgresql",
    5672: "amqp", 5900: "vnc", 6379: "redis", 8000: "http-alt",
    8080: "http-proxy", 8443: "https-alt", 8888: "jupyter", 9000: "dev-http",
    9200: "elasticsearch", 11211: "memcached", 27017: "mongodb",
}

TOP_PORTS: tuple[int, ...] = tuple(sorted(SERVICES))


class PortSpecError(ValueError):
    """Raised when a port specification cannot be parsed."""


def _parse_port(token: str) -> int:
    try:
        port = int(token)
    except ValueError:
        raise PortSpecError(f"not a port number: {token!r}") from None
    if not MIN_PORT <= port <= MAX_PORT:
        raise PortSpecError(f"port out of range 1-65535: {port}")
    return port


def parse_ports(spec: str) -> list[int]:
    """Expand a port spec into a sorted list of unique ports.

    >>> parse_ports("80,22,20-23")
    [20, 21, 22, 23, 80]
    """
    ports: set[int] = set()
    for raw in spec.split(","):
        token = raw.strip().lower()
        if not token:
            continue
        if token == "top":
            ports.update(TOP_PORTS)
        elif token == "all":
            ports.update(range(MIN_PORT, MAX_PORT + 1))
        elif "-" in token:
            lo_s, _, hi_s = token.partition("-")
            lo, hi = _parse_port(lo_s), _parse_port(hi_s)
            if lo > hi:
                raise PortSpecError(f"range start exceeds end: {token!r}")
            ports.update(range(lo, hi + 1))
        else:
            ports.add(_parse_port(token))
    if not ports:
        raise PortSpecError("empty port specification")
    return sorted(ports)


def service_name(port: int) -> str:
    """Best-effort service label for display (``"?"`` if unknown)."""
    return SERVICES.get(port, "?")
