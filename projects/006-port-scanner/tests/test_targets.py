import ipaddress

import pytest

from port_scanner.targets import TargetNotAllowed, check_allowed, classify, make_target

ip = ipaddress.ip_address


@pytest.mark.parametrize("addr,kind", [
    ("127.0.0.1", "loopback"), ("127.8.9.10", "loopback"), ("::1", "loopback"),
    ("10.0.0.5", "private"), ("192.168.1.1", "private"), ("172.16.0.1", "private"),
    ("169.254.1.1", "private"), ("fd00::1", "private"),
    ("8.8.8.8", "public"), ("1.1.1.1", "public"), ("2606:4700::1111", "public"),
    ("0.0.0.0", "public"), ("224.0.0.1", "public"),
])
def test_classify(addr, kind):
    assert classify(ip(addr)) == kind


def test_loopback_always_allowed():
    check_allowed(ip("127.0.0.1"))


def test_private_requires_flag():
    with pytest.raises(TargetNotAllowed, match="--allow-private"):
        check_allowed(ip("192.168.0.10"))
    check_allowed(ip("192.168.0.10"), allow_private=True)


def test_public_never_allowed():
    with pytest.raises(TargetNotAllowed):
        check_allowed(ip("8.8.8.8"), allow_private=True)


def test_hostname_resolves_then_checked():
    t = make_target("localhost")
    assert t.address.is_loopback


def test_unresolvable_host():
    with pytest.raises(TargetNotAllowed, match="cannot resolve"):
        make_target("no-such-host.invalid")
