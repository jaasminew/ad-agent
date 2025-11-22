"""Checklist note parsing utilities."""

from typing import Dict, List

VALID_CHECKLIST_STATUSES = {"pending", "done", "skipped"}


def parse_checklist_note(note: str) -> Dict[str, str]:
    """Parse a checklist memory note into a dictionary."""

    if not note.startswith("checklist:"):
        return {}

    payload = note.split(":", 1)[1].strip()
    parts = [segment.strip() for segment in payload.split("|")]
    data: Dict[str, str] = {}

    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        data[key.strip()] = value.strip()

    status = data.get("status")
    if status:
        normalized = status.lower()
        if normalized in VALID_CHECKLIST_STATUSES:
            data["status"] = normalized
        else:
            data["status"] = normalized

    return data


def extract_checklist_statuses(notes: List[str], beat_number: int) -> Dict[str, str]:
    """
    Return the latest status for each slug recorded for a beat.
    """

    statuses: Dict[str, str] = {}
    for note in notes:
        parsed = parse_checklist_note(note)
        if not parsed:
            continue
        if str(parsed.get("beat")) != str(beat_number):
            continue

        slug = parsed.get("slug")
        status = parsed.get("status", "").lower()
        if not slug or status not in VALID_CHECKLIST_STATUSES:
            continue
        statuses[slug] = status

    return statuses


