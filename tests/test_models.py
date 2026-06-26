"""Tests for data models."""

from pathlib import Path

from depotpy.models import (
    DependencyManager,
    Manifest,
    PackageFile,
    PackOptions,
    ProjectInfo,
)


class TestDependencyManager:
    def test_values(self):
        assert DependencyManager.UV.value == "uv"
        assert DependencyManager.POETRY.value == "poetry"
        assert DependencyManager.PDM.value == "pdm"
        assert DependencyManager.PIPENV.value == "pipenv"
        assert DependencyManager.PIP.value == "pip"


class TestProjectInfo:
    def test_defaults(self):
        info = ProjectInfo(path=Path("/tmp"), name="myapp", version="1.0.0")
        assert info.python_requires is None
        assert info.dependencies == []
        assert info.extras == {}
        assert info.manager is None

    def test_full(self):
        info = ProjectInfo(
            path=Path("/project"),
            name="myapp",
            version="2.0.0",
            python_requires=">=3.11",
            dependencies=["requests>=2.0", "click"],
            extras={"dev": ["pytest"]},
            manager=DependencyManager.UV,
        )
        assert info.name == "myapp"
        assert len(info.dependencies) == 2
        assert "dev" in info.extras


class TestPackageFile:
    def test_wheel_detection(self):
        pkg = PackageFile(
            filename="requests-2.31.0-py3-none-any.whl",
            name="requests",
            version="2.31.0",
            sha256="abc123",
            size=1024,
        )
        assert pkg.is_wheel is True
        assert pkg.is_sdist is False

    def test_sdist_tar_gz_detection(self):
        pkg = PackageFile(
            filename="some-pkg-1.0.tar.gz",
            name="some-pkg",
            version="1.0",
            sha256="def456",
            size=2048,
        )
        assert pkg.is_wheel is False
        assert pkg.is_sdist is True

    def test_sdist_zip_detection(self):
        pkg = PackageFile(
            filename="some-pkg-1.0.zip",
            name="some-pkg",
            version="1.0",
            sha256="def456",
            size=2048,
        )
        assert pkg.is_wheel is False
        assert pkg.is_sdist is True

    def test_platform_tags(self):
        pkg = PackageFile(
            filename="numpy-1.0-cp311-cp311-manylinux2014_x86_64.whl",
            name="numpy",
            version="1.0",
            sha256="abc",
            size=4096,
            platform_tags=["manylinux2014_x86_64"],
        )
        assert pkg.platform_tags == ["manylinux2014_x86_64"]


class TestManifest:
    def test_total_size(self):
        m = Manifest(
            project_name="myapp",
            project_version="1.0.0",
            python_version="3.11",
            platforms=["manylinux2014_x86_64"],
            packages=[
                PackageFile("a.whl", "a", "1.0", "aaa", 100),
                PackageFile("b.whl", "b", "2.0", "bbb", 200),
            ],
        )
        assert m.total_size == 300
        assert m.package_count == 2

    def test_defaults(self):
        m = Manifest(
            project_name="myapp",
            project_version="1.0.0",
            python_version="3.11",
            platforms=[],
        )
        assert m.packages == []
        assert m.created_by == "depotpy"
        assert m.total_size == 0
        assert m.package_count == 0


class TestPackOptions:
    def test_defaults(self):
        opts = PackOptions(
            project_path=Path("/project"),
            output_dir=Path("/out"),
        )
        assert opts.platforms == []
        assert opts.python_version is None
        assert opts.exclude == []
        assert opts.include_extras == []
