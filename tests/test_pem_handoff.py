import unittest
from unittest import mock

from gateway.pem_handoff import handoff_to_pem
from gateway.pem_status import PemProbeError


class PemHandoffTests(unittest.TestCase):
    def _base_config(self) -> dict:
        return {
            "pem_enabled": True,
            "pem_launcher_path": "/bin/sh",
            "pem_project_root": "/tmp",
            "pem_timeout_s": 10,
        }

    def test_valid_pem_ask_returns_answer_with_footer(self) -> None:
        payload = {
            "ok": True,
            "result": {
                "answer": "Governed answer.",
                "breadcrumb": {
                    "case_id": "case-123",
                    "projection_hash": "abc123",
                    "reused_active_case": False,
                },
            },
        }
        with (
            mock.patch("gateway.pem_handoff.call_pem_tool", return_value=payload) as mocked_call,
            mock.patch("gateway.pem_handoff.pem_client_config_from_runtime", return_value=mock.Mock()),
        ):
            result = handoff_to_pem(self._base_config(), question="Fix this bug.")

        self.assertTrue(result.ok)
        self.assertEqual(
            result.reply,
            "Governed answer.\n\nPEM case: case-123\nProjection: abc123\nReused case: no",
        )
        mocked_call.assert_called_once()

    def test_reused_active_case_true_renders_yes(self) -> None:
        payload = {
            "ok": True,
            "result": {
                "answer": "Governed answer.",
                "breadcrumb": {
                    "case_id": "case-123",
                    "projection_hash": "abc123",
                    "reused_active_case": True,
                },
            },
        }
        with (
            mock.patch("gateway.pem_handoff.call_pem_tool", return_value=payload),
            mock.patch("gateway.pem_handoff.pem_client_config_from_runtime", return_value=mock.Mock()),
        ):
            result = handoff_to_pem(self._base_config(), question="Fix this bug.")

        self.assertTrue(result.ok)
        self.assertIn("Reused case: yes", result.reply or "")

    def test_pem_error_envelope_blocks(self) -> None:
        payload = {
            "ok": False,
            "error": {
                "code": "pem_answer_failed",
                "message": "PEM failed to synthesize an answer.",
            },
            "result": {
                "breadcrumb": {
                    "case_id": "case-123",
                    "projection_hash": "abc123",
                    "reused_active_case": False,
                }
            },
        }
        with (
            mock.patch("gateway.pem_handoff.call_pem_tool", return_value=payload),
            mock.patch("gateway.pem_handoff.pem_client_config_from_runtime", return_value=mock.Mock()),
        ):
            result = handoff_to_pem(self._base_config(), question="Fix this bug.")

        self.assertFalse(result.ok)
        self.assertIn("PEM failed to synthesize an answer.", result.error or "")

    def test_malformed_success_blocks(self) -> None:
        payload = {
            "ok": True,
            "result": {
                "breadcrumb": {
                    "case_id": "case-123",
                    "projection_hash": "abc123",
                    "reused_active_case": False,
                }
            },
        }
        with (
            mock.patch("gateway.pem_handoff.call_pem_tool", return_value=payload),
            mock.patch("gateway.pem_handoff.pem_client_config_from_runtime", return_value=mock.Mock()),
        ):
            result = handoff_to_pem(self._base_config(), question="Fix this bug.")

        self.assertFalse(result.ok)
        self.assertIn("no answer text", result.error or "")

    def test_timeout_blocks(self) -> None:
        with (
            mock.patch("gateway.pem_handoff.call_pem_tool", side_effect=PemProbeError("Timed out waiting for PEM response.")),
            mock.patch("gateway.pem_handoff.pem_client_config_from_runtime", return_value=mock.Mock()),
        ):
            result = handoff_to_pem(self._base_config(), question="Fix this bug.")

        self.assertFalse(result.ok)
        self.assertIn("Timed out waiting for PEM response.", result.error or "")
