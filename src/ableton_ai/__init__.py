"""Control Ableton Live from an AI assistant over MCP."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .config import MODIFYING_COMMANDS, Settings, settings
from .connection import AbletonConnection, get_ableton_connection, reset_connection
from .exceptions import (
    AbletonMCPError,
    CommandFailedError,
    CommandTimeoutError,
    ConnectionFailedError,
    InvalidResponseError,
    NotConnectedError,
)

try:
    # Read the version from package metadata rather than hardcoding it here.
    # The distribution is named "ableton-ai" in pyproject.toml.
    __version__ = version("ableton-ai")
except PackageNotFoundError:  # pragma: no cover - running from a source tree
    __version__ = "0.0.0.dev0"

__all__ = [
    "MODIFYING_COMMANDS",
    "AbletonConnection",
    "AbletonMCPError",
    "CommandFailedError",
    "CommandTimeoutError",
    "ConnectionFailedError",
    "InvalidResponseError",
    "NotConnectedError",
    "Settings",
    "__version__",
    "get_ableton_connection",
    "reset_connection",
    "settings",
]
