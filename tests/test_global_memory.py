"""Tests for global memory formatting utilities."""

from storyboard_gen_agent.utils import (
    format_global_memory_notes,
    build_global_memory_with_uploaded_urls,
)


def test_format_global_memory_notes_empty():
    assert format_global_memory_notes([]) == "(none)"


def test_format_global_memory_notes_lists_entries():
    notes = [
        "episode_palette: #FEE3B5, #C47C4E",
        "character: Emi wears a linen jumpsuit with copper accessories",
    ]
    formatted = format_global_memory_notes(notes)
    assert "- episode_palette: #FEE3B5, #C47C4E" in formatted
    assert "- character: Emi wears a linen jumpsuit with copper accessories" in formatted
    assert formatted.count("\n") == 1


def test_build_global_memory_with_uploaded_urls_inserts_note_first():
    base_memory = ["episode_palette: #FEE3B5, #C47C4E"]
    urls = ["https://example.com/final.png", "https://example.com/alt.png"]
    combined = build_global_memory_with_uploaded_urls(base_memory, urls)

    assert combined[0].startswith("uploaded_final_urls:")
    assert combined[1:] == base_memory


def test_build_global_memory_with_uploaded_urls_formats_empty_list():
    combined = build_global_memory_with_uploaded_urls([], [])
    assert combined[0] == 'uploaded_final_urls: []'
    formatted = format_global_memory_notes(combined)
    assert formatted.splitlines()[0] == "- uploaded_final_urls: []"

