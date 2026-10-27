"""Check that compose.yaml describes the architecture the README promises.

Uses `docker compose config` to parse and normalize the file, so it needs
the Docker CLI (but not a running daemon). Skipped if docker is missing.
"""

import json
import shutil
import subprocess
import unittest

from helpers import ROOT


def compose_config():
    out = subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)


@unittest.skipUnless(shutil.which("docker"), "docker CLI not installed")
class ComposeFileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = compose_config()
        cls.services = cls.cfg["services"]

    def test_three_services(self):
        self.assertEqual(set(self.services), {"gateway", "notes", "stats"})

    def test_only_gateway_publishes_a_port(self):
        self.assertTrue(self.services["gateway"].get("ports"))
        self.assertFalse(self.services["notes"].get("ports"))
        self.assertFalse(self.services["stats"].get("ports"))
        self.assertEqual(self.services["gateway"]["ports"][0]["host_ip"], "127.0.0.1")

    def test_backend_network_is_internal(self):
        self.assertTrue(self.cfg["networks"]["backend"].get("internal"))
        self.assertEqual(set(self.services["gateway"]["networks"]), {"frontend", "backend"})
        self.assertEqual(set(self.services["notes"]["networks"]), {"backend"})
        self.assertEqual(set(self.services["stats"]["networks"]), {"backend"})

    def test_stateful_services_use_named_volumes(self):
        for name, volume in (("notes", "notes-data"), ("stats", "stats-data")):
            mounts = self.services[name]["volumes"]
            self.assertIn((volume, "/data"), [(m["source"], m["target"]) for m in mounts])
            self.assertEqual(mounts[0]["type"], "volume")
        self.assertEqual(set(self.cfg["volumes"]), {"notes-data", "stats-data"})

    def test_startup_order_waits_for_health(self):
        self.assertEqual(self.services["gateway"]["depends_on"]["notes"]["condition"], "service_healthy")
        self.assertEqual(self.services["notes"]["depends_on"]["stats"]["condition"], "service_healthy")

    def test_service_urls_use_compose_dns_names(self):
        self.assertEqual(self.services["gateway"]["environment"]["NOTES_URL"], "http://notes:8000")
        self.assertEqual(self.services["notes"]["environment"]["STATS_URL"], "http://stats:8000")

    def test_every_service_has_a_dockerfile_with_healthcheck(self):
        for name in self.services:
            dockerfile = (ROOT / "services" / name / "Dockerfile").read_text()
            self.assertIn("HEALTHCHECK", dockerfile)
            self.assertIn("USER app", dockerfile)  # not running as root


if __name__ == "__main__":
    unittest.main()
