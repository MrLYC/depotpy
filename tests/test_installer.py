"""Tests for install from offline bundle."""

import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from depotpy.installer import BundleInstaller, _check_conflicts, _get_installed_packages
from depotpy.commands.install import run_install
from depotpy.models import ConflictPolicy, Manifest, PackageFile


def _create_test_bundle(tmp_path, with_packages=True, package_data=b"fake wheel content", sha256=None, size=None):
    """Create a test bundle with manifest and optional fake packages."""
    package_sha256 = sha256 or hashlib.sha256(package_data).hexdigest()
    package_size = len(package_data) if size is None else size
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
                "sha256": package_sha256,
                "size": package_size,
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
            pkg_info = tarfile.TarInfo(
                name="myapp-1.0.0-offline/packages/requests-2.31.0-py3-none-any.whl"
            )
            pkg_info.size = len(package_data)
            tar.addfile(pkg_info, fileobj=io.BytesIO(package_data))

    return bundle_path


class TestGetInstalledPackages:
    @patch("depotpy.installer.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[{"name": "requests", "version": "2.31.0"}, {"name": "click", "version": "8.0"}]',
        )
        result = _get_installed_packages()
        assert mock_run.call_args[0][0] == [sys.executable, "-m", "pip", "list", "--format=json"]
        assert result == {"requests": "2.31.0", "click": "8.0"}

    @patch("depotpy.installer.subprocess.run")
    def test_failure_returns_empty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = _get_installed_packages()
        assert result == {}

    @patch("depotpy.installer.subprocess.run")
    def test_invalid_json_raises(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="not json")
        with pytest.raises(RuntimeError, match="Failed to parse pip list output"):
            _get_installed_packages()

    @patch("depotpy.installer.subprocess.run")
    def test_pip_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError("pip not found")
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
        assert cmd[:4] == [sys.executable, "-m", "pip", "install"]
        assert "--no-index" in cmd
        assert "--find-links" in cmd
        assert "requests==2.31.0" in cmd
        assert not any(arg.endswith("requests-2.31.0-py3-none-any.whl") for arg in cmd)
        assert "requests" not in cmd

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

    def test_install_missing_manifest_package_file(self, tmp_path):
        bundle = _create_test_bundle(tmp_path, with_packages=False)
        installer = BundleInstaller(bundle)
        with pytest.raises(RuntimeError, match="Package file missing"):
            installer.install()

    def test_install_package_size_mismatch(self, tmp_path):
        bundle = _create_test_bundle(tmp_path, size=999)
        installer = BundleInstaller(bundle)
        with pytest.raises(RuntimeError, match="Package size mismatch"):
            installer.install()

    def test_install_package_sha256_mismatch(self, tmp_path):
        bundle = _create_test_bundle(tmp_path, sha256="0" * 64)
        installer = BundleInstaller(bundle)
        with pytest.raises(RuntimeError, match="Package SHA-256 mismatch"):
            installer.install()

    def test_build_install_cmd_uses_pinned_requirements_for_platform_selection(self, tmp_path):
        manifest = Manifest(
            project_name="myapp",
            project_version="1.0.0",
            python_version="3.11",
            platforms=["manylinux2014_x86_64", "macosx_11_0_arm64"],
            packages=[
                PackageFile("demo-1.0.0-cp311-cp311-manylinux2014_x86_64.whl", "demo", "1.0.0", "a", 1),
                PackageFile("demo-1.0.0-cp311-cp311-macosx_11_0_arm64.whl", "demo", "1.0.0", "b", 1),
            ],
        )
        installer = BundleInstaller(tmp_path / "bundle.tar.gz")
        cmd = installer._build_install_cmd(manifest, tmp_path / "packages")
        assert cmd.count("demo==1.0.0") == 1
        assert not any(arg.endswith(".whl") for arg in cmd)

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
            "bundle_path": str(bundle), "target": None,
            "on_conflict": "keep", "json_output": False,
        })()
        result = run_install(args)
        assert result == 0
        assert "Successfully installed" in capsys.readouterr().err

    @patch("depotpy.installer.subprocess.run")
    def test_success_json(self, mock_run, tmp_path, capsys):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        bundle = _create_test_bundle(tmp_path)
        args = type("Args", (), {
            "bundle_path": str(bundle), "target": None,
            "on_conflict": "keep", "json_output": True,
        })()
        result = run_install(args)
        assert result == 0

        data = json.loads(capsys.readouterr().out)
        assert data["success"] is True
        assert data["on_conflict"] == "keep"

    def test_nonexistent(self, tmp_path, capsys):
        args = type("Args", (), {
            "bundle_path": str(tmp_path / "nope.tar.gz"),
            "target": None, "on_conflict": "keep", "json_output": False,
        })()
        result = run_install(args)
        assert result == 1

    def test_nonexistent_json(self, tmp_path, capsys):
        args = type("Args", (), {
            "bundle_path": str(tmp_path / "nope.tar.gz"),
            "target": None, "on_conflict": "keep", "json_output": True,
        })()
        result = run_install(args)
        assert result == 1

        data = json.loads(capsys.readouterr().out)
        assert data["success"] is False

    def test_bad_bundle(self, tmp_path, capsys):
        bundle_path = tmp_path / "bad.tar.gz"
        with tarfile.open(bundle_path, "w:gz") as tar:
            data = b"hello"
            info = tarfile.TarInfo(name="some/file.txt")
            info.size = len(data)
            tar.addfile(info, fileobj=io.BytesIO(data))

        args = type("Args", (), {
            "bundle_path": str(bundle_path),
            "target": None, "on_conflict": "keep", "json_output": False,
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
            "target": None, "on_conflict": "keep", "json_output": False,
        })()
        result = run_install(args)
        assert result == 1

    @patch("depotpy.installer._get_installed_packages")
    def test_error_policy_conflict_via_cli(self, mock_get_installed, tmp_path, capsys):
        mock_get_installed.return_value = {"requests": "1.0.0"}

        bundle = _create_test_bundle(tmp_path)
        args = type("Args", (), {
            "bundle_path": str(bundle),
            "target": None, "on_conflict": "error", "json_output": False,
        })()
        result = run_install(args)
        assert result == 1
        assert "conflicts" in capsys.readouterr().err.lower()
