import unittest
from unittest import mock

from gateway.pem_status import PemProbeError, get_pem_status


class PemStatusTests(unittest.TestCase):
    def test_disabled_config_returns_unavailable_without_probe(self) -> None:
        with mock.patch("gateway.pem_status._query_pem_status", side_effect=AssertionError("probe should not run")):
            status = get_pem_status({"pem_enabled": False})

        self.assertEqual(status.state, "unavailable")
        self.assertFalse(status.reachable)
        self.assertFalse(status.active)

    def test_active_activation_payload_maps_to_active(self) -> None:
        activation = {
            "result": {
                "activation": {
                    "active": True,
                    "activation_state": "active",
                    "inactive_reason": None,
                    "failure_reason": None,
                }
            }
        }
        meta = {"result": {"pem_project_root": "/tmp/project", "pem_case_root": "cases"}}

        with (
            mock.patch("gateway.pem_status._validate_client_config", return_value=None),
            mock.patch("gateway.pem_status._query_pem_status", return_value=(activation, meta)),
        ):
            status = get_pem_status(
                {
                    "pem_enabled": True,
                    "pem_launcher_path": "/bin/sh",
                    "pem_project_root": "/tmp",
                }
            )

        self.assertEqual(status.state, "active")
        self.assertTrue(status.reachable)
        self.assertTrue(status.active)
        self.assertEqual(status.diagnostics["meta"]["pem_case_root"], "cases")

    def test_inactive_activation_payload_maps_to_inactive(self) -> None:
        activation = {
            "result": {
                "activation": {
                    "active": False,
                    "activation_state": "inactive",
                    "inactive_reason": "explicit_opt_out",
                    "failure_reason": None,
                }
            }
        }

        with (
            mock.patch("gateway.pem_status._validate_client_config", return_value=None),
            mock.patch("gateway.pem_status._query_pem_status", return_value=(activation, None)),
        ):
            status = get_pem_status(
                {
                    "pem_enabled": True,
                    "pem_launcher_path": "/bin/sh",
                    "pem_project_root": "/tmp",
                }
            )

        self.assertEqual(status.state, "inactive")
        self.assertTrue(status.reachable)
        self.assertFalse(status.active)

    def test_activation_failure_reason_maps_to_unavailable(self) -> None:
        activation = {
            "result": {
                "activation": {
                    "active": False,
                    "activation_state": "inactive",
                    "inactive_reason": "restart_required",
                    "failure_reason": "restart_required",
                }
            }
        }

        with (
            mock.patch("gateway.pem_status._validate_client_config", return_value=None),
            mock.patch("gateway.pem_status._query_pem_status", return_value=(activation, None)),
        ):
            status = get_pem_status(
                {
                    "pem_enabled": True,
                    "pem_launcher_path": "/bin/sh",
                    "pem_project_root": "/tmp",
                }
            )

        self.assertEqual(status.state, "unavailable")
        self.assertTrue(status.reachable)
        self.assertFalse(status.active)

    def test_malformed_activation_payload_maps_to_ambiguous(self) -> None:
        activation = {"result": {"activation": {"active": "yes", "activation_state": "active"}}}

        with (
            mock.patch("gateway.pem_status._validate_client_config", return_value=None),
            mock.patch("gateway.pem_status._query_pem_status", return_value=(activation, None)),
        ):
            status = get_pem_status(
                {
                    "pem_enabled": True,
                    "pem_launcher_path": "/bin/sh",
                    "pem_project_root": "/tmp",
                }
            )

        self.assertEqual(status.state, "ambiguous")
        self.assertTrue(status.reachable)
        self.assertFalse(status.active)

    def test_probe_error_maps_to_unavailable(self) -> None:
        with (
            mock.patch("gateway.pem_status._validate_client_config", return_value=None),
            mock.patch("gateway.pem_status._query_pem_status", side_effect=PemProbeError("boom")),
        ):
            status = get_pem_status(
                {
                    "pem_enabled": True,
                    "pem_launcher_path": "/bin/sh",
                    "pem_project_root": "/tmp",
                }
            )

        self.assertEqual(status.state, "unavailable")
        self.assertFalse(status.reachable)
        self.assertFalse(status.active)
