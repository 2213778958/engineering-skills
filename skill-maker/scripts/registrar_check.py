#!/usr/bin/env python3
"""Registrar checklist for one registration patch ticket.

skill-maker executes registrations per
``engineering-routing/references/routing-table.md`` § Registration (ADR 0006
Decision 1 + Decision 3). A registration touches skill files, the spec
contains/uses entry, and one appended routing-table row — never engine code.
``validate_registration`` checks that checklist against one proposed row and
one changed-path list, and fails closed on malformed input: an offender list
is returned instead of a best-effort guess, so a broken registration stops
the patch rather than half-landing. A ``registered`` row is not routable;
enablement is a separate patch ticket and outside this checklist.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from collections.abc import Iterable
from pathlib import Path

TABLE_RELATIVE = "engineering-routing/references/routing-table.md"
ENGINEERING_SERIES = ("engineering-*", "*-sessions", "*-watch")
ROW_PATTERN = re.compile(r"^\|(?P<cells>.*)\|$")


def _frontmatter_name(skill_md: Path) -> str | None:
    """Return the frontmatter ``name:`` value of a SKILL.md, or None.

    Args:
        skill_md: Path to the candidate SKILL.md.

    Returns:
        The declared name, or ``None`` when the file is unreadable, has no
        frontmatter block, or declares no name.
    """
    try:
        text = skill_md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    frontmatter = re.match(
        r"^---[ \t]*\r?\n(?P<body>.*?)\r?\n---[ \t]*\r?\n?", text, re.DOTALL
    )
    if frontmatter is None:
        return None
    match = re.search(
        r"^name:\s*(?P<name>.+?)\s*$", frontmatter.group("body"), re.MULTILINE
    )
    return match["name"] if match else None


def _parse_row(line: str) -> dict[str, str]:
    """Parse one proposed routing-table row into its five cells.

    Args:
        line: Raw row text, pipes included.

    Returns:
        Mapping with the keys ``skill``, ``state``, ``group``, ``entry``,
        and ``uses``.

    Raises:
        ValueError: When the line is not a 5-column table row.
    """
    match = ROW_PATTERN.match(line.strip())
    if match is None:
        raise ValueError(f"row is not a Markdown table row: {line!r}")
    cells = [cell.strip() for cell in match.group("cells").split("|")]
    if len(cells) != 5:
        raise ValueError(f"row must have 5 columns, got {len(cells)}: {line!r}")
    return dict(zip(("skill", "state", "group", "entry", "uses"), cells))


def _is_engine_code(path: str) -> bool:
    """Answer whether a changed path counts as engine code.

    Args:
        path: Repo-relative POSIX path from the changed-path list.

    Returns:
        ``True`` when the top-level directory name matches an
        engineering-series glob (``engineering-*``, ``*-sessions``,
        ``*-watch``), except the table file itself, which is data and
        always allowed.
    """
    posix = path.replace("\\", "/")
    if posix == TABLE_RELATIVE:
        return False
    top = posix.split("/", maxsplit=1)[0]
    return any(fnmatch.fnmatchcase(top, pattern) for pattern in ENGINEERING_SERIES)


def validate_registration(
    root: Path,
    changed_paths: Iterable[str],
    table_path: Path,
    row_line: str,
) -> list[str]:
    """Validate one registration patch against the registrar checklist.

    Args:
        root: Repository root holding the skill directories.
        changed_paths: Repo-relative POSIX paths the patch touches. The list
            must include the table file itself; without it the row cannot
            have been appended, which fails closed.
        table_path: Routing-table Markdown file the row must be appended to.
        row_line: The proposed routing-table row, pipes included.

    Returns:
        Offender strings; an empty list means the registration passes.
        Malformed input yields offenders, never a guess.
    """
    offenders: list[str] = []
    posix_paths = {Path(path).as_posix() for path in changed_paths}
    try:
        row = _parse_row(row_line)
    except ValueError as error:
        offenders.append(f"row: {error}")
        return offenders

    name = row["skill"]
    skill_md = root / name / "SKILL.md"
    if not skill_md.is_file():
        offenders.append(f"files: {name}/SKILL.md missing under {root}")
    else:
        declared = _frontmatter_name(skill_md)
        if declared != name:
            offenders.append(f"files: {name}/SKILL.md name={declared!r} != {name!r}")

    if row["state"] != "registered":
        offenders.append(
            f"state: {row['state']!r} != 'registered'; "
            "enablement is a separate patch ticket"
        )
    if row["group"] not in ("", "—"):
        offenders.append(f"group: {row['group']!r} must be empty on a registered row")
    if row["uses"] not in ("", "—"):
        offenders.append(f"uses: {row['uses']!r} must be empty on a registered row")
    if row["entry"] != name or "/" in row["entry"] or "\\" in row["entry"]:
        offenders.append(
            f"entry: {row['entry']!r} must equal skill name {name!r} "
            "with no path separators"
        )

    for path in sorted(posix_paths):
        if _is_engine_code(path):
            offenders.append(
                f"engine code: {path} is inside an engineering-series directory"
            )

    if table_path.is_relative_to(root):
        table_relative = table_path.relative_to(root).as_posix()
    else:
        table_relative = Path(table_path).as_posix()
    if table_relative not in posix_paths:
        offenders.append(
            f"changed_paths: {table_relative} missing; row cannot be appended"
        )

    try:
        text = table_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        offenders.append(f"table: unreadable {table_path}: {error}")
        return offenders
    if row_line.strip() not in {line.strip() for line in text.splitlines()}:
        offenders.append(f"table: row not appended in {table_path}")
    return offenders


def main() -> int:
    """Run the registrar checklist from command-line arguments.

    Returns:
        0 when the registration passes, 1 when any offender is found.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="skill name to register")
    parser.add_argument("--table", default=TABLE_RELATIVE, help="routing-table path")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    row_line = f"| {args.name} | registered | — | {args.name} | — |"
    table = Path(args.table)
    offenders = validate_registration(root, [table.as_posix()], table, row_line)
    for offender in offenders:
        print(offender, file=sys.stderr)
    return 1 if offenders else 0


if __name__ == "__main__":
    raise SystemExit(main())
