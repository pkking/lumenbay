"""Windows desktop WeChat image adapter using the optional wxauto4 package.

This is a best-effort poll of the currently visible message list, not a
lossless historical or incremental message stream.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast


class WeChatReadError(RuntimeError):
    """The configured group or its original image cannot be read safely."""


class WeChatClient(Protocol):
    def ChatWith(self, who: str) -> object: ...
    def ChatInfo(self) -> dict[str, object]: ...
    def GetAllMessage(self) -> Sequence[object]: ...


@dataclass(frozen=True)
class ImageEvent:
    source_group: str
    message_id: str
    path: Path
    quality: str = "unknown"


class WxAutoImageSource:
    """Read image messages from exactly one explicitly authorized group."""

    def __init__(self, client: WeChatClient, group_name: str) -> None:
        if not group_name.strip():
            raise ValueError("A WeChat group name is required")
        self.client = client
        self.group_name = group_name

    @classmethod
    def from_desktop(cls, group_name: str) -> WxAutoImageSource:
        """Connect to the already authenticated Windows WeChat desktop session.

        Never starts a login, bypasses protections or imports wxauto in CI.
        Install `wxauto4` separately on a compatible Windows/Python version.
        """
        if sys.platform != "win32":
            raise RuntimeError("wxauto4 requires Windows desktop WeChat")
        try:
            package = importlib.import_module("wxauto4")
        except ImportError as exc:
            raise RuntimeError("Install wxauto4 on Windows to use this adapter") from exc
        return cls(cast(WeChatClient, package.WeChat()), group_name)

    def poll(self, *, seen: Callable[[str], bool] | None = None) -> list[ImageEvent]:
        """Poll current messages; never infer original quality from a file path.

        An unstable UI runtime message ID is used if wxauto does not expose a
        stable hash. Content hashing in the archive is the final deduplication
        boundary. Missed messages are possible with UI polling.
        """
        self.client.ChatWith(self.group_name)
        chat = self.client.ChatInfo()
        if chat.get("chat_name") != self.group_name:
            raise WeChatReadError("Active WeChat chat did not match configured group")
        result: list[ImageEvent] = []
        for msg in self.client.GetAllMessage():
            if getattr(msg, "type", None) != "image":
                continue
            raw_id = getattr(msg, "hash", None) or getattr(msg, "id", None)
            if raw_id is None or str(raw_id) == "":
                raise WeChatReadError("Image message has no usable identity")
            identity = str(raw_id)
            if seen is not None and seen(identity):
                continue
            downloader = getattr(msg, "download", None)
            if not callable(downloader):
                raise WeChatReadError("Image does not support downloading")
            try:
                candidate = downloader(original=True)
            except Exception as exc:
                raise WeChatReadError("Original image request failed") from exc
            if not isinstance(candidate, (str, Path)):
                raise WeChatReadError("Original image request did not return a file path")
            path = Path(candidate)
            if not path.is_file():
                raise WeChatReadError("Image download file is missing")
            # wxauto's reported path does not prove that remote original bytes
            # were obtained; callers must verify quality separately.
            result.append(ImageEvent(
                source_group=self.group_name,
                message_id=identity,
                path=path,
                quality="unknown",
            ))
        return result
