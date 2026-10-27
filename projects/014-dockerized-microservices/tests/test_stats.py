import tempfile
import unittest

from helpers import RunningServer, load_service, request

stats = load_service("stats")


class StatsStoreTest(unittest.TestCase):
    def test_counts_persist_across_restarts(self):
        with tempfile.TemporaryDirectory() as data:
            store = stats.StatsStore(data)
            store.record("note_created")
            store.record("note_created")
            store.record("note_deleted")
            # A new store on the same directory = a restarted container on the same volume.
            reloaded = stats.StatsStore(data)
            self.assertEqual(reloaded.snapshot(), {"note_created": 2, "note_deleted": 1})

    def test_corrupt_file_starts_from_zero(self):
        with tempfile.TemporaryDirectory() as data:
            (stats.StatsStore(data).path).write_text("{not json")
            self.assertEqual(stats.StatsStore(data).snapshot(), {})


class StatsApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.srv = RunningServer(stats.make_server("127.0.0.1", 0, self.tmp.name))

    def tearDown(self):
        self.srv.stop()
        self.tmp.cleanup()

    def test_health(self):
        status, body, _ = request("GET", self.srv.url + "/health")
        self.assertEqual((status, body["status"]), (200, "ok"))

    def test_record_and_read(self):
        for _ in range(3):
            status, _, _ = request("POST", self.srv.url + "/events", {"type": "note_created"})
            self.assertEqual(status, 201)
        status, body, _ = request("GET", self.srv.url + "/stats")
        self.assertEqual(status, 200)
        self.assertEqual(body["counts"], {"note_created": 3})
        self.assertEqual(body["total"], 3)

    def test_rejects_bad_events(self):
        for raw in (b"not json", b"{}", b'{"type": 5}', b'{"type": "DROP TABLE"}', b"[1]"):
            status, _, _ = request("POST", self.srv.url + "/events", raw=raw)
            self.assertEqual(status, 400, raw)

    def test_unknown_route(self):
        self.assertEqual(request("GET", self.srv.url + "/nope")[0], 404)
        self.assertEqual(request("POST", self.srv.url + "/nope", {})[0], 404)


if __name__ == "__main__":
    unittest.main()
