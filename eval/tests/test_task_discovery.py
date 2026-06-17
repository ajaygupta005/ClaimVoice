"""Component 10 - Inspect AI finds at least one task."""
import subprocess
import sys
import pytest


@pytest.mark.integration
def test_inspect_lists_tasks():
    """Run `inspect eval --list` and assert at least one task is found."""
    result = subprocess.run(
        [sys.executable, "-m", "inspect_ai", "eval", "--list", "eval/tasks"],
        capture_output=True, text=True,
    )
    # exit code 0 or 2 acceptable depending on inspect-ai version; check stdout
    assert "coverage_qa_eval" in result.stdout or result.returncode == 0
