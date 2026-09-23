#!/usr/bin/env python3
"""Gate engineering-init's routing points on the routing-table registry.

The registry is data — ``engineering-routing/references/routing-table.md``
read at runtime, never engine code (ADR 0006 Decision 1). This module is a
read-only consumer: engineering-init routes its calls through it like every
other routing caller, reusing the primitives in
``engineering-routing/scripts/routing_table.py`` by import.

Two states are distinguished: a ``registered`` row is not routable (a call
stops at the gate; enablement is a patch ticket), an ``enabled`` row is
routable. An unknown skill fails closed via ``RoutingTableError``.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TABLE_PATH = ROOT / "engineering-routing" / "references" / "routing-table.md"

sys.path.insert(0, str(ROOT / "engineering-routing" / "scripts"))

import routing_table  # noqa: E402


class RegistryGateError(RuntimeError):
    """Raised when a caller wants to route to a registered, non-routable skill."""


def _default_rows() -> tuple[routing_table.Row, ...]:
    """Load the registry from the default table path.

    Returns:
        The validated registry rows, in file order.
    """
    return routing_table.load_table(TABLE_PATH)


def _find_row(skill: str, table: tuple[routing_table.Row, ...]) -> routing_table.Row:
    """Return the registry row for one skill, failing closed when unknown.

    Args:
        skill: The skill's source-marker name.
        table: Parsed registry rows.

    Returns:
        The row matching ``skill``.

    Raises:
        routing_table.RoutingTableError: When the skill has no registry row;
            the unknown-name lookup is delegated to ``should_route``.
    """
    for row in table:
        if row.skill == skill:
            return row
    routing_table.should_route(skill, table)  # always raises for an unknown skill
    raise AssertionError  # pragma: no cover - unreachable after should_route


def rows() -> tuple[routing_table.Row, ...]:
    """Load the routing-table registry with this module's default path.

    Returns:
        The validated registry rows, in file order.

    Raises:
        routing_table.RoutingTableError: When the table is missing or malformed.
    """
    return _default_rows()


def registered_skills(
    rows: tuple[routing_table.Row, ...] | None = None,
) -> tuple[routing_table.Row, ...]:
    """Return the registry rows whose state is ``registered``.

    Args:
        rows: Parsed registry rows; loaded from the default table when omitted.

    Returns:
        The registered rows, in table order — the registration inventory.
    """
    table = _default_rows() if rows is None else rows
    return tuple(row for row in table if row.state == "registered")


def enabled_skills(
    rows: tuple[routing_table.Row, ...] | None = None,
) -> tuple[str, ...]:
    """Return the skill names routing may dispatch to.

    Args:
        rows: Parsed registry rows; loaded from the default table when omitted.

    Returns:
        Skill names whose state is ``enabled``, in table order.
    """
    return routing_table.routable_skills(rows)


def is_routable(skill: str, rows: tuple[routing_table.Row, ...] | None = None) -> bool:
    """Answer whether the registry allows routing to one skill.

    Args:
        skill: The skill's source-marker name.
        rows: Parsed registry rows; loaded from the default table when omitted.

    Returns:
        ``True`` when the row is ``enabled`` and so routable, ``False`` when
        the row is ``registered`` and so must be skipped.

    Raises:
        routing_table.RoutingTableError: When the skill has no registry row
            (fail closed — routing stops instead of guessing).
    """
    return routing_table.should_route(skill, rows)


def require_routable(
    skill: str, rows: tuple[routing_table.Row, ...] | None = None
) -> routing_table.Row:
    """Return the registry row for a skill routing may dispatch to.

    Args:
        skill: The skill's source-marker name.
        rows: Parsed registry rows; loaded from the default table when omitted.

    Returns:
        The row when its state is ``enabled``.

    Raises:
        RegistryGateError: When the row is ``registered`` — not routable;
            enablement is a patch ticket.
        routing_table.RoutingTableError: When the skill has no registry row.
    """
    table = _default_rows() if rows is None else rows
    row = _find_row(skill, table)
    if routing_table.should_route(skill, table):
        return row
    raise RegistryGateError(
        f"{skill} is registered, not enabled; enablement is a patch ticket"
        " (references/routing-table.md)"
    )


def require_entry(
    skill: str, rows: tuple[routing_table.Row, ...] | None = None
) -> Path:
    """Return the on-disk contains-node directory of one registry skill.

    Args:
        skill: The skill's source-marker name.
        rows: Parsed registry rows; loaded from the default table when omitted.

    Returns:
        The entry directory under the repository root.

    Raises:
        RegistryGateError: When the entry directory does not exist under ROOT.
        routing_table.RoutingTableError: When the skill has no registry row.
    """
    table = _default_rows() if rows is None else rows
    row = _find_row(skill, table)
    entry = ROOT / row.entry
    if not entry.is_dir():
        raise RegistryGateError(f"entry {row.entry!r} of {skill} is missing under ROOT")
    return entry


if __name__ == "__main__":
    for name in enabled_skills():
        print(name)
