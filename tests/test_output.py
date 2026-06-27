"""Tests for output utilities."""

import json
import logging

from depotpy.output import error_json, print_error, print_json, print_text, setup_logging


class TestSetupLogging:
    def test_default_level(self):
        setup_logging(0)
        assert logging.getLogger().level == logging.INFO

    def test_verbose_level(self):
        setup_logging(1)
        assert logging.getLogger().level == logging.DEBUG

    def test_quiet_level(self):
        setup_logging(-1)
        assert logging.getLogger().level == logging.WARNING


class TestPrintJson:
    def test_outputs_to_stdout(self, capsys):
        print_json({"key": "value"})
        data = json.loads(capsys.readouterr().out)
        assert data == {"key": "value"}


class TestPrintText:
    def test_outputs_to_stderr(self, capsys):
        print_text("hello")
        assert "hello" in capsys.readouterr().err


class TestPrintError:
    def test_outputs_to_stderr(self, capsys):
        print_error("bad thing")
        err = capsys.readouterr().err
        assert "Error: bad thing" in err


class TestErrorJson:
    def test_outputs_to_stdout(self, capsys):
        error_json("something broke")
        data = json.loads(capsys.readouterr().out)
        assert data["success"] is False
        assert data["error"] == "something broke"
