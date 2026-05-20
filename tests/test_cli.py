import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import shutil
import os
import json

from sophra_client.cli import parse_env_file, named_profiles, run_named_probe, cmd_named_rehabilitate

class TestSophraClient(unittest.TestCase):
    def setUp(self):
        import importlib
        import sophra_client.cli

        # Create a temporary directory for testing environment configuration
        self.test_dir = tempfile.mkdtemp()
        self.jiclaw_dir = Path(self.test_dir) / ".jiclaw"
        self.config_dir = self.jiclaw_dir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Mock environment variable for SOPHRA_WORKSPACE_ROOT
        self.env_patcher = patch.dict(os.environ, {"SOPHRA_WORKSPACE_ROOT": self.test_dir})
        self.env_patcher.start()

        # Reload the module to re-evaluate the module level paths
        importlib.reload(sophra_client.cli)

        # Create mock configurations
        self.sophra_env = self.config_dir / "sophra.env"
        self.sophra_env.write_text(
            "SOPHRA_BASE_URL=https://test.sophra.me\n"
            "SOPHRA_API_KEY=mock-master-key\n",
            encoding="utf-8"
        )

        self.agent_keys_env = self.config_dir / "sophra-agent-keys.env"
        self.agent_keys_env.write_text(
            "SOPHRA_API_KEY_SOPHRA_OPERATIONS_EXEC=mock-coo-key\n"
            "SOPHRA_API_KEY_SOPHRA_TECHNOLOGY_EXEC=mock-cto-key\n",
            encoding="utf-8"
        )

    def tearDown(self):
        import importlib
        import sophra_client.cli
        self.env_patcher.stop()
        shutil.rmtree(self.test_dir)
        importlib.reload(sophra_client.cli)

    def test_parse_env_file(self):
        res = parse_env_file(self.sophra_env)
        self.assertEqual(res.get("SOPHRA_BASE_URL"), "https://test.sophra.me")
        self.assertEqual(res.get("SOPHRA_API_KEY"), "mock-master-key")

    def test_named_profiles(self):
        profiles = named_profiles()
        # Should detect the profiles configured in agent_keys_env
        coo_profile = next((p for p in profiles if p["agentId"] == "sophra-operations-exec"), None)
        cto_profile = next((p for p in profiles if p["agentId"] == "sophra-technology-exec"), None)
        cmo_profile = next((p for p in profiles if p["agentId"] == "sophra-marketing-exec"), None)

        self.assertIsNotNone(coo_profile)
        self.assertTrue(coo_profile["configured"])
        self.assertEqual(coo_profile["baseUrl"], "https://test.sophra.me")

        self.assertIsNotNone(cto_profile)
        self.assertTrue(cto_profile["configured"])

        self.assertIsNotNone(cmo_profile)
        self.assertFalse(cmo_profile["configured"])  # Not in agent_keys_env

    @patch("urllib.request.urlopen")
    def test_run_named_probe(self, mock_urlopen):
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_response.read.return_value = json.dumps({
            "success": True,
            "agent": {"agent_id": "sophra-technology-exec"},
            "vital": {"overall_health": "green"},
            "event": {"success": True}
        }).encode("utf-8")
        mock_urlopen.return_value = mock_response

        # Execute probe
        res = run_named_probe("sophra-technology-exec", label="test-probe", entropy=0.75)

        self.assertTrue(res["ok"])
        self.assertEqual(res["agentId"], "sophra-technology-exec")
        self.assertTrue(res["register"]["success"])

    @patch("urllib.request.urlopen")
    def test_cmd_named_rehabilitate(self, mock_urlopen):
        import argparse
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_response.read.return_value = json.dumps({
            "success": True,
            "event": {"event_type": "agent_rehabilitated"}
        }).encode("utf-8")
        mock_urlopen.return_value = mock_response

        # Execute rehabilitation via command handler
        args = argparse.Namespace(profile="sophra-technology-exec")
        
        # We need to mock stdout print
        mock_print = MagicMock()
        with patch("builtins.print", mock_print):
            exit_code = cmd_named_rehabilitate(args)

        self.assertEqual(exit_code, 0)
        # Verify print was called with JSON payload containing rehabilitated: True
        printed_str = mock_print.call_args[0][0]
        printed_json = json.loads(printed_str)
        self.assertTrue(printed_json["ok"])
        self.assertTrue(printed_json["rehabilitated"])

if __name__ == "__main__":
    unittest.main()
