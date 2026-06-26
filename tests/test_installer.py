"""Tests for install from offline bundle."""

import io
import json
import tarfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from depotpy.installer import BundleInstaller, _check_conflicts, _get_installed_packages
from depotpy.commands.install import run_install
from depotpy.models import ConflictPolicy, Manifest, PackageFile


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


class TestGetInstalledPackages:
    @patch("depotpy.installer.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[{"name": "requests", "version": "2.31.0"}, {"name": "click", "version": "8.0"}]',
        )
        result = _get_installed_packages()
        assert result == {"requests": "2.31.0", "click": "8.0"}

    @patch("depotpy.installer.subprocess.run")
    def test_failure_returns_empty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = _get_installed_packages()
        assert result == {}


class TestCheckConflicts:
    def test_no_conflicts(self):
        manifest = Manifest(
            project_name="myapp", project_version="1.0.0",
            python_version="3.11", platforms=[],
            packages=[PackageFile("requests-2.31.0-py3-none-any.whl", "requests", "2.31.0", "abc", 100)],
        )
        installed = {"requests": "2.31.0"}
        assert _check_conflicts(manifest, installed) == []

    def test_version_conflict(self):
        manifest = Manifest(
            project_name="myapp", project_version="1.0.0",
            python_version="3.11", platforms=[],
            packages=[PackageFile("requests-2.31.0-py3-none-any.whl", "requests", "2.31.0", "abc", 100)],
        )
        installed = {"requests": "2.28.0"}
        conflicts = _check_conflicts(manifest, installed)
        assert len(conflicts) == 1
        assert "2.28.0" in conflicts[0]
        assert "2.31.0" in conflicts[0]

    def test_not_installed_no_conflict(self):
        manifest = Manifest(
            project_name="myapp", project_version="1.0.0",
            python_version="3.11", platforms=[],
            packages=[PackageFile("requests-2.31.0-py3-none-any.whl", "requests", "2.31.0", "abc", 100)],
        )
        assert _check_conflicts(manifest, {}) == []

    def test_name_normalization(self):
        manifest = Manifest(
            project_name="myapp", project_version="1.0.0",
            python_version="3.11", platforms=[],
            packages=[PackageFile("my-pkg-1.0-py3-none-any.whl", "my-pkg", "1.0", "abc", 100)],
        )
        installed = {"my_pkg": "0.9"}
        conflicts = _check_conflicts(manifest, installed)
        assert len(conflicts) == 1


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

    @patch("depotpy.installer.subprocess.run")
    def test_keep_policy_no_force(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        bundle = _create_test_bundle(tmp_path)
        installer = BundleInstaller(bundle)
        installer.install(on_conflict=ConflictPolicy.KEEP)

        cmd = mock_run.call_args[0][0]
        assert "--force-reinstall" not in cmd

    @patch("depotpy.installer.subprocess.run")
    def test_overwrite_policy_force_reinstall(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        bundle = _create_test_bundle(tmp_path)
        installer = BundleInstaller(bundle)
        installer.install(on_conflict=ConflictPolicy.OVERWRITE)

        cmd = mock_run.call_args[0][0]
        assert "--force-reinstall" in cmd

    @patch("depotpy.installer._get_installed_packages")
    @patch("depotpy.installer.subprocess.run")
    def test_error_policy_no_conflict(self, mock_run, mock_get_installed, tmp_path):
        mock_get_installed.return_value = {"requests": "2.31.0"}
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        bundle = _create_test_bundle(tmp_path)
        installer = BundleInstaller(bundle)
        installer.install(on_conflict=ConflictPolicy.ERROR)

        # Should proceed to pip install
        mock_run.assert_called_once()

    @patch("depotpy.installer._get_installed_packages")
    def test_error_policy_with_conflict(self, mock_get_installed, tmp_path):
        mock_get_installed.return_value = {"requests": "2.28.0"}

        bundle = _create_test_bundle(tmp_path)
        installer = BundleInstaller(bundle)
        with pytest.raises(RuntimeError, match="Version conflicts detected"):
            installer.install(on_conflict=ConflictPolicy.ERROR)

    @patch("depotpy.installer._get_installed_packages")
    @patch("depotpy.installer.subprocess.run")
    def test_error_policy_not_installed(self, mock_run, mock_get_installed, tmp_path):
        mock_get_installed.return_value = {}
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        bundle = _create_test_bundle(tmp_path)
        installer = BundleInstaller(bundle)
        installer.install(on_conflict=ConflictPolicy.ERROR)
        mock_run.assert_called_once()


class TestRunInstall:
    @patch("depotpy.installer.subprocess.run")
    def test_success(self, mock_run, tmp_path, capsys):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        bundle = _create_test_bundle(tmp_path)
        args = type("Args", (), {
            "bundle_path": str(bundle), "target": None, "on_conflict": "keep",
        })()
        result = run_install(args)
        assert result == 0

        output = capsys.readouterr().out
        assert "Successfully installed" in output

    def test_nonexistent(self, tmp_path, capsys):
        args = type("Args", (), {
            "bundle_path": str(tmp_path / "nope.tar.gz"),
            "target": None, "on_conflict": "keep",
        })()
        result = run_install(args)
        assert result == 1

    def test_bad_bundle(self, tmp_path, capsys):
        bundle_path = tmp_path / "bad.tar.gz"
        with tarfile.open(bundle_path, "w:gz") as tar:
            data = b"hello"
            info = tarfile.TarInfo(name="some/file.txt")
            info.size = len(data)
            tar.addfile(info, fileobj=io.BytesIO(data))

        args = type("Args", (), {
            "bundle_path": str(bundle_path),
            "target": None, "on_conflict": "keep",
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
            "target": None, "on_conflict": "keep",
        })()
        result = run_install(args)
        assert result == 1

    @patch("depotpy.installer._get_installed_packages")
    def test_error_policy_conflict_via_cli(self, mock_get_installed, tmp_path, capsys):
        mock_get_installed.return_value = {"requests": "1.0.0"}

        bundle = _create_test_bundle(tmp_path)
        args = type("Args", (), {
            "bundle_path": str(bundle),
            "target": None, "on_conflict": "error",
        })()
        result = run_install(args)
        assert result == 1

        err = capsys.readouterr().err
        assert "conflicts" in err.lower()
