# List

Run:

```text
python <this-skill>/scripts/list_catalog.py
```

`spawnable_agent_profiles` can be passed as `agent_profile_id`. `llm_profiles_without_agent` require encrypted `agent_settings` plus that LLM through the environment skill; do not silently downgrade.

Resolve named targets by exact agent profile, exact LLM profile, then family plus effort. Live API is authoritative; do not cache ids, names, or efforts.
