import os
from unittest import TestCase
from unittest.mock import patch

from server import create_app


class EipAppTests(TestCase):
    def setUp(self):
        self._env = os.environ.copy()
        os.environ["EIP_HUB_HOST"] = "hub.test"
        os.environ["EIP_HUB_PORT"] = "3389"
        os.environ["EIP_STATUS_TIMEOUT"] = "0.01"
        os.environ["EIP_WAKE_COMMAND"] = "wakepc hub"
        self.app = create_app().test_client()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def test_health_lists_eip_app(self):
        response = self.app.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["apps"]["eip"], "/eip")

    @patch("apps.eip.probe_tcp", return_value=True)
    def test_hub_status_online(self, probe):
        response = self.app.get("/eip/api/status/hub")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["status"], "ONLINE")
        self.assertEqual(body["host"], "hub.test")
        self.assertEqual(body["port"], 3389)
        probe.assert_called_once_with("hub.test", 3389, 0.01)

    @patch("apps.eip.probe_tcp", return_value=False)
    def test_hub_status_offline(self, _probe):
        response = self.app.get("/eip/api/status/hub")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "OFFLINE")

    @patch.dict(os.environ, {}, clear=True)
    @patch("apps.eip.probe_tcp", return_value=False)
    def test_hub_status_uses_example_default_host(self, _probe):
        response = create_app().test_client().get("/eip/api/status/hub")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["host"], "hub.tailnet.example")

    @patch("apps.eip.subprocess.run")
    def test_wake_uses_configured_command(self, run):
        run.return_value.stdout = "sent"
        run.return_value.stderr = ""
        run.return_value.returncode = 0

        response = self.app.post("/eip/wake")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"sent", response.data)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], ["wakepc", "hub"])
