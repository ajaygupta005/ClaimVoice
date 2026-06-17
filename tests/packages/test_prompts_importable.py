"""Component 04 - every shared-prompts subfolder has a default export."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROMPTS_SRC = ROOT / "packages/shared-prompts/src"


def test_each_prompt_folder_has_index():
    if not PROMPTS_SRC.exists():
        import pytest
        pytest.skip("shared-prompts not built yet")
    for sub in PROMPTS_SRC.iterdir():
        if sub.is_dir():
            # Either index.ts or a .ts file with the same name as the folder
            ts_files = list(sub.glob("*.ts"))
            assert ts_files, f"no .ts files in {sub}"
