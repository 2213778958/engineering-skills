#!/usr/bin/env python3
"""Join Agent Canvas agent profiles with LLM profiles. Source of truth is the live API."""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = os.environ.get("OPENHANDS_URL", "http://localhost:8000").rstrip("/")
KEY_PATH = Path.home() / ".openhands" / "agent-canvas" / "api-key.txt"


def api(path: str) -> object:
    key = KEY_PATH.read_text(encoding="utf-8").strip()
    req = Request(
        f"{BASE}{path}",
        headers={"X-Session-API-Key": key, "X-Expose-Secrets": "encrypted"},
        method="GET",
    )
    with urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def effort_from_acp_model(model: str | None) -> str | None:
    if not model:
        return None
    for token in ("xhigh", "max", "high", "medium"):
        if model.endswith(token) or f"-{token}" in model:
            return token
    return None


def main() -> None:
    try:
        agents = api("/api/agent-profiles")
        llms = api("/api/profiles")
    except (HTTPError, URLError, FileNotFoundError) as exc:
        raise SystemExit(f"catalog fetch failed: {exc}") from exc

    llm_rows = []
    for item in (llms or {}).get("profiles") or []:
        name = item.get("name")
        cfg = {}
        try:
            cfg = (api(f"/api/profiles/{name}") or {}).get("config") or {}
        except HTTPError:
            pass
        llm_rows.append(
            {
                "name": name,
                "list_model": item.get("model"),
                "config_model": cfg.get("model"),
                "reasoning_effort": cfg.get("reasoning_effort"),
                "has_agent_profile": False,
            }
        )
    llm_by_name = {row["name"]: row for row in llm_rows}

    spawnable = []
    for item in (agents or {}).get("profiles") or []:
        name = item.get("name")
        detail = (api(f"/api/agent-profiles/{name}") or {}).get("profile") or item
        ref = detail.get("llm_profile_ref")
        llm = llm_by_name.get(ref) if ref else None
        if llm:
            llm["has_agent_profile"] = True
        kind = detail.get("agent_kind")
        acp_model = detail.get("acp_model")
        effort = (llm or {}).get("reasoning_effort") if llm else effort_from_acp_model(acp_model)
        spawnable.append(
            {
                "agent_profile_id": detail.get("id") or item.get("id"),
                "agent_profile_name": name,
                "agent_kind": kind,
                "runtime": "cursor-acp" if kind == "acp" else "openhands",
                "llm_profile": ref,
                "model": (llm or {}).get("config_model") or (llm or {}).get("list_model") or acp_model,
                "effort": effort,
                "spawn": "agent_profile_id",
            }
        )

    llm_only = [
        {
            "llm_profile": row["name"],
            "model": row.get("config_model") or row.get("list_model"),
            "effort": row.get("reasoning_effort"),
            "spawn": "agent_settings+llm",
        }
        for row in llm_rows
        if not row["has_agent_profile"]
    ]

    print(
        json.dumps(
            {
                "backend": BASE,
                "active_agent_profile_id": (agents or {}).get("active_agent_profile_id"),
                "active_llm_profile": (llms or {}).get("active_profile"),
                "spawnable_agent_profiles": spawnable,
                "llm_profiles_without_agent": llm_only,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
