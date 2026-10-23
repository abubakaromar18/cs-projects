import pytest

from port_scanner.ports import TOP_PORTS, PortSpecError, parse_ports, service_name


def test_singles_and_ranges_are_merged_sorted_unique():
    assert parse_ports("80,22,20-23, 22") == [20, 21, 22, 23, 80]


def test_top_and_all_keywords():
    assert parse_ports("top") == list(TOP_PORTS)
    assert len(parse_ports("all")) == 65535


@pytest.mark.parametrize("spec", ["", "0", "65536", "abc", "10-5", "1-x", ",,"])
def test_invalid_specs(spec):
    with pytest.raises(PortSpecError):
        parse_ports(spec)


def test_service_names():
    assert service_name(22) == "ssh"
    assert service_name(4) == "?"
