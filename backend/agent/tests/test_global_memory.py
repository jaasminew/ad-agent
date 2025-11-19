"""Tests for global memory formatting utilities."""

from storyboard_gen_agent.utils import (
    format_global_memory_notes,
    build_global_memory_with_uploaded_urls,
)


def test_format_global_memory_notes_empty():
    assert format_global_memory_notes([]) == "(none)"


def test_format_global_memory_notes_lists_entries():
    notes = [
        ["https://example.com/final.png"],
        [
            "Shot 1",
            "Emi wears a linen jumpsuit with copper accessories",
            "Illustrative realism",
            "#FEE3B5, #C47C4E",
            "Camera pushes in as Emi lifts the product toward the light",
        ],
    ]
    formatted = format_global_memory_notes(notes)
    assert "- Shot 1" in formatted
    assert "Main character: Emi wears a linen jumpsuit with copper accessories" in formatted
    assert "Style: Illustrative realism" in formatted
    assert "Palette: #FEE3B5, #C47C4E" in formatted
    assert "Description: Camera pushes in" in formatted


def test_build_global_memory_with_uploaded_urls_inserts_note_first():
    base_memory = [
        [
            "Shot 1",
            "Emi wears a linen jumpsuit with copper accessories",
            "Illustrative realism",
            "#FEE3B5, #C47C4E",
            "Camera pushes in as Emi lifts the product toward the light",
        ]
    ]
    urls = ["https://example.com/final.png", "https://example.com/alt.png"]
    combined = build_global_memory_with_uploaded_urls(base_memory, urls)

    assert combined[0] == urls
    assert combined[1:] == base_memory


def test_build_global_memory_with_uploaded_urls_formats_empty_list():
    combined = build_global_memory_with_uploaded_urls([], [])
    assert combined[0] == []
    formatted = format_global_memory_notes(combined)
    assert formatted.splitlines()[0] == "- Uploaded final URLs: (none)"

