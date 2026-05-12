from __future__ import annotations

from memory_reconciler.parser import parse_memory_entries


def test_parser_preserves_bullet_line_numbers(tmp_path):
    memory_file = tmp_path / "USER.md"
    memory_file.write_text(
        "# USER\n\n- first preference\n- second preference\n\nPlain paragraph memory.\n",
        encoding="utf-8",
    )

    entries = parse_memory_entries("user", memory_file, memory_file.read_text(encoding="utf-8"))

    assert [entry.start_line for entry in entries] == [3, 4, 6]
    assert [entry.end_line for entry in entries] == [3, 4, 6]
    assert entries[0].text == "first preference"
    assert entries[2].text == "Plain paragraph memory."
