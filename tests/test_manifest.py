"""Tests for manifest generation and reading."""

import json
from pathlib import Path

import pytest

from pydepot.manifest import (
    manifest_from_dict,
    manifest_to_dict,
    read_manifest,
    write_manifest,
)
from pydepot.models import Manifest, PackageFile


def _sample_manifest():
    return Manifest(
        project_name="myapp",
        project_version="1.0.0",
        python_version="3.11",
        platforms=["manylinux2014_x86_64", "macosx_11_0_arm64"],
        packages=[
            PackageFile(
                filename="requests-2.31.0-py3-none-any.whl",
                name="requests",
                version="2.31.0",
                sha256="abc123",
                size=1024,
                platform_tags=[],
            ),
            PackageFile(
                filename="numpy-1.26.0-cp311-cp311-manylinux2014_x86_64.whl",
                name="numpy",
                version="1.26.0",
                sha256="def456",
                size=4096,
                platform_tags=["manylinux2014_x86_64"],
            ),
        ],
    )


class TestManifestToDict:
    def test_basic(self):
        m = _sample_manifest()
        d = manifest_to_dict(m)
        assert d["project_name"] == "myapp"
        assert d["project_version"] == "1.0.0"
        assert d["python_version"] == "3.11"
        assert d["package_count"] == 2
        assert d["total_size"] == 5120
        assert len(d["packages"]) == 2

    def test_package_fields(self):
        m = _sample_manifest()
        d = manifest_to_dict(m)
        pkg = d["packages"][0]
        assert pkg["filename"] == "requests-2.31.0-py3-none-any.whl"
        assert pkg["name"] == "requests"
        assert pkg["version"] == "2.31.0"
        assert pkg["sha256"] == "abc123"
        assert pkg["size"] == 1024
        assert pkg["platform_tags"] == []

    def test_empty_packages(self):
        m = Manifest(
            project_name="empty",
            project_version="0.0.0",
            python_version="3.11",
            platforms=[],
        )
        d = manifest_to_dict(m)
        assert d["packages"] == []
        assert d["package_count"] == 0
        assert d["total_size"] == 0


class TestManifestFromDict:
    def test_roundtrip(self):
        original = _sample_manifest()
        d = manifest_to_dict(original)
        restored = manifest_from_dict(d)
        assert restored.project_name == original.project_name
        assert restored.project_version == original.project_version
        assert restored.python_version == original.python_version
        assert restored.platforms == original.platforms
        assert len(restored.packages) == len(original.packages)
        assert restored.packages[0].filename == original.packages[0].filename

    def test_missing_optional_fields(self):
        d = {
            "project_name": "test",
            "project_version": "1.0.0",
            "python_version": "3.11",
        }
        m = manifest_from_dict(d)
        assert m.platforms == []
        assert m.packages == []
        assert m.created_by == "pydepot"

    def test_missing_required_field_raises(self):
        with pytest.raises(KeyError):
            manifest_from_dict({"project_name": "test"})


class TestWriteAndReadManifest:
    def test_write_read_roundtrip(self, tmp_path):
        original = _sample_manifest()
        path = tmp_path / "manifest.json"

        write_manifest(original, path)
        assert path.exists()

        restored = read_manifest(path)
        assert restored.project_name == original.project_name
        assert restored.package_count == original.package_count

    def test_written_file_is_valid_json(self, tmp_path):
        m = _sample_manifest()
        path = tmp_path / "manifest.json"
        write_manifest(m, path)

        data = json.loads(path.read_text())
        assert isinstance(data, dict)
        assert data["project_name"] == "myapp"

    def test_written_file_is_pretty_printed(self, tmp_path):
        m = _sample_manifest()
        path = tmp_path / "manifest.json"
        write_manifest(m, path)

        content = path.read_text()
        # Pretty-printed JSON has newlines
        assert "\n" in content
        # Ends with newline
        assert content.endswith("\n")

    def test_read_nonexistent_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_manifest(tmp_path / "nope.json")

    def test_read_invalid_json_raises(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json at all")
        with pytest.raises(json.JSONDecodeError):
            read_manifest(path)
