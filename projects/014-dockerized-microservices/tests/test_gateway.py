import tempfile
import unittest

from helpers import RunningServer, load_service, request

gateway = load_service("gateway")
UPSTREAMS = {"notes": "http://notes:8000", "stats": "http://stats:8000"}


class RoutingTest(unittest.TestCase):
    def test_resolve(self):
        self.assertEqual(gateway.resolve("/api/notes", UPSTREAMS), "http://notes:8000/notes")
        self.assertEqual(gateway.resolve("/api/notes/7", UPSTREAMS), "http://notes:8000/notes/7")
        self.assertEqual(gateway.resolve("/api/stats", UPSTREAMS), "http://stats:8000/stats")

    def test_unrouted_paths(self):
        for path in ("/api", "/api/notesX", "/api/stats/events", "/notes", "/api/stats/../events"):
            self.assertIsNone(gateway.resolve(path, UPSTREAMS), path)


class DegradedGatewayTest(unittest.TestCase):
    """Gateway with no backends running: it must stay up and say so."""

    def setUp(self):
        self.srv = RunningServer(gateway.make_server(
            "127.0.0.1", 0, "http://127.0.0.1:9", "http://127.0.0.1:9"))

    def tearDown(self):
        self.srv.stop()

    def test_index_still_answers(self):
        status, body, _ = request("GET", self.srv.url + "/")
        self.assertEqual((status, body["service"]), (200, "gateway"))

    def test_health_reports_degraded(self):
        status, body, _ = request("GET", self.srv.url + "/health")
        self.assertEqual(status, 503)
        self.assertEqual(body["status"], "degraded")
        self.assertEqual(body["services"]["gateway"], "ok")
        self.assertTrue(body["services"]["notes"].startswith("down"))

    def test_proxy_returns_502(self):
        status, body, headers = request("GET", self.srv.url + "/api/notes")
        self.assertEqual((status, body["error"]), (502, "upstream unavailable"))
        self.assertTrue(headers["X-Request-ID"])

    def test_unknown_route_404(self):
        self.assertEqual(request("GET", self.srv.url + "/admin")[0], 404)


if __name__ == "__main__":
    unittest.main()
