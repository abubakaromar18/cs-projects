import json

from port_scanner.cli import main


def test_text_output_lists_open_port(server, capsys):
    code = main(["127.0.0.1", "-p", str(server.port)])
    out = capsys.readouterr().out
    assert code == 0
    assert f"{server.port}/tcp  open" in out
    assert "1 ports scanned" in out


def test_json_output(server, closed_port, capsys):
    code = main(["127.0.0.1", "-p", f"{server.port},{closed_port}", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["counts"]["open"] == 1 and data["counts"]["closed"] == 1
    assert {r["port"] for r in data["results"]} == {server.port, closed_port}


def test_nothing_open_exits_1(closed_port, capsys):
    assert main(["-p", str(closed_port)]) == 1
    assert "No open ports found." in capsys.readouterr().out


def test_show_all_lists_closed(closed_port, capsys):
    main(["-p", str(closed_port), "--all"])
    assert "closed" in capsys.readouterr().out


def test_public_target_refused(capsys):
    assert main(["8.8.8.8", "-p", "53"]) == 2
    assert "only targets your own machines" in capsys.readouterr().err


def test_private_target_needs_flag(capsys):
    assert main(["192.168.1.1", "-p", "80"]) == 2
    assert "--allow-private" in capsys.readouterr().err


def test_bad_port_spec(capsys):
    assert main(["-p", "99999"]) == 2
    assert "out of range" in capsys.readouterr().err


def test_bad_concurrency(capsys):
    assert main(["-p", "80", "-c", "0"]) == 2


def test_verbose_streams_to_stderr(server, capsys):
    main(["-p", str(server.port), "-v"])
    assert f"[+] {server.port}/tcp open" in capsys.readouterr().err
