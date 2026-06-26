"""Tests for tar.gz packing logic."""

import io
import json
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pydepot.models import Manifest, PackageFile, PackOptions
from pydepot.packer import PackBuilder, _create_bundle_tarball, _generate_readme


def _sample_manifest():
    return Manifest(
        project_name="myapp",
        project_version="1.0.0",
        python_version="3.11",
        platforms=["manylinux2014_x86_64"],
        packages=[
            PackageFile(
                filename="requests-2.31.0-py3-none-any.whl",
                name="requests",
                version="2.31.0",
                sha256="abc123",
                size=1024,
            ),
            PackageFile(
                filename="click-8.0.0-py3-none-any.whl",
                name="click",
                version="8.0.0",
                sha256="def456",
                size=512,
            ),
        ],
    )


class TestGenerateReadme:
    def test_contains_project_info(self):
        m = _sample_manifest()
        readme = _generate_readme(m)
        assert "myapp" in readme
        assert "1.0.0" in readme
        assert "3.11" in readme

    def test_contains_pip_install_command(self):
        m = _sample_manifest()
        readme = _generate_readme(m)
        assert "pip install --no-index --find-links ./packages" in readme

    def test_contains_package_names(self):
        m = _sample_manifest()
        readme = _generate_readme(m)
        assert "requests" in readme
        assert "click" in readme

    def test_contains_platform_info(self):
        m = _sample_manifest()
        readme = _generate_readme(m)
        assert "manylinux2014_x86_64" in readme

    def test_empty_packages(self):
        m = Manifest(
            project_name="empty",
            project_version="0.0.0",
            python_version="3.11",
            platforms=[],
        )
        readme = _generate_readme(m)
        assert "empty" in readme


class TestCreateBundleTarball:
    def test_creates_tarball(self, tmp_path):
        manifest = _sample_manifest()
        packages_dir = tmp_path / "packages"
        packages_dir.mkdir()

        # Create fake package files
        for pkg in manifest.packages:
            (packages_dir / pkg.filename).write_bytes(b"fake content")

        output_dir = tmp_path / "output"
        result = _create_bundle_tarball(
            output_path=output_dir,
            bundle_name="myapp-1.0.0-offline",
            manifest=manifest,
            packages_dir=packages_dir,
        )

        assert result.exists()
        assert result.name == "myapp-1.0.0-offline.tar.gz"

    def test_tarball_structure(self, tmp_path):
        manifest = _sample_manifest()
        packages_dir = tmp_path / "packages"
        packages_dir.mkdir()

        for pkg in manifest.packages:
            (packages_dir / pkg.filename).write_bytes(b"fake content")

        output_dir = tmp_path / "output"
        result = _create_bundle_tarball(
            output_path=output_dir,
            bundle_name="myapp-1.0.0-offline",
            manifest=manifest,
            packages_dir=packages_dir,
        )

        with tarfile.open(result, "r:gz") as tar:
            names = tar.getnames()
            assert "myapp-1.0.0-offline/README.md" in names
            assert "myapp-1.0.0-offline/manifest.json" in names
            assert "myapp-1.0.0-offline/packages/requests-2.31.0-py3-none-any.whl" in names
            assert "myapp-1.0.0-offline/packages/click-8.0.0-py3-none-any.whl" in names

    def test_manifest_json_valid(self, tmp_path):
        manifest = _sample_manifest()
        packages_dir = tmp_path / "packages"
        packages_dir.mkdir()

        for pkg in manifest.packages:
            (packages_dir / pkg.filename).write_bytes(b"fake content")

        output_dir = tmp_path / "output"
        result = _create_bundle_tarball(
            output_path=output_dir,
            bundle_name="myapp-1.0.0-offline",
            manifest=manifest,
            packages_dir=packages_dir,
        )

        with tarfile.open(result, "r:gz") as tar:
            f = tar.extractfile("myapp-1.0.0-offline/manifest.json")
            data = json.load(f)
            assert data["project_name"] == "myapp"
            assert len(data["packages"]) == 2

    def test_readme_content(self, tmp_path):
        manifest = _sample_manifest()
        packages_dir = tmp_path / "packages"
        packages_dir.mkdir()

        output_dir = tmp_path / "output"
        result = _create_bundle_tarball(
            output_path=output_dir,
            bundle_name="myapp-1.0.0-offline",
            manifest=manifest,
            packages_dir=packages_dir,
        )

        with tarfile.open(result, "r:gz") as tar:
            f = tar.extractfile("myapp-1.0.0-offline/README.md")
            content = f.read().decode("utf-8")
            assert "pip install --no-index" in content

    def test_missing_package_file_skipped(self, tmp_path):
        manifest = _sample_manifest()
        packages_dir = tmp_path / "packages"
        packages_dir.mkdir()
        # Don't create any package files

        output_dir = tmp_path / "output"
        result = _create_bundle_tarball(
            output_path=output_dir,
            bundle_name="myapp-1.0.0-offline",
            manifest=manifest,
            packages_dir=packages_dir,
        )

        with tarfile.open(result, "r:gz") as tar:
            names = tar.getnames()
            # README and manifest should still be there
            assert "myapp-1.0.0-offline/README.md" in names
            assert "myapp-1.0.0-offline/manifest.json" in names
            # But no package files
            assert len([n for n in names if n.startswith("myapp-1.0.0-offline/packages/")]) == 0

    def test_creates_output_dir(self, tmp_path):
        manifest = _sample_manifest()
        packages_dir = tmp_path / "packages"
        packages_dir.mkdir()

        output_dir = tmp_path / "new" / "nested" / "dir"
        result = _create_bundle_tarball(
            output_path=output_dir,
            bundle_name="myapp-1.0.0-offline",
            manifest=manifest,
            packages_dir=packages_dir,
        )
        assert output_dir.exists()
        assert result.exists()


class TestPackBuilder:
    @patch("pydepot.packer.download_packages")
    @patch("pydepot.packer.detect_project")
    def test_build(self, mock_detect, mock_download, tmp_path):
        from pydepot.models import DependencyManager, ProjectInfo

        mock_detect.return_value = ProjectInfo(
            path=tmp_path,
            name="myapp",
            version="1.0.0",
            dependencies=["requests"],
            manager=DependencyManager.PIP,
        )
        mock_download.return_value = [
            PackageFile(
                filename="requests-2.31.0-py3-none-any.whl",
                name="requests",
                version="2.31.0",
                sha256="abc",
                size=100,
            ),
        ]

        output_dir = tmp_path / "output"
        options = PackOptions(
            project_path=tmp_path,
            output_dir=output_dir,
        )
        builder = PackBuilder(options)

        # Need to create the file in the temp dir that download_packages would create
        # Since we mock download_packages, the files won't exist, but the tarball
        # creation will just skip missing files
        result = builder.build()
        assert result.exists()
        assert result.name == "myapp-1.0.0-offline.tar.gz"

    @patch("pydepot.packer.download_packages")
    @patch("pydepot.packer.detect_project")
    def test_build_with_platforms(self, mock_detect, mock_download, tmp_path):
        from pydepot.models import DependencyManager, ProjectInfo

        mock_detect.return_value = ProjectInfo(
            path=tmp_path,
            name="myapp",
            version="1.0.0",
            dependencies=["requests"],
            manager=DependencyManager.PIP,
        )
        mock_download.return_value = []

        output_dir = tmp_path / "output"
        options = PackOptions(
            project_path=tmp_path,
            output_dir=output_dir,
            platforms=["manylinux2014_x86_64", "macosx_11_0_arm64"],
        )
        builder = PackBuilder(options)
        result = builder.build()

        # Verify download was called with resolved platforms
        call_kwargs = mock_download.call_args
        platforms = call_kwargs.kwargs.get("platforms") or call_kwargs[1].get("platforms")
        assert len(platforms) == 2
