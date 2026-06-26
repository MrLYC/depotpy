"""Tests for CLI entry point."""

from unittest.mock import patch

import pytest

from depotpy.cli import create_parser, main


class TestCreateParser:
    def test_parser_creation(self):
        parser = create_parser()
        assert parser.prog == "depotpy"

    def test_version_flag(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "depotpy" in captured.out

    def test_no_command_shows_help(self, capsys):
        result = main([])
        assert result == 0

    def test_pack_subcommand_parsing(self):
        parser = create_parser()
        args = parser.parse_args(["pack", "/some/project"])
        assert args.command == "pack"
        assert args.project_path == "/some/project"
        assert args.output == "."
        assert args.platforms is None
        assert args.exclude == []
        assert args.include_extras == []
        assert args.prefer == "wheel"

    def test_pack_prefer_source(self):
        parser = create_parser()
        args = parser.parse_args(["pack", "/some/project", "--prefer", "source"])
        assert args.prefer == "source"

    def test_pack_with_options(self):
        parser = create_parser()
        args = parser.parse_args([
            "pack", "/some/project",
            "-o", "/output",
            "--platform", "manylinux2014_x86_64",
            "--platform", "macosx_11_0_arm64",
            "--python-version", "3.11",
            "--exclude", "pytest",
            "--include-extras", "dev",
        ])
        assert args.output == "/output"
        assert args.platforms == ["manylinux2014_x86_64", "macosx_11_0_arm64"]
        assert args.python_version == "3.11"
        assert args.exclude == ["pytest"]
        assert args.include_extras == ["dev"]

    def test_inspect_subcommand_parsing(self):
        parser = create_parser()
        args = parser.parse_args(["inspect", "/some/bundle.tar.gz"])
        assert args.command == "inspect"
        assert args.bundle_path == "/some/bundle.tar.gz"

    def test_install_subcommand_parsing(self):
        parser = create_parser()
        args = parser.parse_args(["install", "/some/bundle.tar.gz"])
        assert args.command == "install"
        assert args.bundle_path == "/some/bundle.tar.gz"

    def test_install_with_target(self):
        parser = create_parser()
        args = parser.parse_args(["install", "/some/bundle.tar.gz", "--target", "/install/dir"])
        assert args.target == "/install/dir"

    def test_install_default_on_conflict(self):
        parser = create_parser()
        args = parser.parse_args(["install", "/some/bundle.tar.gz"])
        assert args.on_conflict == "keep"

    def test_install_on_conflict_overwrite(self):
        parser = create_parser()
        args = parser.parse_args(["install", "/some/bundle.tar.gz", "--on-conflict", "overwrite"])
        assert args.on_conflict == "overwrite"

    def test_install_on_conflict_error(self):
        parser = create_parser()
        args = parser.parse_args(["install", "/some/bundle.tar.gz", "--on-conflict", "error"])
        assert args.on_conflict == "error"


class TestMainDispatch:
    @patch("depotpy.commands.pack.run_pack", return_value=0)
    def test_dispatch_pack(self, mock_run):
        result = main(["pack", "/some/project"])
        assert result == 0
        mock_run.assert_called_once()

    @patch("depotpy.commands.inspect.run_inspect", return_value=0)
    def test_dispatch_inspect(self, mock_run):
        result = main(["inspect", "/some/bundle.tar.gz"])
        assert result == 0
        mock_run.assert_called_once()

    @patch("depotpy.commands.install.run_install", return_value=0)
    def test_dispatch_install(self, mock_run):
        result = main(["install", "/some/bundle.tar.gz"])
        assert result == 0
        mock_run.assert_called_once()

    @patch("depotpy.commands.pack.run_pack", return_value=1)
    def test_dispatch_returns_error_code(self, mock_run):
        result = main(["pack", "/some/project"])
        assert result == 1
