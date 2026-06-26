"""Platform tags and presets for cross-platform wheel downloads."""

from __future__ import annotations

import platform
import struct
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformTag:
    """Represents a platform tag for wheel compatibility."""

    os: str  # e.g. "linux", "macos", "windows"
    arch: str  # e.g. "x86_64", "aarch64", "arm64"
    tag: str  # e.g. "manylinux2014_x86_64", "macosx_11_0_arm64"

    def __str__(self) -> str:
        return self.tag


# Common platform tags
MANYLINUX_X86_64 = PlatformTag("linux", "x86_64", "manylinux2014_x86_64")
MANYLINUX_AARCH64 = PlatformTag("linux", "aarch64", "manylinux2014_aarch64")
MUSLLINUX_X86_64 = PlatformTag("linux", "x86_64", "musllinux_1_2_x86_64")
MUSLLINUX_AARCH64 = PlatformTag("linux", "aarch64", "musllinux_1_2_aarch64")
MACOSX_X86_64 = PlatformTag("macos", "x86_64", "macosx_11_0_x86_64")
MACOSX_ARM64 = PlatformTag("macos", "arm64", "macosx_11_0_arm64")
WIN_AMD64 = PlatformTag("windows", "x86_64", "win_amd64")
WIN_ARM64 = PlatformTag("windows", "arm64", "win_arm64")

# Preset groups
PLATFORM_PRESETS: dict[str, list[PlatformTag]] = {
    "all": [
        MANYLINUX_X86_64,
        MANYLINUX_AARCH64,
        MUSLLINUX_X86_64,
        MUSLLINUX_AARCH64,
        MACOSX_X86_64,
        MACOSX_ARM64,
        WIN_AMD64,
        WIN_ARM64,
    ],
    "linux": [
        MANYLINUX_X86_64,
        MANYLINUX_AARCH64,
        MUSLLINUX_X86_64,
        MUSLLINUX_AARCH64,
    ],
    "macos": [
        MACOSX_X86_64,
        MACOSX_ARM64,
    ],
    "windows": [
        WIN_AMD64,
        WIN_ARM64,
    ],
}

# Lookup from tag string to PlatformTag
_TAG_LOOKUP: dict[str, PlatformTag] = {}
for _preset_platforms in PLATFORM_PRESETS.values():
    for _pt in _preset_platforms:
        _TAG_LOOKUP[_pt.tag] = _pt


def get_current_platform() -> PlatformTag:
    """Detect the current platform and return a matching PlatformTag."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "linux":
        if machine in ("x86_64", "amd64"):
            return MANYLINUX_X86_64
        elif machine in ("aarch64", "arm64"):
            return MANYLINUX_AARCH64
    elif system == "darwin":
        if machine in ("x86_64", "amd64"):
            return MACOSX_X86_64
        elif machine in ("arm64", "aarch64"):
            return MACOSX_ARM64
    elif system == "windows":
        bits = struct.calcsize("P") * 8
        if machine in ("arm64", "aarch64"):
            return WIN_ARM64
        elif bits == 64:
            return WIN_AMD64

    # Fallback: construct a best-effort tag
    return PlatformTag(system, machine, f"{system}_{machine}")


def resolve_platforms(platform_args: list[str] | None) -> list[PlatformTag]:
    """Resolve platform arguments to a list of PlatformTags.

    Args:
        platform_args: List of platform strings from CLI. None means current platform only.

    Returns:
        List of PlatformTag objects.

    Raises:
        ValueError: If an unknown platform string is provided.
    """
    if platform_args is None:
        return [get_current_platform()]

    result: list[PlatformTag] = []
    seen: set[str] = set()

    for arg in platform_args:
        arg_lower = arg.lower()

        # Check presets first
        if arg_lower in PLATFORM_PRESETS:
            for pt in PLATFORM_PRESETS[arg_lower]:
                if pt.tag not in seen:
                    result.append(pt)
                    seen.add(pt.tag)
            continue

        # Check known tags
        if arg in _TAG_LOOKUP:
            if arg not in seen:
                result.append(_TAG_LOOKUP[arg])
                seen.add(arg)
            continue

        # Unknown platform - treat as raw tag
        raise ValueError(
            f"Unknown platform: '{arg}'. "
            f"Known platforms: {', '.join(sorted(_TAG_LOOKUP.keys()))}. "
            f"Known presets: {', '.join(sorted(PLATFORM_PRESETS.keys()))}."
        )

    return result


def get_python_version() -> str:
    """Get the current Python version as 'X.Y' string."""
    return f"{sys.version_info.major}.{sys.version_info.minor}"
