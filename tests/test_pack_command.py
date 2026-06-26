"""Tests for pack subcommand."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from depotpy.commands.pack import run_pack


def _make_args(**kwargs):
    defaults = {
        "project_path": "/some/project",
        "output": ".",
        "platforms": None,
        "python_version": None,
        "exclude": [],
        "include_extras": [],
        "prefer": "wheel",
    }
    defaults.update(kwargs)
    return type("Args", (), defaults)()


class TestRunPack:
    @patch("depotpy.commands.pack.PackBuilder")
    def test_success(self, mock_builder_cls, tmp_path, capsys):
        mock_builder = MagicMock()
        mock_builder.build.return_value = tmp_path / "myapp-1.0.0-offline.tar.gz"
        mock_builder_cls.return_value = mock_builder

        args = _make_args(project_path=str(tmp_path))
        result = run_pack(args)
        assert result == 0

        output = capsys.readouterr().out
        assert "Bundle created" in output

    @patch("depotpy.commands.pack.PackBuilder")
    def test_file_not_found(self, mock_builder_cls, capsys):
        mock_builder = MagicMock()
        mock_builder.build.side_effect = FileNotFoundError("not found")
        mock_builder_cls.return_value = mock_builder

        args = _make_args()
        result = run_pack(args)
        assert result == 1

        err = capsys.readouterr().err
        assert "not found" in err

    @patch("depotpy.commands.pack.PackBuilder")
    def test_value_error(self, mock_builder_cls, capsys):
        mock_builder = MagicMock()
        mock_builder.build.side_effect = ValueError("bad config")
        mock_builder_cls.return_value = mock_builder

        args = _make_args()
        result = run_pack(args)
        assert result == 1

        err = capsys.readouterr().err
        assert "bad config" in err

    @patch("depotpy.commands.pack.PackBuilder")
    def test_runtime_error(self, mock_builder_cls, capsys):
        mock_builder = MagicMock()
        mock_builder.build.side_effect = RuntimeError("download failed")
        mock_builder_cls.return_value = mock_builder

        args = _make_args()
        result = run_pack(args)
        assert result == 1

        err = capsys.readouterr().err
        assert "download failed" in err

    @patch("depotpy.commands.pack.PackBuilder")
    def test_passes_options(self, mock_builder_cls, tmp_path):
        mock_builder = MagicMock()
        mock_builder.build.return_value = tmp_path / "out.tar.gz"
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
