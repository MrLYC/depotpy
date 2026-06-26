"""Tests for CLI entry point."""

import pytest

from pydepot.cli import create_parser, main


class TestCreateParser:
    def test_parser_creation(self):
        parser = create_parser()
        assert parser.prog == "pydepot"

    def test_version_flag(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "pydepot" in captured.out

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
