import json
import unittest
from unittest import mock

import urllib.error

from matrix.client import MatrixApiError, MatrixClient
from gateway.runtime import check_connection


class MatrixAuthHardeningTests(unittest.TestCase):
    def test_matrix_api_error_captures_errcode_without_secrets(self) -> None:
        client = MatrixClient(homeserver_url="https://example.invalid", access_token="SECRET_TOKEN", user_id="@u:x", room_id="!r:x")

        body = json.dumps({"errcode": "M_UNKNOWN_TOKEN", "error": "Token is not active"}).encode("utf-8")
        http_err = urllib.error.HTTPError("http://x", 401, "Unauthorized", hdrs=None, fp=mock.Mock(read=mock.Mock(return_value=body)))

        with mock.patch("urllib.request.urlopen", side_effect=http_err):
            with self.assertRaises(MatrixApiError) as ctx:
                client.whoami()

        exc = ctx.exception
        self.assertEqual(exc.http_status, 401)
        self.assertEqual(exc.errcode, "M_UNKNOWN_TOKEN")
        self.assertNotIn("SECRET_TOKEN", str(exc))

    def test_check_connection_fails_on_user_id_mismatch(self) -> None:
        client = MatrixClient(homeserver_url="https://hs", access_token="T", user_id="@config:x", room_id="!r:x")

        with mock.patch.object(client, "versions", return_value={"versions": ["v1.1"]}), mock.patch.object(
            client, "whoami", return_value={"user_id": "@whoami:x"}
        ):
            with self.assertRaises(Exception) as ctx:
                check_connection(client, "!room:x")
        self.assertIn("config user_id mismatch", str(ctx.exception))

