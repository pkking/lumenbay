"""NapCat OneBot QQ group album client.

Transport and API responses are intentionally explicit: an upload response is
not proof that a photo was durably listed in the remote album.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

JsonObject = dict[str, object]
Transport = Callable[[str, JsonObject], JsonObject]


_MAX_RESPONSE_BYTES = 4 * 1024 * 1024
_MAX_ALBUM_PAGES = 100


class _NoRedirect(HTTPRedirectHandler):
    """Never forward an authenticated request to a different host."""

    def redirect_request(
        self,
        req: Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> None:
        return None


class NapCatError(RuntimeError):
    """Malformed responses or unsuccessful album queries."""


class UploadUncertain(NapCatError):
    """Upload may have committed; callers must reconcile before retrying."""


@dataclass(frozen=True)
class Album:
    id: str
    name: str


class NapCatAlbumClient:
    """Small adapter for group album actions, with an injectable transport."""

    def __init__(
        self,
        *,
        base_url: str,
        access_token: str,
        timeout: float = 30.0,
        transport: Transport | None = None,
    ) -> None:
        parsed = urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("NapCat base_url must be an absolute HTTP(S) URL")
        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Use HTTPS when NapCat is not on the local host")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Credentials, query and fragment are not allowed in base_url")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.base_url = base_url.rstrip("/")
        self._token = access_token
        self.timeout = timeout
        self._transport = transport or self._http_post

    def _http_post(self, action: str, payload: JsonObject) -> JsonObject:
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        request = Request(self.base_url + "/" + action, data=body, headers=headers, method="POST")
        # urllib's default redirect policy can forward Authorization across origins.
        # A redirect must fail closed rather than leak the NapCat token.
        opener = build_opener(_NoRedirect())
        with opener.open(request, timeout=self.timeout) as response:
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise NapCatError("NapCat response exceeded size limit")
        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise NapCatError("Expected JSON object from NapCat")
        return parsed

    def _request(self, action: str, payload: JsonObject, *, upload: bool = False) -> object:
        try:
            result = self._transport(action, payload)
            if not isinstance(result, dict):
                raise NapCatError("Expected a NapCat response object")
            if result.get("status") != "ok" or result.get("retcode") != 0:
                raise NapCatError("NapCat reported an unsuccessful action")
            return result.get("data")
        except Exception as exc:
            if upload:
                raise UploadUncertain("Upload result is not confirmed") from exc
            if isinstance(exc, NapCatError):
                raise
            raise NapCatError("NapCat album request failed") from exc

    def list_albums(self, group_id: str) -> list[Album]:
        if not group_id:
            raise ValueError("group_id must be nonempty")
        albums: list[Album] = []
        cursor = ""
        visited: set[str] = set()
        for _ in range(_MAX_ALBUM_PAGES):
            data = self._request(
                "get_qun_album_list",
                {
                    "group_id": group_id,
                    "attach_info": cursor,
                },
            )
            if not isinstance(data, dict) or not isinstance(data.get("album_list"), list):
                raise NapCatError("Invalid QQ group album list response")
            for item in data["album_list"]:
                if not isinstance(item, dict):
                    raise NapCatError("Invalid group album entry")
                album_id, album_name = item.get("album_id"), item.get("album_name")
                if not isinstance(album_id, str) or not isinstance(album_name, str):
                    raise NapCatError("Album id or name is missing")
                albums.append(Album(id=album_id, name=album_name))
            has_more = data.get("has_more")
            if not isinstance(has_more, bool):
                raise NapCatError("Invalid QQ album pagination flag")
            if not has_more:
                return albums
            next_cursor = data.get("attach_info")
            if not isinstance(next_cursor, str) or not next_cursor or next_cursor in visited:
                raise NapCatError("Invalid or repeated QQ album pagination cursor")
            visited.add(next_cursor)
            cursor = next_cursor
        raise NapCatError("Exceeded QQ album pagination safety limit")

    def find_album(self, group_id: str, album_name: str) -> Album:
        matches = [album for album in self.list_albums(group_id) if album.name == album_name]
        if len(matches) != 1:
            raise NapCatError("Expected exactly one album matching the configured name")
        return matches[0]

    def upload_images(
        self,
        *,
        group_id: str,
        album_id: str,
        album_name: str,
        paths: list[Path],
    ) -> object:
        """Upload image bytes without relying on a shared host filesystem.

        The return value is a provisional receipt, NOT a verified remote image.
        A timeout, HTTP error, malformed reply or non-successful code is
        intentionally treated as uncertain.
        """
        if not all((group_id, album_id, album_name)) or not paths:
            raise ValueError("A destination and at least one image are required")
        files = [
            "base64://" + base64.b64encode(Path(path).read_bytes()).decode("ascii")
            for path in paths
        ]
        payload: JsonObject = {
            "group_id": group_id,
            "album_id": album_id,
            "album_name": album_name,
        }
        if len(files) == 1:
            payload["file"] = files[0]
            action = "upload_image_to_qun_album"
        else:
            payload["files"] = files
            action = "upload_images_to_qun_album"
        return self._request(action, payload, upload=True)

    def get_album_media(self, group_id: str, album_id: str, cursor: str = "") -> object:
        """Return raw media payload; remote verification is adapter-version specific."""
        if not group_id or not album_id:
            raise ValueError("Group and album IDs are required")
        return self._request(
            "get_group_album_media_list",
            {"group_id": group_id, "album_id": album_id, "attach_info": cursor},
        )
