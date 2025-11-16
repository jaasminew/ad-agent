"""Unit tests for the storyboard checklist utilities."""

from storyboard_gen_agent.checklist import (
    ChecklistItem,
    build_checklist,
    format_checklist_markdown,
    extract_checklist_statuses,
    find_checklist_gaps,
)


def test_build_checklist_first_beat_contains_palette_extract():
    first_items = build_checklist(is_first_beat=True)
    later_items = build_checklist(is_first_beat=False)

    assert any(item.slug == "palette_extract" for item in first_items)
    assert not any(item.slug == "palette_extract" for item in later_items)


def test_format_checklist_markdown_includes_slug_and_instructions():
    items = build_checklist(is_first_beat=False)
    markdown = format_checklist_markdown(items)

    assert "Checklist (print this before any tool call" in markdown
    assert "- [ ] palette_check" in markdown


def test_extract_statuses_prefers_latest_and_validates():
    notes = [
        "checklist: beat=1 | slug=palette_check | status=pending",
        "checklist: beat=1 | slug=palette_check | status=done",
        "checklist: beat=1 | slug=reference_search | status=pending",
        "checklist: beat=2 | slug=palette_check | status=done",
    ]

    statuses = extract_checklist_statuses(notes, beat_number=1)
    assert statuses["palette_check"] == "done"
    assert statuses["reference_search"] == "pending"

    items = build_checklist(is_first_beat=False)
    missing = find_checklist_gaps(statuses, items[:2])
    assert missing == ["reference_search"]


def test_optional_items_do_not_block_validation():
    optional_item = ChecklistItem(
        slug="attempt2_generation",
        label="Run Attempt 2",
        mandatory=False,
    )

    missing = find_checklist_gaps({}, [optional_item])
    assert missing == []

    missing = find_checklist_gaps({"attempt2_generation": "skipped"}, [optional_item])
    assert missing == []

