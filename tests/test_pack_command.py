"""Tests for pack subcommand."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from depotpy.commands.pack import run_pack
from depotpy.models import Manifest, PackageFile


def _make_args(**kwargs):
    defaults = {
        "project_path": "/some/project",
        "output": ".",
        "platforms": None,
        "python_version": None,
        "exclude": [],
        "include_extras": [],
        "prefer": "wheel",
        "json_output": False,
    }
    defaults.update(kwargs)
    return type("Args", (), defaults)()


def _mock_manifest():
    return Manifest(
        project_name="myapp",
        project_version="1.0.0",
        python_version="3.11",
        platforms=["manylinux2014_x86_64"],
        packages=[PackageFile("requests-2.31.0-py3-none-any.whl", "requests", "2.31.0", "abc", 100)],
    )


class TestRunPack:
    @patch("depotpy.commands.pack.PackBuilder")
    def test_success(self, mock_builder_cls, tmp_path, capsys):
        mock_builder = MagicMock()
        mock_builder.build.return_value = (tmp_path / "myapp-1.0.0-offline.tar.gz", _mock_manifest())
        mock_builder_cls.return_value = mock_builder

        args = _make_args(project_path=str(tmp_path))
        result = run_pack(args)
        assert result == 0

        captured = capsys.readouterr()
        assert "Bundle created" in captured.err

    @patch("depotpy.commands.pack.PackBuilder")
    def test_success_json(self, mock_builder_cls, tmp_path, capsys):
        mock_builder = MagicMock()
        mock_builder.build.return_value = (tmp_path / "myapp-1.0.0-offline.tar.gz", _mock_manifest())
        mock_builder_cls.return_value = mock_builder

        args = _make_args(project_path=str(tmp_path), json_output=True)
        result = run_pack(args)
        assert result == 0

        data = json.loads(capsys.readouterr().out)
        assert data["success"] is True
        assert data["project_name"] == "myapp"
        assert "bundle_path" in data

    @patch("depotpy.commands.pack.PackBuilder")
    def test_file_not_found(self, mock_builder_cls, capsys):
        mock_builder = MagicMock()
        mock_builder.build.side_effect = FileNotFoundError("not found")
        mock_builder_cls.return_value = mock_builder

        args = _make_args()
        result = run_pack(args)
        assert result == 1
        assert "not found" in capsys.readouterr().err

    @patch("depotpy.commands.pack.PackBuilder")
    def test_error_json(self, mock_builder_cls, capsys):
        mock_builder = MagicMock()
        mock_builder.build.side_effect = RuntimeError("download failed")
        mock_builder_cls.return_value = mock_builder

        args = _make_args(json_output=True)
        result = run_pack(args)
        assert result == 1

        data = json.loads(capsys.readouterr().out)
        assert data["success"] is False
        assert "download failed" in data["error"]

    @patch("depotpy.commands.pack.PackBuilder")
    def test_passes_options(self, mock_builder_cls, tmp_path):
        mock_builder = MagicMock()
        mock_builder.build.return_value = (tmp_path / "out.tar.gz", _mock_manifest())
        mock_builder_cls.return_value = mock_builder

        args = _make_args(
            project_path=str(tmp_path),
            output="/out",
            platforms=["manylinux2014_x86_64"],
            python_version="3.12",
            exclude=["pytest"],
            include_extras=["dev"],
        )
        run_pack(args)

        opts = mock_builder_cls.call_args[0][0]
        assert opts.project_path == Path(str(tmp_path))
        assert opts.output_dir == Path("/out")
        assert opts.platforms == ["manylinux2014_x86_64"]
        assert opts.python_version == "3.12"
        assert opts.exclude == ["pytest"]
        assert opts.include_extras == ["dev"]
