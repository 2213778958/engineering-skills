"""Contract tests for the engineering-process review disposition flow."""
from pathlib import Path
import re
import unittest
ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")
TEMPLATES = (ROOT / "references" / "templates.md").read_text(encoding="utf-8")
CONTRACT = f"{SKILL}\n{TEMPLATES}"
class ReviewDispositionContractTest(unittest.TestCase):
    """Verify the seven acceptance cases from issue 29."""
    def test_accept_reworks_then_fresh_review_then_verify(self) -> None:
        self.assertRegex(
            TEMPLATES,
            re.compile(
                r"`accept`.*?same implement employee.*?focused rework.*?"
                r"fresh review.*?review passes.*?staff verify",
                re.DOTALL,
            ),
        )
        self.assertRegex(TEMPLATES, r"`accept`[^\n]*do not arbitrate")
    def test_partial_arbitrates_only_disputed_findings(self) -> None:
        self.assertRegex(
            TEMPLATES,
            r"`partial`[^\n]*arbitrate only the disputed findings",
        )
        self.assertIn(
            "Accepted independent findings may be fixed without re-litigating them",
            TEMPLATES,
        )
    def test_full_dispute_enters_arbitration(self) -> None:
        self.assertRegex(TEMPLATES, r"`dispute`[^\n]*arbitrate")
    def test_explicit_challenges_enter_direct_arbitration(self) -> None:
        self.assertIn("explicit contract or upstream challenge", CONTRACT)
        self.assertIn("user challenge", CONTRACT)
        self.assertIn("direct arbitration", CONTRACT)
    def test_repeated_same_finding_disagreement_enters_arbitration(self) -> None:
        self.assertIn(
            "same finding remains disputed after focused rework", CONTRACT
        )
        self.assertIn("Do not repeat the rework loop", CONTRACT)
    def test_blocking_review_failure_skips_verify(self) -> None:
        self.assertIn("Blocking review failure skips verify", CONTRACT)
        self.assertIn("Review pass with non-blocking notes", CONTRACT)
    def test_rework_preserves_existing_work(self) -> None:
        self.assertIn("preserve existing commits", TEMPLATES)
        self.assertIn("valid receipts", TEMPLATES)
        self.assertIn("unrelated completed work", TEMPLATES)
    def test_structured_findings_and_exact_disposition_receipt(self) -> None:
        for field in ("ID", "Category", "Evidence", "Required behavior"):
            self.assertIn(f"{field}:", TEMPLATES)
        receipt = re.compile(
            r"Review disposition: accept \| partial \| dispute\n"
            r"Accepted findings IDs: <stable finding IDs or none>\n"
            r"Disputed findings IDs: <stable finding IDs or none>\n"
            r"Reason: <contract/code evidence>\n"
            r"Action: rework \| arbitration"
        )
        self.assertRegex(TEMPLATES, receipt)
    def test_skill_calls_canonical_flow_instead_of_duplicating_it(self) -> None:
        self.assertIn("templates.md **Review disposition**", SKILL)
        self.assertNotIn("Review disposition: accept | partial | dispute", SKILL)
if __name__ == "__main__":
    unittest.main()
