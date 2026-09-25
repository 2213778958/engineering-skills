"""Contract tests for same-ticket department resume after arbitration."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = "\n".join(
    (ROOT / name).read_text(encoding="utf-8")
    for name in ("SKILL.md", "references/rules.md")
)
TEMPLATES = (ROOT / "references" / "templates.md").read_text(encoding="utf-8")

RESUME_RULE = re.compile(
    r"^19\. \*\*Same-ticket department continuation\.\*\*(?P<rule>.*)$", re.M
)
RESUME_SECTION = re.compile(
    r"(?ms)^## Department resume \(same-ticket continuation\)\n"
    r"(?P<section>.*?)(?=^## )"
)
RESUME_COMMAND = re.compile(
    r"spawn\.py --mode resume --target-id <uuid> --ticket #<n> --request-id <id>"
)


def resume_rule_text() -> str:
    match = RESUME_RULE.search(SKILL)
    if not match:
        raise AssertionError("SKILL.md rule 19 for department continuation is missing")
    return match["rule"]


def resume_section_text() -> str:
    match = RESUME_SECTION.search(TEMPLATES)
    if not match:
        raise AssertionError(
            "templates.md Department resume section is missing"
        )
    return match["section"]


class ResumeContinuationContractTest(unittest.TestCase):
    """Rules must require explicit resume with target and request identity."""

    def setUp(self) -> None:
        self.rule = resume_rule_text()
        self.section = resume_section_text()

    def test_skill_rule_requires_explicit_resume_command(self) -> None:
        self.assertIn("spawn.py --mode resume", self.rule)
        self.assertIn("--target-id", self.rule)
        self.assertIn("--ticket", self.rule)
        self.assertIn("--request-id", self.rule)
        self.assertIn("original department manage conversation", self.rule)

    def test_templates_section_carries_the_full_command(self) -> None:
        self.assertRegex(self.section, RESUME_COMMAND)
        self.assertIn("stable request identity", self.section)

    def test_redispatch_and_new_window_are_forbidden(self) -> None:
        self.assertIn("Do not `--mode dispatch`", self.rule)
        self.assertIn("`--mode open` a new window", self.rule)
        self.assertIn("redispatch or a new department window → **fail**", self.section)

    def test_inferring_target_from_an_old_conversation_id_is_forbidden(self) -> None:
        self.assertIn("Do not infer the target from an old conversation id", self.rule)
        self.assertIn(
            "Never infer the continuation target from an old conversation id",
            self.section,
        )
        self.assertIn("recorded at 分发", self.section)

    def test_hop_table_marks_same_department_as_continuation(self) -> None:
        self.assertIn(
            "that is a continuation, not a new 分发: **Department resume**",
            TEMPLATES,
        )


class DepartmentVsEmployeeIdentityTest(unittest.TestCase):
    """The resumed target is the department manage session, never an employee."""

    def setUp(self) -> None:
        self.rule = resume_rule_text()
        self.section = resume_section_text()

    def test_rules_name_the_manage_window_as_target(self) -> None:
        self.assertIn("the target is the department **manage** window", self.rule)
        self.assertIn(
            "the department **manage** window (the dispatch child carrying that "
            "department tag)",
            self.section,
        )

    def test_employee_conversations_must_not_be_resumed(self) -> None:
        self.assertIn("Do not resume or reuse an employee conversation", self.rule)
        self.assertIn(
            "resuming or reusing an employee conversation for department "
            "continuation → **fail**",
            self.section,
        )
        self.assertIn("never an implement / review / verify subagent", self.section)
        self.assertIn("have no conversation window to resume", self.section)


class PreservationTest(unittest.TestCase):
    """Continuation preserves work and reruns only invalidated hops."""

    def test_section_requires_preserving_prior_work(self) -> None:
        section = resume_section_text()
        for item in ("commits", "accepted fixes", "history", "valid receipts"):
            self.assertIn(item, section)
        self.assertIn("Preserve commits, accepted fixes", section)

    def test_section_limits_reruns_to_invalidated_hops(self) -> None:
        section = resume_section_text()
        self.assertIn("Rerun only the hops the arbitration verdict invalidated", section)
        self.assertIn("do not re-run accepted independent findings", section)
        self.assertIn("already verified hops", section)

    def test_accepted_receipt_is_not_work_completion(self) -> None:
        section = resume_section_text()
        self.assertIn(
            "`accepted` = the continuation operation was accepted only, "
            "not department work completion",
            section,
        )
        self.assertIn("do not finish the hop, do not watch", section)


class ReceiptHandlingTest(unittest.TestCase):
    """Unknown reconciles without blind retry; rejected stops with evidence."""

    def setUp(self) -> None:
        self.section = resume_section_text()

    def test_unknown_requires_reconciliation_with_same_identity(self) -> None:
        self.assertIn(
            "`unknown` = unproven (timeout or lost response): reconcile with "
            "the same `--ticket` + `--request-id`",
            self.section,
        )
        self.assertIn("no blind retry", self.section)

    def test_rejected_stops_with_evidence_without_replacement_or_bypass(self) -> None:
        self.assertIn("`rejected` = stop with the receipt evidence", self.section)
        self.assertIn("no automatic replacement dispatch", self.section)
        self.assertIn("no force bypass", self.section)

    def test_timeout_is_unknown_until_reconciled_not_a_retry_trigger(self) -> None:
        self.assertIn(
            "a timeout or lost response is unknown-until-reconciled, "
            "not a retry trigger",
            self.section,
        )
        self.assertIn("no redispatch on timeout", self.section)


class NotifyAndAdapterBoundaryTest(unittest.TestCase):
    """notify stays child->parent and callers stay on the sessions abstraction."""

    def test_resumed_department_reports_child_to_parent_via_notify(self) -> None:
        section = resume_section_text()
        self.assertIn("Reporting stays child → parent", section)
        self.assertIn("spawn.py --mode notify", section)

    def test_callers_use_spawn_py_never_copied_http(self) -> None:
        section = resume_section_text()
        self.assertIn("Planning manage resumes via sessions only", section)
        self.assertIn("never copied raw HTTP calls", section)


class ReviewDispositionSeparationTest(unittest.TestCase):
    """The #35 disposition flow stays intact and separate from resume."""

    def test_review_disposition_flow_still_present(self) -> None:
        self.assertIn("## Review disposition", TEMPLATES)
        self.assertIn("returns findings to the original implement employee", TEMPLATES)

    def test_skill_still_delegates_disposition_detail(self) -> None:
        self.assertIn("templates.md **Review disposition**", SKILL)
        self.assertNotIn("Review disposition: accept | partial | dispute", SKILL)

    def test_resume_rules_do_not_conflate_the_two_flows(self) -> None:
        rule = resume_rule_text()
        section = resume_section_text()
        self.assertIn("that flow is separate", rule)
        self.assertIn(
            "This resume does not implement the **Review disposition** flow", section
        )
        self.assertIn("do not conflate them", section)

    def test_resume_delegates_receipt_detail_to_templates(self) -> None:
        rule = resume_rule_text()
        self.assertIn("templates.md **Department resume**", rule)
        self.assertNotIn("spawn.py --mode resume --target-id <uuid>", SKILL)
        self.assertNotIn("unknown-until-reconciled", SKILL)


if __name__ == "__main__":
    unittest.main()
