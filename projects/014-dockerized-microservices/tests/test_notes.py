import tempfile
import unittest

from helpers import RunningServer, load_service, request

notes = load_service("notes")
import notes_store  # noqa: E402  (importable once load_service has set sys.path)


class ValidationTest(unittest.TestCase):
    def test_valid_note_is_trimmed(self):
        self.assertEqual(notes_store.validate({"title": "  hi  ", "body": "x"}), ("hi", "x"))

    def test_body_is_optional(self):
        self.assertEqual(notes_store.validate({"title": "t"}), ("t", ""))

    def test_rejects_bad_input(self):
        bad = [None, [], {}, {"title": ""}, {"title": "   "}, {"title": 3},
               {"title": "t", "body": 1}, {"title": "x" * 201}, {"title": "t", "body": "x" * 10_001}]
        for data in bad:
            with self.assertRaises(notes_store.ValidationError, msg=data):
                notes_store.validate(data)


class NoteStoreTest(unittest.TestCase):
    def test_crud_and_persistence(self):
        with tempfile.TemporaryDirectory() as data:
            store = notes_store.NoteStore(data)
            a = store.create("a", "first")
            b = store.create("b", "second")
            self.assertEqual([n.id for n in store.list()], [1, 2])
            self.assertTrue(store.delete(a.id))
            self.assertFalse(store.delete(a.id))

            reloaded = notes_store.NoteStore(data)
            self.assertEqual([n.title for n in reloaded.list()], ["b"])
            self.assertEqual(reloaded.get(b.id).body, "second")

    def test_ids_are_never_reused(self):
        with tempfile.TemporaryDirectory() as data:
            store = notes_store.NoteStore(data)
            store.create("a", "")
            last = store.create("b", "")
            store.delete(last.id)
            self.assertEqual(notes_store.NoteStore(data).create("c", "").id, 3)


class NotesApiTest(unittest.TestCase):
    """The API on its own, with stats unreachable (it must keep working)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        # Port 9 (discard) on localhost: nothing listens, so every event send fails fast.
        server = notes.make_server("127.0.0.1", 0, self.tmp.name, "http://127.0.0.1:9")
        self.srv = RunningServer(server)

    def tearDown(self):
        self.srv.stop()
        self.tmp.cleanup()

    def test_create_get_list_delete(self):
        status, note, _ = request("POST", self.srv.url + "/notes", {"title": "Docker", "body": "volumes"})
        self.assertEqual(status, 201)
        self.assertEqual(note["id"], 1)

        status, got, _ = request("GET", f"{self.srv.url}/notes/{note['id']}")
        self.assertEqual((status, got["title"]), (200, "Docker"))

        status, listed, _ = request("GET", self.srv.url + "/notes")
        self.assertEqual((status, len(listed)), (200, 1))

        self.assertEqual(request("DELETE", f"{self.srv.url}/notes/1")[0], 200)
        self.assertEqual(request("GET", f"{self.srv.url}/notes/1")[0], 404)
        self.assertEqual(request("DELETE", f"{self.srv.url}/notes/1")[0], 404)

    def test_bad_requests(self):
        self.assertEqual(request("POST", self.srv.url + "/notes", raw=b"{oops")[0], 400)
        status, body, _ = request("POST", self.srv.url + "/notes", {"body": "no title"})
        self.assertEqual((status, body["error"]), (400, "title is required"))
        self.assertEqual(request("GET", self.srv.url + "/notes/abc")[0], 404)
        self.assertEqual(request("POST", self.srv.url + "/elsewhere", {})[0], 404)


if __name__ == "__main__":
    unittest.main()
