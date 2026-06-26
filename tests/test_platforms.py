"""Tests for platform tags and presets."""

import pytest

from pydepot.platforms import (
    MANYLINUX_X86_64,
    MANYLINUX_AARCH64,
    MACOSX_ARM64,
    MACOSX_X86_64,
    WIN_AMD64,
    PLATFORM_PRESETS,
    PlatformTag,
    get_current_platform,
    get_python_version,
    resolve_platforms,
)


class TestPlatformTag:
    def test_str(self):
        tag = PlatformTag("linux", "x86_64", "manylinux2014_x86_64")
        assert str(tag) == "manylinux2014_x86_64"

    def test_frozen(self):
        tag = MANYLINUX_X86_64
        with pytest.raises(AttributeError):
            tag.os = "windows"

    def test_equality(self):
        a = PlatformTag("linux", "x86_64", "manylinux2014_x86_64")
        b = PlatformTag("linux", "x86_64", "manylinux2014_x86_64")
        assert a == b

    def test_hash(self):
        a = PlatformTag("linux", "x86_64", "manylinux2014_x86_64")
        b = PlatformTag("linux", "x86_64", "manylinux2014_x86_64")
        assert hash(a) == hash(b)
        assert len({a, b}) == 1


class TestPresets:
    def test_all_preset_contains_all_platforms(self):
        all_platforms = PLATFORM_PRESETS["all"]
        assert len(all_platforms) == 8

    def test_linux_preset(self):
        linux = PLATFORM_PRESETS["linux"]
        assert all(pt.os == "linux" for pt in linux)

    def test_macos_preset(self):
        macos = PLATFORM_PRESETS["macos"]
        assert all(pt.os == "macos" for pt in macos)

    def test_windows_preset(self):
        windows = PLATFORM_PRESETS["windows"]
        assert all(pt.os == "windows" for pt in windows)


class TestResolvePlatforms:
    def test_none_returns_current(self):
        result = resolve_platforms(None)
        assert len(result) == 1

    def test_single_platform(self):
        result = resolve_platforms(["manylinux2014_x86_64"])
        assert result == [MANYLINUX_X86_64]

    def test_multiple_platforms(self):
        result = resolve_platforms(["manylinux2014_x86_64", "macosx_11_0_arm64"])
        assert result == [MANYLINUX_X86_64, MACOSX_ARM64]

    def test_preset_all(self):
        result = resolve_platforms(["all"])
        assert len(result) == 8

    def test_preset_linux(self):
        result = resolve_platforms(["linux"])
        assert all(pt.os == "linux" for pt in result)

    def test_deduplication(self):
        result = resolve_platforms(["manylinux2014_x86_64", "linux"])
        tags = [pt.tag for pt in result]
        assert len(tags) == len(set(tags))

    def test_unknown_platform_raises(self):
        with pytest.raises(ValueError, match="Unknown platform"):
            resolve_platforms(["totally_fake_platform"])

    def test_case_insensitive_presets(self):
        result = resolve_platforms(["ALL"])
        assert len(result) == 8


class TestGetCurrentPlatform:
    def test_returns_platform_tag(self):
        result = get_current_platform()
        assert isinstance(result, PlatformTag)
        assert result.os != ""
        assert result.arch != ""
        assert result.tag != ""


class TestGetPythonVersion:
    def test_format(self):
        version = get_python_version()
        parts = version.split(".")
        assert len(parts) == 2
        assert all(p.isdigit() for p in parts)
