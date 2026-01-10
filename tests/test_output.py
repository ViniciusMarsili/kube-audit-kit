"""Tests for output module."""
import output
from rich.console import Console


def test_info_output(capsys):
    """Test info output."""
    output.info("Test info message")
    captured = capsys.readouterr()
    assert "Test info message" in captured.out


def test_success_output(capsys):
    """Test success output."""
    output.success("Test success message")
    captured = capsys.readouterr()
    assert "Test success message" in captured.out


def test_warning_output(capsys):
    """Test warning output."""
    output.warning("Test warning message")
    captured = capsys.readouterr()
    assert "Test warning message" in captured.out


def test_error_output(capsys):
    """Test error output."""
    output.error("Test error message")
    captured = capsys.readouterr()
    assert "Test error message" in captured.out


def test_step_output(capsys):
    """Test step output."""
    output.step(1, 3, "Test step message")
    captured = capsys.readouterr()
    assert "[1/3]" in captured.out
    assert "Test step message" in captured.out


def test_console_exists():
    """Test that console object exists."""
    assert hasattr(output, "console")
    assert isinstance(output.console, Console)


def test_convenience_aliases():
    """Test that convenience aliases exist."""
    assert output.print_info == output.info
    assert output.print_success == output.success
    assert output.print_warning == output.warning
    assert output.print_error == output.error
    assert output.print_step == output.step
    assert output.print_header == output.header
