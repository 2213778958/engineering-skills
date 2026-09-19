#!/usr/bin/env python3
from render_graph import ISSUE_RE, body_refs, issue_scan_text, mermaid

MERMAID = """
<!-- engineering:graph -->
```mermaid
classDef closed fill:#8256d0,color:#FFFFFF,stroke-width:0px;
i15["#15 三关通关可玩包"]:::open
i8256["#8256 ghost"]:::closed
```
<!-- /engineering:graph -->
"""


def main() -> int:
    prose = "Part of #2. See #15."
    assert ISSUE_RE.findall(issue_scan_text("fill:#8256d0,color:#FFFFFF")) == []
    assert 8256 not in body_refs(MERMAID + prose, spec=2)
    assert body_refs(MERMAID + prose, spec=2) == [15]
    assert body_refs("Blocked by: #8 #9\n" + MERMAID, spec=2) == [8, 9]
    drawn = mermaid(
        {15: {"title": "x", "state": "open", "url": "", "_blocked_by": []}}
    )
    assert drawn.startswith("flowchart TD")
    assert not drawn.startswith("---")
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
