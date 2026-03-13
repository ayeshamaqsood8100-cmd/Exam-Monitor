import unittest
from uuid import uuid4
from unittest.mock import patch

from fastapi import HTTPException

from backend.models.session import SessionStartModel
from backend.routes.session import process_session_start


class SessionRouteTests(unittest.TestCase):
    @patch("backend.routes.session.start_session")
    def test_session_start_surfaces_terminated_detail(self, start_session_mock) -> None:
        start_session_mock.side_effect = ValueError("Session terminated; reinstall required.")

        with self.assertRaises(HTTPException) as context:
            process_session_start(
                SessionStartModel(student_erp="12345", exam_id=uuid4())
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.detail, "Session terminated; reinstall required.")


if __name__ == "__main__":
    unittest.main()
