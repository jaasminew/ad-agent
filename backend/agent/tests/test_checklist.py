"""Unit tests for the storyboard checklist utilities."""

from storyboard_gen_agent.checklist import extract_checklist_statuses, parse_checklist_note


def test_parse_checklist_note_handles_whitespace_and_unknown_fields():
    note = "checklist: beat=3 | slug=reference_search | status=Done | extra=ignore me"

    parsed = parse_checklist_note(note)
    assert parsed["beat"] == "3"
    assert parsed["slug"] == "reference_search"
    assert parsed["status"] == "done"
    assert parsed["extra"] == "ignore me"


def test_extract_statuses_prefers_latest_and_filters_invalid():
    notes = [
        "checklist: beat=1 | slug=plan | status=pending",
        "checklist: beat=1 | slug=plan | status=done",
        "checklist: beat=1 | slug=reference_search | status=PENDING",
        "checklist: beat=1 | slug=bad | status=unknown",
        "checklist: beat=2 | slug=plan | status=done",
    ]

    statuses = extract_checklist_statuses(notes, beat_number=1)

    assert statuses["plan"] == "done"
    assert statuses["reference_search"] == "pending"
    assert "bad" not in statuses
    statuses_beat2 = extract_checklist_statuses(notes, beat_number=2)
    assert statuses_beat2["plan"] == "done"