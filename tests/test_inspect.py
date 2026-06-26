"""Tests for inspect subcommand."""

import io
import json
import tarfile
from pathlib import Path

import pytest

from depotpy.commands.inspect import BundleInspector, run_inspect


def _create_test_bundle(tmp_path, manifest_data=None):
    """Create a test bundle tar.gz with a manifest."""
    if manifest_data is None:
        manifest_data = {
            "project_name": "myapp",
            "project_version": "1.0.0",
            "python_version": "3.11",
            "platforms": ["manylinux2014_x86_64"],
            "created_by": "depotpy",
            "package_count": 2,
            "total_size": 1536,
            "packages": [
                {
                    "filename": "requests-2.31.0-py3-none-any.whl",
                    "name": "requests",
                    "version": "2.31.0",
                    "sha256": "abc123",
                    "size": 1024,
                    "platform_tags": [],
                },
                {
                    "filename": "click-8.0.0-py3-none-any.whl",
                    "name": "click",
                    "version": "8.0.0",
                    "sha256": "def456",
                    "size": 512,
                    "platform_tags": [],
                },
            ],
        }

    bundle_path = tmp_path / "myapp-1.0.0-offline.tar.gz"
    with tarfile.open(bundle_path, "w:gz") as tar:
        manifest_bytes = json.dumps(manifest_data).encode("utf-8")
        info = tarfile.TarInfo(name="myapp-1.0.0-offline/manifest.json")
        info.size = len(manifest_bytes)
        tar.addfile(info, fileobj=io.BytesIO(manifest_bytes))

    return bundle_path


class TestBundleInspector:
    def test_get_manifest(self, tmp_path):
        bundle = _create_test_bundle(tmp_path)
        inspector = BundleInspector(bundle)
        data = inspector.get_manifest()
        assert data["project_name"] == "myapp"
        assert len(data["packages"]) == 2

    def test_nonexistent_bundle(self, tmp_path):
        inspector = BundleInspector(tmp_path / "nope.tar.gz")
        with pytest.raises(FileNotFoundError):
            inspector.get_manifest()

    def test_no_manifest_in_bundle(self, tmp_path):
        bundle_path = tmp_path / "empty.tar.gz"
        with tarfile.open(bundle_path, "w:gz") as tar:
            data = b"hello"
            info = tarfile.TarInfo(name="some/other/file.txt")
            info.size = len(data)
            tar.addfile(info, fileobj=io.BytesIO(data))

        inspector = BundleInspector(bundle_path)
        with pytest.raises(ValueError, match="No manifest.json"):
            inspector.get_manifest()

    def test_print_summary(self, tmp_path, capsys):
        bundle = _create_test_bundle(tmp_path)
        inspector = BundleInspector(bundle)
        inspector.print_summary()

        output = capsys.readouterr().err
        assert "myapp" in output
        assert "1.0.0" in output
        assert "3.11" in output
        assert "requests" in output
        assert "click" in output
        assert "manylinux2014_x86_64" in output


class TestRunInspect:
    def test_success(self, tmp_path, capsys):
        bundle = _create_test_bundle(tmp_path)
        args = type("Args", (), {"bundle_path": str(bundle), "json_output": False})()
        result = run_inspect(args)
        assert result == 0

        output = capsys.readouterr().err
        assert "myapp" in output

    def test_success_json(self, tmp_path, capsys):
        bundle = _create_test_bundle(tmp_path)
        args = type("Args", (), {"bundle_path": str(bundle), "json_output": True})()
        result = run_inspect(args)
        assert result == 0

        data = json.loads(capsys.readouterr().out)
        assert data["success"] is True
        assert data["project_name"] == "myapp"
        assert len(data["packages"]) == 2

    def test_nonexistent_file(self, tmp_path, capsys):
        args = type("Args", (), {"bundle_path": str(tmp_path / "nope.tar.gz"), "json_output": False})()
        result = run_inspect(args)
        assert result == 1
        assert "Error" in capsys.readouterr().err

    def test_nonexistent_json(self, tmp_path, capsys):
        args = type("Args", (), {"bundle_path": str(tmp_path / "nope.tar.gz"), "json_output": True})()
        result = run_inspect(args)
        assert result == 1

        data = json.loads(capsys.readouterr().out)
        assert data["success"] is False
        assert "error" in data

    def test_bad_bundle_no_manifest(self, tmp_path, capsys):
        bundle_path = tmp_path / "bad.tar.gz"
        with tarfile.open(bundle_path, "w:gz") as tar:
            data = b"hello"
            info = tarfile.TarInfo(name="some/file.txt")
            info.size = len(data)
            tar.addfile(info, fileobj=io.BytesIO(data))

        args = type("Args", (), {"bundle_path": str(bundle_path), "json_output": False})()
        result = run_inspect(args)
        assert result == 1
        assert "Error" in capsys.readouterr().err
