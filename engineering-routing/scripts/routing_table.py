#!/usr/bin/env python3
"""Read the routing-table registry and answer route/skip per skill.

The registry is pure data in
``engineering-routing/references/routing-table.md`` (ADR 0006 Decision 1:
never engine code). This module is its only consumer: it parses the table,
lists the skills routing may dispatch to, and answers route-or-skip for a
single skill name. A `registered` row is not routable — routing must skip
it. Anything malformed fails closed: routing stops instead of guessing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TABLE_PATH = ROOT / "engineering-routing" / "references" / "routing-table.md"

HEADER = "| skill | state | group | entry | uses |"
SEPARATOR = "|---|---|---|---|---|"
STATES = ("registered", "enabled")
GROUPS = ("office", "hardware", "research", "process")
DEFAULT_USES = "engineering-routing"


class RoutingTableError(ValueError):
    """Raised when the routing table is malformed or a skill is unknown."""


@dataclass(frozen=True)
class Row:
    """One parsed registry row.

    Attributes:
        skill: The skill's source-marker name (equals its directory name).
        state: ``registered`` or ``enabled``.
        group: The task-type group, or ``None`` for a registered row.
        entry: The spec contains-node path of the skill.
        uses: The owning skill, or ``None`` for a registered row.
    """

    skill: str
    state: str
    group: str | None
    entry: str
    uses: str | None


def _validate(row: Row) -> None:
    """Reject any row that violates the registry contract.

    Args:
        row: Parsed row to check.

    Raises:
        RoutingTableError: On an unknown state, a group/uses that does not
            match the state, or an entry carrying a path separator.
    """
    if row.state not in STATES:
        raise RoutingTableError(f"unknown state {row.state!r} for skill {row.skill!r}")
    if row.entry != os.path.basename(row.entry) or row.entry.startswith("."):
        raise RoutingTableError(f"entry {row.entry!r} must be a contains-node path")
    if row.state == "enabled":
        if row.group not in GROUPS:
            raise RoutingTableError(
                f"unknown group {row.group!r} for skill {row.skill!r}"
            )
        if row.uses != DEFAULT_USES:
            raise RoutingTableError(f"uses {row.uses!r} must be {DEFAULT_USES!r}")
    elif row.group is not None or row.uses is not None:
        raise RoutingTableError(
            f"registered row {row.skill!r} must set group and uses to —"
        )


def _parse_row(line: str, number: int) -> Row:
    """Parse one Markdown table row into a validated registry row.

    Args:
        line: Raw table row, pipes included.
        number: One-based line number, for error messages.

    Returns:
        The validated row.

    Raises:
        RoutingTableError: On a wrong column count or a contract violation.
    """
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    if len(cells) != 5:
        raise RoutingTableError(
            f"routing-table.md line {number}: expected 5 columns, got {len(cells)}"
        )
    skill, state, group, entry, uses = cells
    row = Row(
        skill=skill,
        state=state,
        group=None if group == "—" else group,
        entry=entry,
        uses=None if uses == "—" else uses,
    )
    try:
        _validate(row)
    except RoutingTableError as error:
        raise RoutingTableError(f"routing-table.md line {number}: {error}") from None
    return row


def load_table(path: str | os.PathLike[str] | None = None) -> tuple[Row, ...]:
    """Load and validate the routing table from a Markdown file.

    Args:
        path: Markdown table path; defaults to the repository's
            ``engineering-routing/references/routing-table.md``.

    Returns:
        Rows in file order.

    Raises:
        RoutingTableError: When the file is missing, has no header, carries
            a malformed row, or lists a duplicate skill name.
    """
    table_path = TABLE_PATH if path is None else Path(path)
    try:
        text = table_path.read_text(encoding="utf-8")
    except OSError as error:
        raise RoutingTableError(f"routing table unreadable: {table_path}") from error
    rows: list[Row] = []
    seen: set[str] = set()
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if stripped == HEADER or stripped == SEPARATOR:
            continue
        row = _parse_row(stripped, number)
        if row.skill in seen:
            raise RoutingTableError(
                f"routing-table.md line {number}: duplicate skill {row.skill!r}"
            )
        seen.add(row.skill)
        rows.append(row)
    return tuple(rows)


def routable_skills(rows: tuple[Row, ...] | None = None) -> tuple[str, ...]:
    """Return the skills routing may dispatch to.

    Args:
        rows: Parsed rows; loaded from the default table when omitted.

    Returns:
        Skill names whose state is ``enabled``, in table order.
    """
    if rows is None:
        rows = load_table()
    return tuple(row.skill for row in rows if row.state == "enabled")


def should_route(skill: str, rows: tuple[Row, ...] | None = None) -> bool:
    """Answer whether routing may dispatch to a skill.

    Args:
        skill: The skill's source-marker name.
        rows: Parsed rows; loaded from the default table when omitted.

    Returns:
        ``True`` when the row is ``enabled`` and so routable, ``False``
        when the row is ``registered`` and so must be skipped.

    Raises:
        RoutingTableError: When the skill has no table row.
    """
    if rows is None:
        rows = load_table()
    for row in rows:
        if row.skill == skill:
            return row.state == "enabled"
    raise RoutingTableError(f"unknown skill {skill!r}: no routing-table row")


if __name__ == "__main__":
    for name in routable_skills():
        print(name)
