from pathlib import Path

import yggame


def test_next_release_metadata_and_prompt_pack_are_present() -> None:
    root = Path(__file__).resolve().parents[1]
    assert yggame.__version__ == "0.3.0"
    assert yggame.__author__ == "Yashraj Sachin Ghemud"
    prompt_pack = root / "docs" / "PRODUCTION_PROMPT_PACK.md"
    assert prompt_pack.is_file()
    assert "100% Production-Grade Project Prompt Pack" in prompt_pack.read_text(encoding="utf-8")
