from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import uuid


class MatrixClientError(RuntimeError):
    """Raised when a Matrix API call fails or returns malformed data."""


class MatrixApiError(MatrixClientError):
    def __init__(self, message: str, *, http_status: int | None = None, errcode: str | None = None) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.errcode = errcode


class MatrixClient:
    def __init__(
        self,
        *,
        homeserver_url: str,
        access_token: str | None,
        user_id: str,
        room_id: str,
    ) -> None:
        self.homeserver_url = homeserver_url.rstrip("/")
        self.access_token = access_token
        self.user_id = user_id
        self.room_id = room_id
        self.last_sync_response: dict | None = None

    def initial_sync_cursor(self) -> str:
        response = self.sync(since=None, timeout_ms=0)
        self.last_sync_response = response
        next_batch = response.get("next_batch")
        if not isinstance(next_batch, str) or not next_batch:
            raise MatrixClientError("sync response missing next_batch")
        return next_batch

    def versions(self) -> dict:
        return self._request_json("GET", "/_matrix/client/versions", auth=False)

    def whoami(self) -> dict:
        return self._request_json("GET", "/_matrix/client/v3/account/whoami")

    def joined_rooms(self) -> list[str]:
        resp = self._request_json("GET", "/_matrix/client/v3/joined_rooms")
        rooms = resp.get("joined_rooms", [])
        if not isinstance(rooms, list) or not all(isinstance(x, str) for x in rooms):
            raise MatrixClientError("joined_rooms response malformed")
        return rooms

    def login_password(
        self,
        *,
        user_id: str,
        password: str,
        device_id: str | None = None,
        initial_device_display_name: str | None = None,
    ) -> dict:
        identifier = {"type": "m.id.user", "user": user_id}
        body: dict[str, object] = {
            "type": "m.login.password",
            "identifier": identifier,
            "password": password,
        }
        if device_id:
            body["device_id"] = device_id
        if initial_device_display_name:
            body["initial_device_display_name"] = initial_device_display_name

        return self._request_json("POST", "/_matrix/client/v3/login", body=body, auth=False)

    def refresh(self, *, refresh_token: str) -> dict:
        body = {"refresh_token": refresh_token}
        return self._request_json("POST", "/_matrix/client/v3/refresh", body=body, auth=False)

    def sync(self, *, since: str | None, timeout_ms: int) -> dict:
        query = {"timeout": str(timeout_ms)}
        if since:
            query["since"] = since
        response = self._request_json("GET", "/_matrix/client/v3/sync", query=query)
        self.last_sync_response = response
        return response

    def send_text(self, body: str) -> str:
        txn_id = uuid.uuid4().hex
        response = self._request_json(
            "PUT",
            f"/_matrix/client/v3/rooms/{urllib.parse.quote(self.room_id, safe='')}/send/m.room.message/{txn_id}",
            body={
                "msgtype": "m.text",
                "body": body,
            },
        )
        event_id = response.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise MatrixClientError("send response missing event_id")
        return event_id

    def room_joined(self, room_id: str, sync_response: dict) -> bool:
        rooms = sync_response.get("rooms", {})
        joined = rooms.get("join", {})
        return room_id in joined

    def text_events(self, sync_response: dict) -> list[dict]:
        rooms = sync_response.get("rooms", {})
        joined = rooms.get("join", {})
        room_data = joined.get(self.room_id, {})
        timeline = room_data.get("timeline", {})
        events = timeline.get("events", [])
        if not isinstance(events, list):
            raise MatrixClientError("room timeline events were not a list")

        results = []
        for event in events:
            if not isinstance(event, dict):
                continue
            if event.get("type") != "m.room.message":
                continue
            if event.get("content", {}).get("msgtype") != "m.text":
                continue
            results.append(event)
        return results

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        body: dict | None = None,
        auth: bool = True,
    ) -> dict:
        url = f"{self.homeserver_url}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"

        data = None
        headers = {"Accept": "application/json"}
        if auth:
            if not self.access_token:
                raise MatrixClientError("Matrix API call requires access_token, but none is configured")
            headers["Authorization"] = f"Bearer {self.access_token}"
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            errcode = None
            try:
                parsed = json.loads(detail)
                if isinstance(parsed, dict):
                    errcode = parsed.get("errcode") if isinstance(parsed.get("errcode"), str) else None
            except Exception:
                pass
            # Never include secrets; token is only in headers.
            raise MatrixApiError(
                f"Matrix API {method} {path} failed: {exc.code} {errcode or ""}".strip(),
                http_status=exc.code,
                errcode=errcode,
            ) from exc
        except urllib.error.URLError as exc:
            raise MatrixClientError(f"Matrix API {method} {path} failed: {exc.reason}") from exc

        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise MatrixClientError(f"Matrix API {method} {path} returned invalid JSON") from exc

        if not isinstance(parsed, dict):
            raise MatrixClientError(f"Matrix API {method} {path} returned non-object JSON")
        return parsed
