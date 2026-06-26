"""Tests for dependency manager detection."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from depotpy.detector import (
    _detect_manager,
    _extract_from_pipfile_lock,
    _extract_from_pyproject,
    _extract_from_requirements_txt,
    _extract_from_setup_cfg,
    detect_project,
)
from depotpy.models import DependencyManager


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory."""
    return tmp_path


class TestDetectManager:
    def test_uv_by_lockfile(self, tmp_project):
        (tmp_project / "pyproject.toml").write_text('[project]\nname = "test"\n')
        (tmp_project / "uv.lock").write_text("")
        with patch("shutil.which", return_value="/usr/bin/uv"):
            assert _detect_manager(tmp_project) == DependencyManager.UV

    def test_uv_by_tool_section(self, tmp_project):
        (tmp_project / "pyproject.toml").write_text(
            '[project]\nname = "test"\n[tool.uv]\n'
        )
        with patch("shutil.which", return_value="/usr/bin/uv"):
            assert _detect_manager(tmp_project) == DependencyManager.UV

    def test_uv_not_installed_falls_through(self, tmp_project):
        (tmp_project / "pyproject.toml").write_text(
            '[project]\nname = "test"\n[tool.uv]\n'
        )
        with patch("shutil.which", return_value=None):
            assert _detect_manager(tmp_project) == DependencyManager.PIP

    def test_poetry_by_lockfile(self, tmp_project):
        (tmp_project / "pyproject.toml").write_text('[project]\nname = "test"\n')
        (tmp_project / "poetry.lock").write_text("")
        with patch("shutil.which", side_effect=lambda x: "/usr/bin/poetry" if x == "poetry" else None):
            assert _detect_manager(tmp_project) == DependencyManager.POETRY

    def test_poetry_by_tool_section(self, tmp_project):
        (tmp_project / "pyproject.toml").write_text(
            '[project]\nname = "test"\n[tool.poetry]\n'
        )
        with patch("shutil.which", side_effect=lambda x: "/usr/bin/poetry" if x == "poetry" else None):
            assert _detect_manager(tmp_project) == DependencyManager.POETRY

    def test_pdm_by_lockfile(self, tmp_project):
        (tmp_project / "pyproject.toml").write_text('[project]\nname = "test"\n')
        (tmp_project / "pdm.lock").write_text("")
        with patch("shutil.which", side_effect=lambda x: "/usr/bin/pdm" if x == "pdm" else None):
            assert _detect_manager(tmp_project) == DependencyManager.PDM

    def test_pipenv_by_pipfile(self, tmp_project):
        (tmp_project / "Pipfile").write_text("")
        with patch("shutil.which", side_effect=lambda x: "/usr/bin/pipenv" if x == "pipenv" else None):
            assert _detect_manager(tmp_project) == DependencyManager.PIPENV

    def test_pip_fallback(self, tmp_project):
        (tmp_project / "requirements.txt").write_text("requests\n")
        with patch("shutil.which", return_value=None):
            assert _detect_manager(tmp_project) == DependencyManager.PIP

    def test_pip_when_no_config(self, tmp_project):
        assert _detect_manager(tmp_project) == DependencyManager.PIP


class TestExtractFromPyproject:
    def test_basic(self, tmp_project):
        (tmp_project / "pyproject.toml").write_text(
            '[project]\nname = "myapp"\nversion = "1.2.3"\n'
            'requires-python = ">=3.11"\n'
            'dependencies = ["requests>=2.0", "click"]\n'
        )
        info = _extract_from_pyproject(tmp_project)
        assert info is not None
        assert info.name == "myapp"
        assert info.version == "1.2.3"
        assert info.python_requires == ">=3.11"
        assert info.dependencies == ["requests>=2.0", "click"]

    def test_with_extras(self, tmp_project):
        (tmp_project / "pyproject.toml").write_text(
            '[project]\nname = "myapp"\nversion = "1.0.0"\n'
            '[project.optional-dependencies]\n'
            'dev = ["pytest", "black"]\n'
        )
        info = _extract_from_pyproject(tmp_project)
        assert info is not None
        assert "dev" in info.extras
        assert info.extras["dev"] == ["pytest", "black"]

    def test_no_name_returns_none(self, tmp_project):
        (tmp_project / "pyproject.toml").write_text("[project]\n")
        assert _extract_from_pyproject(tmp_project) is None

    def test_no_version_defaults(self, tmp_project):
        (tmp_project / "pyproject.toml").write_text('[project]\nname = "myapp"\n')
        info = _extract_from_pyproject(tmp_project)
        assert info is not None
        assert info.version == "0.0.0"

    def test_no_file_returns_none(self, tmp_project):
        assert _extract_from_pyproject(tmp_project) is None


class TestExtractFromSetupCfg:
    def test_basic(self, tmp_project):
        (tmp_project / "setup.cfg").write_text(
            "[metadata]\nname = myapp\nversion = 2.0.0\n"
            "[options]\npython_requires = >=3.11\n"
            "install_requires =\n    requests>=2.0\n    click\n"
        )
        info = _extract_from_setup_cfg(tmp_project)
        assert info is not None
        assert info.name == "myapp"
        assert info.version == "2.0.0"
        assert info.python_requires == ">=3.11"
        assert info.dependencies == ["requests>=2.0", "click"]

    def test_with_extras(self, tmp_project):
        (tmp_project / "setup.cfg").write_text(
            "[metadata]\nname = myapp\nversion = 1.0.0\n"
            "[options.extras_require]\ndev =\n    pytest\n    black\n"
        )
        info = _extract_from_setup_cfg(tmp_project)
        assert info is not None
        assert "dev" in info.extras

    def test_no_metadata_section(self, tmp_project):
        (tmp_project / "setup.cfg").write_text("[options]\n")
        assert _extract_from_setup_cfg(tmp_project) is None

    def test_no_name_returns_none(self, tmp_project):
        (tmp_project / "setup.cfg").write_text(
            "[metadata]\nversion = 1.0.0\n"
        )
        assert _extract_from_setup_cfg(tmp_project) is None

    def test_no_file(self, tmp_project):
        assert _extract_from_setup_cfg(tmp_project) is None


class TestExtractFromRequirementsTxt:
    def test_basic(self, tmp_project):
        (tmp_project / "requirements.txt").write_text(
            "requests>=2.0\nclick\n# comment\n\n-e .\n"
        )
        info = _extract_from_requirements_txt(tmp_project)
        assert info is not None
        assert info.dependencies == ["requests>=2.0", "click"]
        assert info.name == tmp_project.name

    def test_no_file(self, tmp_project):
        assert _extract_from_requirements_txt(tmp_project) is None


class TestExtractFromPipfileLock:
    def test_basic(self, tmp_project):
        lock_data = {
            "default": {
                "requests": {"version": "==2.31.0"},
                "click": {"version": "==8.0.0"},
            }
        }
        (tmp_project / "Pipfile.lock").write_text(json.dumps(lock_data))
        info = _extract_from_pipfile_lock(tmp_project)
        assert info is not None
        assert "requests==2.31.0" in info.dependencies
        assert "click==8.0.0" in info.dependencies

    def test_package_without_version(self, tmp_project):
        lock_data = {
            "default": {
                "somepkg": {},
            }
        }
        (tmp_project / "Pipfile.lock").write_text(json.dumps(lock_data))
        info = _extract_from_pipfile_lock(tmp_project)
        assert info is not None
        assert "somepkg" in info.dependencies

    def test_no_file(self, tmp_project):
        assert _extract_from_pipfile_lock(tmp_project) is None


class TestDetectProject:
    def test_pyproject(self, tmp_project):
        (tmp_project / "pyproject.toml").write_text(
            '[project]\nname = "myapp"\nversion = "1.0.0"\n'
            'dependencies = ["requests"]\n'
        )
        with patch("shutil.which", return_value=None):
            info = detect_project(tmp_project)
        assert info.name == "myapp"
        assert info.manager == DependencyManager.PIP

    def test_nonexistent_path(self):
        with pytest.raises(FileNotFoundError):
            detect_project(Path("/nonexistent/path"))

    def test_not_a_directory(self, tmp_project):
        f = tmp_project / "file.txt"
        f.write_text("")
        with pytest.raises(ValueError, match="not a directory"):
            detect_project(f)

    def test_no_config(self, tmp_project):
        with pytest.raises(ValueError, match="Could not detect"):
            detect_project(tmp_project)

    def test_uv_project(self, tmp_project):
        (tmp_project / "pyproject.toml").write_text(
            '[project]\nname = "myapp"\nversion = "1.0.0"\n'
            '[tool.uv]\n'
        )
        with patch("shutil.which", side_effect=lambda x: "/usr/bin/uv" if x == "uv" else None):
            info = detect_project(tmp_project)
        assert info.manager == DependencyManager.UV

    def test_requirements_txt_fallback(self, tmp_project):
        (tmp_project / "requirements.txt").write_text("requests>=2.0\n")
        with patch("shutil.which", return_value=None):
            info = detect_project(tmp_project)
        assert info.manager == DependencyManager.PIP
        assert info.dependencies == ["requests>=2.0"]
