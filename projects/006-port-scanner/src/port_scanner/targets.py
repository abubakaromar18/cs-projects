"""Target resolution and the safety policy.

This tool is for auditing machines you own. The policy is enforced *after*
DNS resolution so that a hostname cannot smuggle a public address past it:

* loopback addresses (127.0.0.0/8, ::1) are always allowed;
* private / link-local addresses (10/8, 172.16/12, 192.168/16, fc00::/7,
  169.254/16, fe80::/10) require ``allow_private=True`` — use this for your
  own LAN devices;
* every other address is refused. There is no override.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


class TargetNotAllowed(PermissionError):
    """Raised when a target falls outside the safety policy."""


@dataclass(frozen=True)
class Target:
    host: str          # what the user typed
    address: IPAddress  # what we will actually connect to

    @property
    def family(self) -> int:
        return socket.AF_INET6 if self.address.version == 6 else socket.AF_INET


def resolve(host: str) -> IPAddress:
    """Resolve *host* to a single IP address (IP literals pass straight through)."""
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise TargetNotAllowed(f"cannot resolve {host!r}: {exc.strerror}") from None
    # Prefer IPv4 for predictability, then fall back to whatever came first.
    infos.sort(key=lambda info: info[0] != socket.AF_INET)
    return ipaddress.ip_address(infos[0][4][0])


def classify(addr: IPAddress) -> str:
    """Return ``"loopback"``, ``"private"`` or ``"public"``."""
    if addr.is_loopback:
        return "loopback"
    if addr.is_private or addr.is_link_local:
        # is_private also covers some reserved/unspecified blocks; reject those.
        if addr.is_unspecified or addr.is_multicast or addr.is_reserved:
            return "public"
        return "private"
    return "public"


def check_allowed(addr: IPAddress, *, allow_private: bool = False) -> None:
    """Raise :class:`TargetNotAllowed` unless *addr* passes the policy."""
    kind = classify(addr)
    if kind == "loopback":
        return
    if kind == "private":
        if allow_private:
            return
        raise TargetNotAllowed(
            f"{addr} is a private-network address; pass --allow-private "
            "if it is a device you own"
        )
    raise TargetNotAllowed(
        f"{addr} is not a loopback or private address; this educational "
        "scanner only targets your own machines"
    )


def make_target(host: str, *, allow_private: bool = False) -> Target:
    """Resolve and validate *host* in one step."""
    addr = resolve(host)
    check_allowed(addr, allow_private=allow_private)
    return Target(host=host, address=addr)
