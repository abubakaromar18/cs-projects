"""All three services wired together, the same way compose.yaml wires them.

Each service runs on its own port on 127.0.0.1 and is told where the
others are through the same settings the containers get from Compose
(Compose uses service names like http://stats:8000 instead).
"""

import tempfile
import time
import unittest

from helpers import RunningServer, load_service, request

gateway = load_service("gateway")
notes = load_service("notes")
stats = load_service("stats")


def wait_for(predicate, timeout=3.0):
    """Events are sent in the background, so poll briefly for them to land."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


class StackTest(unittest.TestCase):
    def setUp(self):
        self.notes_data = tempfile.TemporaryDirectory()
        self.stats_data = tempfile.TemporaryDirectory()
        self.start_stack()

    def start_stack(self):
        self.stats = RunningServer(stats.make_server("127.0.0.1", 0, self.stats_data.name))
        self.notes = RunningServer(notes.make_server("127.0.0.1", 0, self.notes_data.name, self.stats.url))
        self.gw = RunningServer(gateway.make_server("127.0.0.1", 0, self.notes.url, self.stats.url))

    def stop_stack(self):
        for srv in (self.gw, self.notes, self.stats):
            srv.stop()

    def tearDown(self):
        self.stop_stack()
        self.notes_data.cleanup()
        self.stats_data.cleanup()

    def total_events(self):
        return request("GET", self.gw.url + "/api/stats")[1]["total"]

    def test_health_all_ok(self):
        status, body, _ = request("GET", self.gw.url + "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["services"], {"gateway": "ok", "notes": "ok", "stats": "ok"})

    def test_notes_flow_updates_stats(self):
        for title in ("one", "two"):
            self.assertEqual(request("POST", self.gw.url + "/api/notes", {"title": title})[0], 201)
        self.assertEqual(request("DELETE", self.gw.url + "/api/notes/1")[0], 200)

        self.assertTrue(wait_for(lambda: self.total_events() == 3))
        counts = request("GET", self.gw.url + "/api/stats")[1]["counts"]
        self.assertEqual(counts, {"note_created": 2, "note_deleted": 1})

        status, listed, _ = request("GET", self.gw.url + "/api/notes")
        self.assertEqual([n["title"] for n in listed], ["two"])

    def test_upstream_errors_pass_through(self):
        status, body, _ = request("GET", self.gw.url + "/api/notes/999")
        self.assertEqual((status, body["error"]), (404, "note not found"))
        status, _, _ = request("POST", self.gw.url + "/api/notes", {"title": ""})
        self.assertEqual(status, 400)

    def test_request_id_is_propagated(self):
        _, _, headers = request("GET", self.gw.url + "/api/notes", headers={"X-Request-ID": "trace-123"})
        self.assertEqual(headers["X-Request-ID"], "trace-123")

    def test_data_survives_restart(self):
        """Like `docker compose down && docker compose up`: same volumes, new processes."""
        request("POST", self.gw.url + "/api/notes", {"title": "keep me"})
        self.assertTrue(wait_for(lambda: self.total_events() == 1))

        self.stop_stack()
        self.start_stack()

        listed = request("GET", self.gw.url + "/api/notes")[1]
        self.assertEqual([n["title"] for n in listed], ["keep me"])
        self.assertEqual(self.total_events(), 1)

    def test_notes_keeps_working_when_stats_is_down(self):
        self.stats.stop()
        status, _, _ = request("POST", self.gw.url + "/api/notes", {"title": "resilient"})
        self.assertEqual(status, 201)
        self.assertEqual(request("GET", self.gw.url + "/api/stats")[0], 502)
        self.assertEqual(request("GET", self.gw.url + "/health")[0], 503)
        # Give tearDown a live server to stop.
        self.stats = RunningServer(stats.make_server("127.0.0.1", 0, self.stats_data.name))


if __name__ == "__main__":
    unittest.main()
