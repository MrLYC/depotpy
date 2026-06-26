"""Tests for dependency resolution and wheel download."""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from pydepot.models import DependencyManager, ProjectInfo
from pydepot.platforms import MANYLINUX_X86_64, MACOSX_ARM64, PlatformTag
from pydepot.resolver import (
    _build_pip_download_cmd,
    _build_uv_download_cmd,
    _compute_sha256,
    _scan_downloaded_files,
    download_packages,
)


class TestComputeSha256:
    def test_hash(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        result = _compute_sha256(f)
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert result == expected

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_bytes(b"")
        result = _compute_sha256(f)
        assert result == hashlib.sha256(b"").hexdigest()


class TestBuildPipDownloadCmd:
    def test_basic(self, tmp_path):
        cmd = _build_pip_download_cmd(
            ["requests>=2.0", "click"],
            tmp_path,
            MANYLINUX_X86_64,
        )
        assert "pip" in cmd
        assert "download" in cmd
        assert "--dest" in cmd
        assert str(tmp_path) in cmd
        assert "--platform" in cmd
        assert "manylinux2014_x86_64" in cmd
        assert "requests>=2.0" in cmd
        assert "click" in cmd

    def test_with_python_version(self, tmp_path):
        cmd = _build_pip_download_cmd(
            ["requests"],
            tmp_path,
            MANYLINUX_X86_64,
            python_version="3.11",
        )
        assert "--python-version" in cmd
        assert "311" in cmd

    def test_with_exclude(self, tmp_path):
        cmd = _build_pip_download_cmd(
            ["requests>=2.0", "click", "pytest"],
            tmp_path,
            MANYLINUX_X86_64,
            exclude=["pytest"],
        )
        assert "requests>=2.0" in cmd
        assert "click" in cmd
        assert "pytest" not in cmd

    def test_exclude_case_insensitive(self, tmp_path):
        cmd = _build_pip_download_cmd(
            ["Requests>=2.0"],
            tmp_path,
            MANYLINUX_X86_64,
            exclude=["requests"],
        )
        assert "Requests>=2.0" not in cmd


class TestBuildUvDownloadCmd:
    def test_basic(self, tmp_path):
        cmd = _build_uv_download_cmd(
            ["requests"],
            tmp_path,
            MANYLINUX_X86_64,
        )
        assert cmd[0] == "uv"
        assert cmd[1] == "pip"
        assert "download" in cmd

    def test_python_version_format(self, tmp_path):
        cmd = _build_uv_download_cmd(
            ["requests"],
            tmp_path,
            MANYLINUX_X86_64,
            python_version="3.12",
        )
        # uv uses "3.12" format, not "312"
        idx = cmd.index("--python-version")
        assert cmd[idx + 1] == "3.12"


class TestScanDownloadedFiles:
    def test_wheel(self, tmp_path):
        whl = tmp_path / "requests-2.31.0-py3-none-any.whl"
        whl.write_bytes(b"fake wheel content")
        result = _scan_downloaded_files(tmp_path)
        assert len(result) == 1
        assert result[0].name == "requests"
        assert result[0].version == "2.31.0"
        assert result[0].is_wheel is True
        assert result[0].platform_tags == []  # "any" means no specific platform

    def test_platform_wheel(self, tmp_path):
        whl = tmp_path / "numpy-1.26.0-cp311-cp311-manylinux2014_x86_64.whl"
        whl.write_bytes(b"fake numpy wheel")
        result = _scan_downloaded_files(tmp_path)
        assert len(result) == 1
        assert result[0].name == "numpy"
        assert result[0].version == "1.26.0"
        assert result[0].platform_tags == ["manylinux2014_x86_64"]

    def test_sdist_tar_gz(self, tmp_path):
        sdist = tmp_path / "some-pkg-1.0.0.tar.gz"
        sdist.write_bytes(b"fake sdist")
        result = _scan_downloaded_files(tmp_path)
        assert len(result) == 1
        assert result[0].name == "some-pkg"
        assert result[0].version == "1.0.0"
        assert result[0].is_sdist is True

    def test_sdist_zip(self, tmp_path):
        sdist = tmp_path / "some-pkg-1.0.0.zip"
        sdist.write_bytes(b"fake sdist zip")
        result = _scan_downloaded_files(tmp_path)
        assert len(result) == 1
        assert result[0].is_sdist is True

    def test_ignores_non_package_files(self, tmp_path):
        (tmp_path / "README.md").write_text("hello")
        (tmp_path / "data.json").write_text("{}")
        result = _scan_downloaded_files(tmp_path)
        assert len(result) == 0

    def test_ignores_directories(self, tmp_path):
        (tmp_path / "subdir").mkdir()
        result = _scan_downloaded_files(tmp_path)
        assert len(result) == 0

    def test_sha256_computed(self, tmp_path):
        content = b"test content"
        whl = tmp_path / "pkg-1.0-py3-none-any.whl"
        whl.write_bytes(content)
        result = _scan_downloaded_files(tmp_path)
        assert result[0].sha256 == hashlib.sha256(content).hexdigest()

    def test_size_computed(self, tmp_path):
        content = b"x" * 1234
        whl = tmp_path / "pkg-1.0-py3-none-any.whl"
        whl.write_bytes(content)
        result = _scan_downloaded_files(tmp_path)
        assert result[0].size == 1234

    def test_multiple_files_sorted(self, tmp_path):
        (tmp_path / "b-1.0-py3-none-any.whl").write_bytes(b"b")
        (tmp_path / "a-1.0-py3-none-any.whl").write_bytes(b"a")
        result = _scan_downloaded_files(tmp_path)
        assert len(result) == 2
        assert result[0].name == "a"
        assert result[1].name == "b"


class TestRunDownloadCmd:
    @patch("pydepot.resolver.subprocess.run")
    def test_success(self, mock_run, tmp_path):
        from pydepot.resolver import _run_download_cmd
        mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")
        _run_download_cmd(["pip", "download"], tmp_path)
        mock_run.assert_called_once()

    @patch("pydepot.resolver.subprocess.run")
    def test_failure(self, mock_run, tmp_path):
        from pydepot.resolver import _run_download_cmd
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error msg")
        with pytest.raises(RuntimeError, match="Download command failed"):
            _run_download_cmd(["pip", "download"], tmp_path)

    @patch("pydepot.resolver.subprocess.run")
    def test_empty_stdout(self, mock_run, tmp_path):
        from pydepot.resolver import _run_download_cmd
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        _run_download_cmd(["pip", "download"], tmp_path)


class TestDownloadForPlatform:
    def test_pip_empty_deps(self, tmp_path):
        from pydepot.resolver import _download_for_platform_pip
        # Should return without calling anything
        _download_for_platform_pip([], tmp_path, MANYLINUX_X86_64)

    def test_uv_empty_deps(self, tmp_path):
        from pydepot.resolver import _download_for_platform_uv
        _download_for_platform_uv([], tmp_path, MANYLINUX_X86_64)


class TestDownloadPackages:
    def _make_project(self, tmp_path, manager=DependencyManager.PIP):
        return ProjectInfo(
            path=tmp_path,
            name="myapp",
            version="1.0.0",
            dependencies=["requests>=2.0", "click"],
            extras={"dev": ["pytest"]},
            manager=manager,
        )

    @patch("pydepot.resolver._run_download_cmd")
    def test_pip_backend(self, mock_run, tmp_path):
        project = self._make_project(tmp_path)
        download_dir = tmp_path / "downloads"

        # Create a fake downloaded wheel
        download_dir.mkdir()
        (download_dir / "requests-2.31.0-py3-none-any.whl").write_bytes(b"fake")

        result = download_packages(
            project, download_dir, [MANYLINUX_X86_64]
        )
        assert mock_run.called
        assert len(result) == 1

    @patch("pydepot.resolver._run_download_cmd")
    def test_uv_backend(self, mock_run, tmp_path):
        project = self._make_project(tmp_path, DependencyManager.UV)
        download_dir = tmp_path / "downloads"
        download_dir.mkdir()

        download_packages(project, download_dir, [MANYLINUX_X86_64])

        # Check that uv command was called
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "uv"

    @patch("pydepot.resolver._run_download_cmd")
    def test_multiple_platforms(self, mock_run, tmp_path):
        project = self._make_project(tmp_path)
        download_dir = tmp_path / "downloads"
        download_dir.mkdir()

        download_packages(
            project, download_dir, [MANYLINUX_X86_64, MACOSX_ARM64]
        )
        assert mock_run.call_count == 2

    @patch("pydepot.resolver._run_download_cmd")
    def test_include_extras(self, mock_run, tmp_path):
        project = self._make_project(tmp_path)
        download_dir = tmp_path / "downloads"
        download_dir.mkdir()

        download_packages(
            project, download_dir, [MANYLINUX_X86_64],
            include_extras=["dev"],
        )
        cmd = mock_run.call_args[0][0]
        assert "pytest" in cmd

    @patch("pydepot.resolver._run_download_cmd")
    def test_no_dependencies(self, mock_run, tmp_path):
        project = ProjectInfo(
            path=tmp_path, name="empty", version="1.0.0",
            manager=DependencyManager.PIP,
        )
        download_dir = tmp_path / "downloads"
        download_dir.mkdir()

        result = download_packages(project, download_dir, [MANYLINUX_X86_64])
        assert result == []
        mock_run.assert_not_called()

    @patch("pydepot.resolver._run_download_cmd")
    def test_fallback_on_failure(self, mock_run, tmp_path):
        project = self._make_project(tmp_path, DependencyManager.UV)
        download_dir = tmp_path / "downloads"
        download_dir.mkdir()

        # First call (uv) fails, second call (pip fallback) succeeds
        mock_run.side_effect = [RuntimeError("uv failed"), None]

        download_packages(project, download_dir, [MANYLINUX_X86_64])
        assert mock_run.call_count == 2
        # Second call should be pip
        second_cmd = mock_run.call_args_list[1][0][0]
        assert second_cmd[0] == "pip"

    @patch("pydepot.resolver._run_download_cmd")
    def test_pip_failure_raises(self, mock_run, tmp_path):
        project = self._make_project(tmp_path)
        download_dir = tmp_path / "downloads"
        download_dir.mkdir()

        mock_run.side_effect = RuntimeError("pip failed")

        with pytest.raises(RuntimeError, match="pip failed"):
            download_packages(project, download_dir, [MANYLINUX_X86_64])

    @patch("pydepot.resolver._run_download_cmd")
    def test_creates_download_dir(self, mock_run, tmp_path):
        project = self._make_project(tmp_path)
        download_dir = tmp_path / "new" / "dir"

        download_packages(project, download_dir, [MANYLINUX_X86_64])
        assert download_dir.exists()
