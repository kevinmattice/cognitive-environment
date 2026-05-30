import json
import unittest
from unittest import mock


from gateway.runtime import establish_matrix_auth_session


def _json_response(payload: dict) -> mock.Mock:
    return mock.Mock(
        __enter__=lambda s: s,
        __exit__=lambda *a: None,
        read=lambda: json.dumps(payload).encode("utf-8"),
    )


class MatrixPasswordLoginTests(unittest.TestCase):
    def test_static_token_mode_still_works(self) -> None:
        cfg = {
            "matrix_auth_mode": "static_token",
            "homeserver_url": "https://hs",
            "access_token": "SECRET_TOKEN",
            "user_id": "@bot:hs",
            "room_id": "!r:hs",
        }
        session = establish_matrix_auth_session(cfg, auth_state_path=mock.Mock())
        self.assertEqual(session.info.mode, "static_token")
        self.assertFalse(session.info.refresh_supported)
        self.assertEqual(session.client.user_id, "@bot:hs")

    def test_password_login_success_no_refresh_token(self) -> None:
        cfg = {
            "matrix_auth_mode": "password_login",
            "homeserver_url": "https://hs",
            "user_id": "@bot:hs",
            "password": "SECRET_PASSWORD",
            "room_id": "!r:hs",
        }

        login_resp = {"access_token": "AT", "device_id": "DEV", "user_id": "@bot:hs"}

        def fake_urlopen(req, timeout=60):
            if req.full_url.endswith("/_matrix/client/v3/login"):
                return _json_response(login_resp)
            raise AssertionError(f"unexpected url: {req.full_url}")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            session = establish_matrix_auth_session(cfg, auth_state_path=mock.Mock())
            self.assertEqual(session.info.mode, "password_login")
            self.assertEqual(session.info.device_id, "DEV")
            self.assertFalse(session.info.refresh_supported)

    def test_password_login_user_id_mismatch_fails_without_secrets(self) -> None:
        cfg = {
            "matrix_auth_mode": "password_login",
            "homeserver_url": "https://hs",
            "user_id": "@bot:hs",
            "password": "SECRET_PASSWORD",
            "room_id": "!r:hs",
        }

        login_resp = {"access_token": "AT", "device_id": "DEV", "user_id": "@other:hs"}

        def fake_urlopen(req, timeout=60):
            if req.full_url.endswith("/_matrix/client/v3/login"):
                return _json_response(login_resp)
            raise AssertionError(f"unexpected url: {req.full_url}")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(Exception) as ctx:
                establish_matrix_auth_session(cfg, auth_state_path=mock.Mock())

        msg = str(ctx.exception)
        self.assertIn("login user_id mismatch", msg)
        self.assertNotIn("SECRET_PASSWORD", msg)
        self.assertNotIn("AT", msg)

    def test_password_login_refresh_supported_when_both_fields_present(self) -> None:
        cfg = {
            "matrix_auth_mode": "password_login",
            "homeserver_url": "https://hs",
            "user_id": "@bot:hs",
            "password": "SECRET_PASSWORD",
            "room_id": "!r:hs",
            "device_id": "DEV",
        }

        login_resp = {
            "access_token": "AT",
            "device_id": "DEV",
            "user_id": "@bot:hs",
            "refresh_token": "RT",
            "expires_in_ms": 60000,
        }

        def fake_urlopen(req, timeout=60):
            if req.full_url.endswith("/_matrix/client/v3/login"):
                return _json_response(login_resp)
            raise AssertionError(f"unexpected url: {req.full_url}")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with mock.patch("gateway.runtime.save_auth_state", return_value=mock.Mock(status="updated")):
                session = establish_matrix_auth_session(cfg, auth_state_path=mock.Mock())

        self.assertTrue(session.info.refresh_supported)
        self.assertEqual(session.refresh_token, "RT")
