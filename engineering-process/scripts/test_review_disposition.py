"""Behavioral contract tests for review disposition transitions."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")
TEMPLATES = (ROOT / "references" / "templates.md").read_text(encoding="utf-8")
ROW = re.compile(
    r"^\| `(?P<state>[^`]+)` \| `(?P<event>[^`]+)` \| "
    r"`(?P<next>[^`]+)` \| `(?P<scope>[^`]+)` \| `(?P<preserve>[^`]+)` \|$"
)


def load_transitions() -> dict[tuple[str, str], tuple[str, str, str]]:
    transitions = {}
    for line in TEMPLATES.splitlines():
        match = ROW.match(line)
        if not match:
            continue
        key = (match["state"], match["event"])
        if key in transitions:
            raise AssertionError(f"duplicate transition: {key}")
        transitions[key] = (match["next"], match["scope"], match["preserve"])
    return transitions


class ReviewFlow:
    def __init__(self) -> None:
        self.transitions = load_transitions()

    def step(self, state: str, event: str) -> tuple[str, str, str]:
        transition = self.transitions.get((state, event))
        if transition is None:
            transition = self.transitions.get(("*", event))
        if transition is None:
            raise ValueError(f"invalid transition: {state} + {event}")
        return transition

    def walk(self, *events: str) -> tuple[str, list[str], list[str]]:
        state = "implementation"
        scopes = []
        preservation = []
        for event in events:
            state, scope, preserve = self.step(state, event)
            scopes.append(scope)
            preservation.append(preserve)
        return state, scopes, preservation


class ReviewDispositionScenarioTest(unittest.TestCase):
    """Exercise all seven acceptance scenarios from issue 29."""

    def setUp(self) -> None:
        self.flow = ReviewFlow()

    def test_all_accepted_reworks_then_reviews_before_verify(self) -> None:
        state, scopes, _ = self.flow.walk(
            "blocking-review-fail", "accept-all", "rework-complete", "review-pass"
        )
        self.assertEqual("verify", state)
        self.assertNotIn("arbitration", scopes)
        with self.assertRaises(ValueError):
            self.flow.step("focused-rework", "review-pass")

    def test_partial_arbitrates_disputed_findings_only(self) -> None:
        state, scopes, _ = self.flow.walk("blocking-review-fail", "partial")
        self.assertEqual("arbitration", state)
        self.assertEqual("disputed-only", scopes[-1])
        self.assertNotEqual("all-findings", scopes[-1])

    def test_full_dispute_enters_disputed_only_arbitration(self) -> None:
        state, scopes, _ = self.flow.walk("blocking-review-fail", "dispute-all")
        self.assertEqual("arbitration", state)
        self.assertEqual("disputed-only", scopes[-1])
        with self.assertRaises(ValueError):
            self.flow.step("disposition", "review-pass")

    def test_explicit_challenge_enters_direct_arbitration(self) -> None:
        event = "explicit-contract-upstream-or-user-challenge"
        for state in ("implementation", "disposition", "fresh-review"):
            next_state, scope, _ = self.flow.step(state, event)
            self.assertEqual(("arbitration", "challenged-only"), (next_state, scope))

    def test_repeated_disagreement_is_reachable_and_bounded(self) -> None:
        state, scopes, _ = self.flow.walk(
            "blocking-review-fail",
            "accept-all",
            "rework-complete",
            "same-finding-blocking-fail",
            "dispute-repeated",
        )
        self.assertEqual("arbitration", state)
        self.assertEqual("repeated-disputed-only", scopes[-1])
        with self.assertRaises(ValueError):
            self.flow.step("post-rework-disposition", "accept-all")

    def test_repeated_partial_arbitrates_only_disputed_ids_once(self) -> None:
        accepted_ids = {"RVW-ACCEPTED"}
        disputed_ids = {"RVW-DISPUTED"}
        state, scope, preserve = self.flow.step("post-rework-disposition", "partial")
        arbitrated_ids = disputed_ids if scope == "repeated-disputed-only" else (
            accepted_ids | disputed_ids
        )
        self.assertEqual("arbitration", state)
        self.assertEqual(disputed_ids, arbitrated_ids)
        self.assertTrue(accepted_ids.isdisjoint(arbitrated_ids))
        self.assertEqual("prior-work+accepted-fixes", preserve)
        self.assertFalse(
            any(
                current == "post-rework-disposition" and next_state == "focused-rework"
                for (current, _), (next_state, _, _) in self.flow.transitions.items()
            )
        )
        for item in (
            "existing commits",
            "current context",
            "valid receipts",
            "unrelated completed work",
        ):
            self.assertIn(item, TEMPLATES)

    def test_blocking_review_cannot_skip_to_verify(self) -> None:
        state, _, _ = self.flow.walk("blocking-review-fail")
        self.assertEqual("disposition", state)
        with self.assertRaises(ValueError):
            self.flow.step(state, "review-pass")
        self.assertEqual("verify", self.flow.step("implementation", "review-pass")[0])

    def test_every_path_preserves_prior_work_and_accepted_fixes(self) -> None:
        for transition in self.flow.transitions.values():
            self.assertIn("prior-work", transition[2])
        _, _, preservation = self.flow.walk(
            "blocking-review-fail",
            "accept-all",
            "rework-complete",
            "same-finding-blocking-fail",
            "dispute-repeated",
        )
        self.assertEqual("prior-work+accepted-fixes", preservation[-1])
        for item in (
            "existing commits",
            "current context",
            "valid receipts",
            "unrelated completed work",
        ):
            self.assertIn(item, TEMPLATES)


class ReviewDispositionSchemaTest(unittest.TestCase):
    def test_structured_receipts_remain_required(self) -> None:
        for field in ("ID", "Category", "Evidence", "Required behavior"):
            self.assertIn(f"{field}:", TEMPLATES)
        self.assertRegex(
            TEMPLATES,
            re.compile(
                r"Review disposition: accept \| partial \| dispute\n"
                r"Accepted findings IDs: <stable finding IDs or none>\n"
                r"Disputed findings IDs: <stable finding IDs or none>\n"
                r"Reason: <contract/code evidence>\n"
                r"Action: rework \| arbitration"
            ),
        )

    def test_skill_delegates_to_the_canonical_flow(self) -> None:
        self.assertIn("templates.md **Review disposition**", SKILL)
        self.assertNotIn("Review disposition: accept | partial | dispute", SKILL)



if __name__ == "__main__":
    unittest.main()
