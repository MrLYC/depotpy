"""Tests for install from offline bundle."""

import io
import json
import tarfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from depotpy.installer import BundleInstaller
from depotpy.commands.install import run_install


def _create_test_bundle(tmp_path, with_packages=True):
    """Create a test bundle with manifest and optional fake packages."""
    manifest_data = {
        "project_name": "myapp",
        "project_version": "1.0.0",
        "python_version": "3.11",
        "platforms": ["manylinux2014_x86_64"],
        "packages": [
            {
                "filename": "requests-2.31.0-py3-none-any.whl",
                "name": "requests",
                "version": "2.31.0",
                "sha256": "abc123",
                "size": 1024,
                "platform_tags": [],
            },
        ],
    }

    bundle_path = tmp_path / "myapp-1.0.0-offline.tar.gz"
    with tarfile.open(bundle_path, "w:gz") as tar:
        # Add manifest
        manifest_bytes = json.dumps(manifest_data).encode("utf-8")
        info = tarfile.TarInfo(name="myapp-1.0.0-offline/manifest.json")
        info.size = len(manifest_bytes)
        tar.addfile(info, fileobj=io.BytesIO(manifest_bytes))

        # Add fake package
        if with_packages:
            pkg_data = b"fake wheel content"
            pkg_info = tarfile.TarInfo(
                name="myapp-1.0.0-offline/packages/requests-2.31.0-py3-none-any.whl"
            )
            pkg_info.size = len(pkg_data)
            tar.addfile(pkg_info, fileobj=io.BytesIO(pkg_data))

    return bundle_path


class TestBundleInstaller:
    def test_nonexistent_bundle(self, tmp_path):
        installer = BundleInstaller(tmp_path / "nope.tar.gz")
        with pytest.raises(FileNotFoundError):
            installer.install()

    @patch("depotpy.installer.subprocess.run")
    def test_install_success(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        bundle = _create_test_bundle(tmp_path)
        installer = BundleInstaller(bundle)
        installer.install()

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "pip" in cmd
        assert "install" in cmd
        assert "--no-index" in cmd
        assert "--find-links" in cmd
        assert "requests" in cmd

    @patch("depotpy.installer.subprocess.run")
    def test_install_with_target(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        bundle = _create_test_bundle(tmp_path)
        installer = BundleInstaller(bundle)
        installer.install(target="/install/dir")

        cmd = mock_run.call_args[0][0]
        assert "--target" in cmd
        assert "/install/dir" in cmd

    @patch("depotpy.installer.subprocess.run")
    def test_install_failure(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="some error"
        )

        bundle = _create_test_bundle(tmp_path)
        installer = BundleInstaller(bundle)
        with pytest.raises(RuntimeError, match="pip install failed"):
            installer.install()

    def test_no_manifest_in_bundle(self, tmp_path):
        bundle_path = tmp_path / "bad.tar.gz"
        with tarfile.open(bundle_path, "w:gz") as tar:
            data = b"hello"
            info = tarfile.TarInfo(name="some/file.txt")
            info.size = len(data)
            tar.addfile(info, fileobj=io.BytesIO(data))

        installer = BundleInstaller(bundle_path)
        with pytest.raises(ValueError, match="No manifest.json"):
            installer.install()


class TestRunInstall:
    @patch("depotpy.installer.subprocess.run")
    def test_success(self, mock_run, tmp_path, capsys):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        bundle = _create_test_bundle(tmp_path)
        args = type("Args", (), {"bundle_path": str(bundle), "target": None})()
        result = run_install(args)
        assert result == 0

        output = capsys.readouterr().out
        assert "Successfully installed" in output

    def test_nonexistent(self, tmp_path, capsys):
        args = type("Args", (), {
            "bundle_path": str(tmp_path / "nope.tar.gz"),
            "target": None,
        })()
        result = run_install(args)
        assert result == 1

    def test_bad_bundle(self, tmp_path, capsys):
        # Bundle with no manifest -> ValueError
        bundle_path = tmp_path / "bad.tar.gz"
        with tarfile.open(bundle_path, "w:gz") as tar:
            data = b"hello"
            info = tarfile.TarInfo(name="some/file.txt")
            info.size = len(data)
            tar.addfile(info, fileobj=io.BytesIO(data))

        args = type("Args", (), {
            "bundle_path": str(bundle_path),
            "target": None,
        })()
        result = run_install(args)
        assert result == 1

    @patch("depotpy.installer.subprocess.run")
    def test_pip_failure(self, mock_run, tmp_path, capsys):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="pip error"
        )
        bundle = _create_test_bundle(tmp_path)
        args = type("Args", (), {
            "bundle_path": str(bundle),
            "target": None,
        })()
        result = run_install(args)
        assert result == 1
