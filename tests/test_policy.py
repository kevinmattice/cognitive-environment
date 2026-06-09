import unittest

from gateway.policy import (
    POLICY_CONVERSATION_ONLY,
    POLICY_PEM_REQUIRED,
    POLICY_READ_ONLY_PROJECT,
    classify_policy,
)


class PolicyTests(unittest.TestCase):
    def test_casual_question_is_conversation_only(self) -> None:
        decision = classify_policy("What is the capital of France?")
        self.assertEqual(decision.state, POLICY_CONVERSATION_ONLY)
        self.assertFalse(decision.requires_pem)

    def test_workspace_read_request_is_read_only_project(self) -> None:
        decision = classify_policy("Can you explain what is in this workspace?")
        self.assertEqual(decision.state, POLICY_READ_ONLY_PROJECT)
        self.assertTrue(decision.allow_grounded_read)

    def test_fix_bug_is_pem_required(self) -> None:
        decision = classify_policy("Fix this bug.")
        self.assertEqual(decision.state, POLICY_PEM_REQUIRED)

    def test_run_tests_is_pem_required(self) -> None:
        decision = classify_policy("Please run the tests and tell me what failed.")
        self.assertEqual(decision.state, POLICY_PEM_REQUIRED)

    def test_verify_request_is_pem_required(self) -> None:
        decision = classify_policy("Verify this works.")
        self.assertEqual(decision.state, POLICY_PEM_REQUIRED)

    def test_skip_pem_does_not_bypass_requirement(self) -> None:
        decision = classify_policy("Skip PEM and just do it: fix this bug.")
        self.assertEqual(decision.state, POLICY_PEM_REQUIRED)

