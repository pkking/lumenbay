"""wxauto4 adapter tests, independent of Windows desktop and accounts."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from lumenbay.wechat import WeChatReadError, WxAutoImageSource


class FakeWeChat:
    def __init__(
        self,
        messages: list[object],
        chat_name: str = "Authorized group",
        chat_type: str = "group",
    ) -> None:
        self.messages = messages
        self.chat_name = chat_name
        self.chat_type = chat_type
        self.opened: str | None = None

    def ChatWith(self, who: str) -> None:
        self.opened = who

    def ChatInfo(self) -> dict[str, object]:
        return {"chat_name": self.chat_name, "chat_type": self.chat_type}

    def GetAllMessage(self) -> list[object]:
        return self.messages


class FakeImage:
    type = "image"
    id = "ui-message-1"
    hash = "stable-hash-1"

    def __init__(self, file: Path) -> None:
        self.file = file
        self.original_calls: list[bool] = []

    def download(self, *, original: bool = False) -> Path:
        self.original_calls.append(original)
        return self.file


def test_poll_only_images_and_verify_active_chat(tmp_path: Path) -> None:
    file = tmp_path / "photo.jpg"
    file.write_bytes(b"test-image")
    image = FakeImage(file)
    fake = FakeWeChat([SimpleNamespace(type="text"), image])
    events = WxAutoImageSource(fake, "Authorized group").poll()
    assert fake.opened == "Authorized group"
    assert len(events) == 1
    assert events[0].message_id == "stable-hash-1"
    assert events[0].quality == "unknown"
    assert image.original_calls == [True]


def test_seen_images_are_not_downloaded(tmp_path: Path) -> None:
    image = FakeImage(tmp_path / "not-downloaded.jpg")
    source = WxAutoImageSource(FakeWeChat([image]), "Authorized group")
    assert source.poll(seen=lambda identity: identity == "stable-hash-1") == []
    assert image.original_calls == []


def test_wrong_chat_fails_closed(tmp_path: Path) -> None:
    source = WxAutoImageSource(FakeWeChat([], chat_name="Different group"), "Authorized group")
    with pytest.raises(WeChatReadError, match="group and type"):
        source.poll()


def test_same_name_friend_is_never_archived() -> None:
    fake = FakeWeChat([], chat_type="friend")
    with pytest.raises(WeChatReadError, match="group and type"):
        WxAutoImageSource(fake, "Authorized group").poll()


def test_callable_message_hash_is_rejected(tmp_path: Path) -> None:
    file = tmp_path / "photo.jpg"
    file.write_bytes(b"media")
    image = FakeImage(file)
    image.hash = lambda: "unstable"  # type: ignore[method-assign]
    with pytest.raises(WeChatReadError, match="identity"):
        WxAutoImageSource(FakeWeChat([image]), "Authorized group").poll()


def test_unavailable_file_fails_without_fake_success(tmp_path: Path) -> None:
    source = WxAutoImageSource(
        FakeWeChat([FakeImage(tmp_path / "missing.jpg")]),
        "Authorized group",
    )
    with pytest.raises(WeChatReadError, match="missing"):
        source.poll()


def test_invalid_group_rejected() -> None:
    with pytest.raises(ValueError, match="group"):
        WxAutoImageSource(FakeWeChat([]), "")
