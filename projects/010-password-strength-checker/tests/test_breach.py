import hashlib

import pytest

from password_checker.breach import (
    HIBP_RANGE_URL, in_local_list, load_hash_set, pwned_count, sha1_hex,
)


def test_sha1_hex_uppercase():
    assert sha1_hex("password") == hashlib.sha1(b"password").hexdigest().upper()


def test_bundled_list():
    assert in_local_list("123456")
    assert in_local_list("letmein")
    assert not in_local_list("xK9#mQ2$vLp7!zR4")


def test_extra_list_plaintext_and_hashes(tmp_path):
    f = tmp_path / "list.txt"
    f.write_text("# comment\nmy-company-2024\n" + sha1_hex("hunter2-xyz").lower() + "\n")
    assert in_local_list("my-company-2024", f)
    assert in_local_list("hunter2-xyz", f)
    assert not in_local_list("something-else", f)


def test_load_hash_set_skips_blanks():
    assert load_hash_set(["", "# x", "abc"]) == {sha1_hex("abc")}


def test_pwned_count_uses_k_anonymity():
    digest = sha1_hex("password")
    seen_urls = []

    def fake_fetch(url):
        seen_urls.append(url)
        return f"0000000000000000000000000000000000A:0\r\n{digest[5:]}:42\r\n"

    assert pwned_count("password", fetch=fake_fetch) == 42
    # Only the 5-char prefix is sent; the full hash and password are not.
    assert seen_urls == [HIBP_RANGE_URL.format(prefix=digest[:5])]
    assert digest[5:] not in seen_urls[0]


def test_pwned_count_not_found():
    assert pwned_count("whatever", fetch=lambda url: "ABCDEF:3\n") == 0


def test_pwned_count_propagates_network_errors():
    def boom(url):
        raise OSError("offline")

    with pytest.raises(OSError):
        pwned_count("x", fetch=boom)
