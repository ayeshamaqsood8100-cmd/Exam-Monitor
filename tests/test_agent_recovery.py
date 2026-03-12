import unittest

from agent.main import classify_saved_session_recovery


class SavedSessionRecoveryTests(unittest.TestCase):
    def test_resume_when_remote_session_is_active(self) -> None:
        decision = classify_saved_session_recovery(
            "exam-123",
            "exam-123",
            "active",
        )
        self.assertEqual(decision, "resume")

    def test_preserve_when_backend_is_temporarily_unreachable(self) -> None:
        decision = classify_saved_session_recovery(
            "exam-123",
            "exam-123",
            None,
        )
        self.assertEqual(decision, "preserve_unverified")

    def test_clear_when_saved_exam_does_not_match(self) -> None:
        decision = classify_saved_session_recovery(
            "exam-old",
            "exam-new",
            None,
        )
        self.assertEqual(decision, "clear")

    def test_clear_when_remote_session_was_terminated(self) -> None:
        decision = classify_saved_session_recovery(
            "exam-123",
            "exam-123",
            "terminated",
        )
        self.assertEqual(decision, "clear")


if __name__ == "__main__":
    unittest.main()
