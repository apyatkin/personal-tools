from click.testing import CliRunner

from hat.cli import main


def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "2.0.0" in result.output


def test_status_no_context():
    runner = CliRunner()
    result = runner.invoke(main, ["status"])
    assert result.exit_code == 0
    assert "No active context" in result.output
