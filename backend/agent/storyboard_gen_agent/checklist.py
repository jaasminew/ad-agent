"""Checklist utilities for the storyboard generation agent."""

from dataclasses import dataclass
from typing import Dict, List

VALID_CHECKLIST_STATUSES = {"pending", "done", "skipped"}


@dataclass(frozen=True)
class ChecklistItem:
    """Single checklist entry defined by slug + human description."""

    slug: str
    label: str
    mandatory: bool = True

    def optional_hint(self) -> str:
        """Return a suffix hint when the item is optional."""
        return " (only if earlier attempts fail)" if not self.mandatory else ""


def build_checklist(is_first_beat: bool) -> List[ChecklistItem]:
    """Return ordered checklist items for the current beat."""

    items: List[ChecklistItem] = [
        ChecklistItem(
            "continuity_recall",
            "Recall the previous shot's continuity record (character + style + palette)",
            mandatory=False,
        ),
        ChecklistItem("reference_search", "List tags and pick the reference image"),
    ]

    if is_first_beat:
        items.append(
            ChecklistItem(
                "palette_extract",
                "Extract palette from the reference image and remember it",
            )
        )

    items.extend(
        [
            ChecklistItem(
                "attempt1_generation",
                "Run MidJourney Attempt 1 (generate + upscale) and store attempt notes",
            ),
            ChecklistItem(
                "attempt1_distortion",
                "Call check_image_distortion on Attempt 1 and log the result",
            ),
            ChecklistItem(
                "attempt2_generation",
                "Run MidJourney Attempt 2 if Attempt 1 fails, else mark skipped",
                mandatory=False,
            ),
            ChecklistItem(
                "attempt2_distortion",
                "Call distortion check for Attempt 2 if it was generated",
                mandatory=False,
            ),
            ChecklistItem(
                "attempt3_generation",
                "Run MidJourney Attempt 3 if the first two fail, else mark skipped",
                mandatory=False,
            ),
            ChecklistItem(
                "attempt3_distortion",
                "Call distortion check for Attempt 3 if it was generated",
                mandatory=False,
            ),
            ChecklistItem(
                "product_integration",
                "Use nanobanana_generate with the PASS storyboard to replace the product",
            ),
            ChecklistItem(
                "results_logging",
                "Store storyboard + final URLs, attempt metadata, and flags in memory",
            ),
            ChecklistItem(
                "checklist_qa",
                "Checklist QA: reprint statuses, confirm all mandatory slugs are DONE",
            ),
        ]
    )

    return items


def format_checklist_markdown(items: List[ChecklistItem]) -> str:
    """
    Build the markdown instructions the agent must echo inside Thoughts.
    """

    lines = [
        "Checklist (print this before any tool call and refresh it after each status change):",
        "- Always include the slug (e.g., `continuity_recall`) so controllers can parse progress.",
        "- Format each row as `- [ ] slug - description` and switch to `[x]` only after the task is DONE.",
        "- When a later step becomes unnecessary (e.g., Skip Attempt 2 after Attempt 1 passes), immediately mark it as `[x] slug - description (skipped – reason)` and log a `status=skipped` note.",
        "- Optional tasks must end in either DONE or SKIPPED with a justification; leaving them unchecked will fail validation.",
        "- After every update, store `remember(\"checklist: beat=<n> | slug=<slug> | status=<pending|done|skipped>\")`.",
        "- `results_logging` is only complete when every mandatory slug shows `[x] DONE`; if anything is still pending, loop back and fix it immediately.",
        "- During `checklist_qa`, print the full checklist again, explicitly call out missing items, and resolve them before Final Answer.",
        "",
    ]

    for item in items:
        lines.append(f"- [ ] {item.slug} - {item.label}{item.optional_hint()}")

    return "\n".join(lines)


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
    if status and status not in VALID_CHECKLIST_STATUSES:
        data["status"] = status.lower()

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


def find_checklist_gaps(statuses: Dict[str, str], items: List[ChecklistItem]) -> List[str]:
    """
    Return mandatory items that never reached DONE.

    Optional checklist entries are informational only and do not impact validation.
    """

    missing_mandatory: List[str] = []

    for item in items:
        if not item.mandatory:
            continue
        if statuses.get(item.slug) != "done":
            missing_mandatory.append(item.slug)

    return missing_mandatory


