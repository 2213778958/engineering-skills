# Sources

Where answers may come from, what counts as a source, and how to cite it. A claim with no source is not delivered.

## Search order

1. Repo: repo library, `AGENTS.md`, `CONTEXT.md`, `docs/`, then code. Collect file paths + line numbers as you go.
2. Local/vendored: vendored docs, dependency docs already in the tree, local datasheets and PDFs. Record the path like a repo source.
3. Web — only when the repo is exhausted. Primary sources first (official docs, standards, changelogs, release notes); secondary sources (blog posts, articles, summaries) only to locate primaries. Record URL + access date.

## What counts as a source

| Source | Counts when | Recorded as |
|---|---|---|
| Repo file | The claim is backed by the cited lines | `path:L42` |
| Web page | The claim is backed by the page content | `<url> (read <YYYY-MM-DD>)` |
| Skill reference | The claim restates a rule in a skill | `<skill>/references/<file>` |

- A claim with no source is not sourced: delete the claim or move it to Open questions.
- An unquotable claim (you cannot point at lines, a URL, or a file) is not sourced — delete it or move it to Open questions.
- Paraphrase is fine; the citation is not optional.

## Citation format

Cite inline, next to the claim:

| Kind | Format |
|---|---|
| Repo file | `path:L42` |
| Web page | `<url> (read <YYYY-MM-DD>)` |
| Skill reference | `<skill>/references/<file>` |

## Do not paste source bodies

Do not copy source bodies into reports. Cite or link them; the reader goes to the source for the full text.
