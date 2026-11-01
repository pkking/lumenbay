"""NapCat group album API contract tests, without network access."""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

import pytest

from lumenbay.napcat import NapCatAlbumClient, NapCatError, UploadUncertain


def test_album_lookup_paginates(tmp_path: Path) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def fake(action: str, payload: dict[str, object]) -> dict[str, object]:
        calls.append((action, payload))
        if payload["attach_info"] == "":
            data: object = {
                "album_list": [{"album_id": "a1", "album_name": "Other"}],
                "has_more": True,
                "attach_info": "page2",
            }
        else:
            data = {
                "album_list": [{"album_id": "a2", "album_name": "Photos"}],
                "has_more": False,
                "attach_info": "",
            }
        return {"status": "ok", "retcode": 0, "data": data}

    client = NapCatAlbumClient(base_url="http://127.0.0.1:3000", access_token="", transport=fake)
    assert client.find_album("q1", "Photos").id == "a2"
    assert [payload["attach_info"] for _, payload in calls] == ["", "page2"]


def test_upload_single_and_batch_use_album_actions(tmp_path: Path) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def fake(action: str, payload: dict[str, object]) -> dict[str, object]:
        calls.append((action, payload))
        return {"status": "ok", "retcode": 0, "data": {"provisional": True}}

    client = NapCatAlbumClient(
        base_url="http://localhost:3000", access_token="test", transport=fake
    )
    first = tmp_path / "1.jpg"
    second = tmp_path / "2.jpg"
    first.write_bytes(b"image1")
    second.write_bytes(b"image2")
    assert client.upload_images(group_id="g", album_id="a", album_name="Album", paths=[first]) == {
        "provisional": True
    }
    assert calls[0][0] == "upload_image_to_qun_album"
    assert calls[0][1]["file"] == "base64://" + base64.b64encode(b"image1").decode()
    client.upload_images(group_id="g", album_id="a", album_name="Album", paths=[first, second])
    assert calls[1][0] == "upload_images_to_qun_album"
    assert isinstance(calls[1][1]["files"], list)
    assert len(calls[1][1]["files"]) == 2


def test_upload_error_is_uncertain_not_safe_to_retry(tmp_path: Path) -> None:
    def broken(action: str, payload: dict[str, object]) -> dict[str, object]:
        raise TimeoutError("private network detail")

    image = tmp_path / "a.jpg"
    image.write_bytes(b"sample")
    client = NapCatAlbumClient(base_url="http://localhost:3000", access_token="", transport=broken)
    with pytest.raises(UploadUncertain, match="not confirmed"):
        client.upload_images(group_id="q", album_id="a", album_name="A", paths=[image])


def test_reject_insecure_remote_endpoint() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        NapCatAlbumClient(base_url="http://example.com:3000", access_token="secret")


def test_missing_or_ambiguous_album_is_error() -> None:
    def fake(action: str, payload: dict[str, object]) -> dict[str, object]:
        return {
            "status": "ok",
            "retcode": 0,
            "data": {
                "album_list": [
                    {"album_id": "1", "album_name": "Photos"},
                    {"album_id": "2", "album_name": "Photos"},
                ],
                "has_more": False,
                "attach_info": "",
            },
        }

    client = NapCatAlbumClient(base_url="http://localhost:3000", access_token="", transport=fake)
    with pytest.raises(NapCatError, match="exactly one"):
        client.find_album("q", "Photos")


def test_redirect_is_never_followed() -> None:
    from urllib.request import Request

    from lumenbay.napcat import _NoRedirect

    assert _NoRedirect().redirect_request(
        Request("https://qq.example.test/get_qun_album_list"),
        None, 302, "Moved", {}, "https://untrusted.test/steal",
    ) is None


def test_reject_oversized_response(monkeypatch: pytest.MonkeyPatch) -> None:
    import lumenbay.napcat as napcat

    class DummyOpener:
        def open(self, request: object, timeout: float) -> BytesIO:
            return BytesIO(b"x" * (4 * 1024 * 1024 + 1))

    monkeypatch.setattr(napcat, "build_opener", lambda handler: DummyOpener())
    client = NapCatAlbumClient(base_url="http://localhost:3000", access_token="secret")
    with pytest.raises(NapCatError, match="size limit"):
        client.list_albums("test")


def test_pagination_stops_after_safety_limit() -> None:
    def forever(action: str, payload: dict[str, object]) -> dict[str, object]:
        return {"status": "ok", "retcode": 0, "data": {
            "album_list": [], "has_more": True,
            "attach_info": str(payload["attach_info"]) + "x",
        }}

    client = NapCatAlbumClient(
        base_url="http://localhost:3000", access_token="secret", transport=forever
    )
    with pytest.raises(NapCatError, match="safety limit"):
        client.list_albums("test")


def test_invalid_has_more_flag_fails_closed() -> None:
    def invalid(action: str, payload: dict[str, object]) -> dict[str, object]:
        return {"status": "ok", "retcode": 0, "data": {
            "album_list": [], "has_more": "false", "attach_info": "",
        }}

    client = NapCatAlbumClient(
        base_url="http://localhost:3000", access_token="", transport=invalid
    )
    with pytest.raises(NapCatError, match="pagination flag"):
        client.list_albums("test")
