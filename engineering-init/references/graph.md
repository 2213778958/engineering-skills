# Graph (flow mermaid)

Draw the **flow** graph from GitHub `blockedBy`/`blocking` only. contains / uses: [architecture.md](architecture.md).

```
python <this-skill>/scripts/render_graph.py --issue <spec>
python <this-skill>/scripts/render_graph.py --issue <spec> --write
python <this-skill>/scripts/render_graph.py --issue <spec> --write --force
python <this-skill>/scripts/render_graph.py --issue <spec> --strict-one-one
```

`--issue` = spec number. If spec is only a container, do not draw it on this graph.

`--write` changes `engineering:graph` only. Title: `Graph（流程）` as the markdown heading inside the marker. Do not write mermaid `---` / `title:` frontmatter. Migrate as-is with no tickets uses spec `engineering:graph-asis`, heading `Graph（现有依赖序）`; do not use this script for that. Collecting tickets does not parse an existing `engineering:graph` block. Six-digit hex colors (`#8256d0`) are not issue numbers.

Multi source/sink allowed by default; not 1-source-1-sink only warns on stderr and still `--write`. `--strict-one-one` makes non-1-1 exit 2; then `--write` needs `--force`. Do not add `Start`/`Finish`. A second flow graph uses `--force` to overwrite.
