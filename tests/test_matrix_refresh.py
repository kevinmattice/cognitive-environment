import unittest
from unittest import mock

from gateway.runtime import MatrixAuthInfo, MatrixAuthSession, try_refresh_on_unknown_token
from matrix.client import MatrixClient, MatrixApiError


class MatrixRefreshTests(unittest.TestCase):
    def test_try_refresh_updates_access_token_and_persists_state(self) -> None:
        client = MatrixClient(homeserver_url="https://hs", access_token="OLD", user_id="@bot:hs", room_id="!r:hs")
        session = MatrixAuthSession(
            client=client,
            info=MatrixAuthInfo(mode="password_login", device_id="DEV", refresh_supported=True),
            refresh_token="RT",
            expires_in_ms=60000,
        )

        with mock.patch.object(client, "refresh", return_value={"access_token": "NEW", "refresh_token": "RT2", "expires_in_ms": 120000}):
            with mock.patch("gateway.runtime.save_auth_state", return_value=mock.Mock(status="updated")) as save_mock:
                ok = try_refresh_on_unknown_token(session, auth_state_path=mock.Mock())

        self.assertTrue(ok)
        self.assertEqual(client.access_token, "NEW")
        self.assertEqual(session.refresh_token, "RT2")
        self.assertEqual(session.expires_in_ms, 120000)
        self.assertTrue(save_mock.called)

    def test_refresh_failure_does_not_echo_refresh_token(self) -> None:
        client = MatrixClient(homeserver_url="https://hs", access_token="OLD", user_id="@bot:hs", room_id="!r:hs")
        session = MatrixAuthSession(
            client=client,
            info=MatrixAuthInfo(mode="password_login", device_id="DEV", refresh_supported=True),
            refresh_token="SECRET_REFRESH",
            expires_in_ms=60000,
        )

        err = MatrixApiError("Matrix API POST /_matrix/client/v3/refresh failed: 401 M_UNKNOWN_TOKEN", http_status=401, errcode="M_UNKNOWN_TOKEN")
        with mock.patch.object(client, "refresh", side_effect=err):
            ok = try_refresh_on_unknown_token(session, auth_state_path=mock.Mock())

        self.assertFalse(ok)
        self.assertNotIn("SECRET_REFRESH", str(err))
