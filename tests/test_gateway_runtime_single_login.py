import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


import gateway.runtime as runtime


class GatewayRuntimeSingleLoginTests(unittest.TestCase):
    def test_main_establishes_auth_once_for_normal_run(self) -> None:
        cfg = {
            "matrix_auth_mode": "password_login",
            "homeserver_url": "https://hs",
            "user_id": "@bot:hs",
            "room_id": "!r:hs",
            "password": "SECRET_PASSWORD",
        }

        with tempfile.TemporaryDirectory() as td:
            config_path = Path(td) / "cce.json"
            config_path.write_text(json.dumps(cfg), encoding="utf-8")

            fake_session = mock.Mock()
            with mock.patch("gateway.runtime.establish_matrix_auth_session", return_value=fake_session) as establish_mock:
                with mock.patch("gateway.runtime.run_forever", return_value=0) as run_mock:
                    rc = runtime.main(["--config", str(config_path)])

        self.assertEqual(rc, 0)
        establish_mock.assert_called_once()
        run_mock.assert_called_once()
        self.assertIs(run_mock.call_args.kwargs["session"], fake_session)

    def test_rate_limit_error_includes_retry_seconds_when_available(self) -> None:
        cfg = {
            "matrix_auth_mode": "password_login",
            "homeserver_url": "https://hs",
            "user_id": "@bot:hs",
            "room_id": "!r:hs",
            "password": "SECRET_PASSWORD",
        }

        with tempfile.TemporaryDirectory() as td:
            config_path = Path(td) / "cce.json"
            config_path.write_text(json.dumps(cfg), encoding="utf-8")

            fake_session = mock.Mock()
            rate_exc = runtime.MatrixApiError(
                "rate",
                http_status=429,
                errcode="M_LIMIT_EXCEEDED",
                retry_after_ms=12_345,
            )
            with mock.patch("gateway.runtime.establish_matrix_auth_session", return_value=fake_session):
                with mock.patch("gateway.runtime.run_forever", side_effect=rate_exc):
                    with mock.patch("gateway.runtime.log") as log_mock:
                        rc = runtime.main(["--config", str(config_path)])

        self.assertEqual(rc, 1)
        logged = "\n".join(str(args[1]) for args, _kwargs in log_mock.call_args_list if len(args) >= 2)
        self.assertIn("wait ~13s", logged)
