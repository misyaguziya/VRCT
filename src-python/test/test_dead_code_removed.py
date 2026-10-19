"""Regression coverage for item 16 (dead code removal).

These are guard tests, not behavior tests: the removed symbols were
confirmed unreferenced anywhere in the codebase before deletion (see
docs/backend_review_2026-08-27.md item 16), so there is no pre-fix
"buggy behavior" to reproduce here the way earlier items had. The point
of these tests is to catch an accidental reintroduction (e.g. a bad
merge resurrecting the duplicate dispatch path) rather than to prove a
behavioral bug is fixed.
"""
import unittest

import errors
import mainloop


class DeadCodeStaysRemovedTests(unittest.TestCase):
    def test_mainloop_no_longer_has_the_duplicate_handle_request_path(self) -> None:
        # handleRequest() was a near-byte-for-byte duplicate of
        # _call_handler() (the real production dispatch path used by
        # handler()); its only caller was the manual test_endpoints.py
        # harness, which now calls _call_handler() directly instead.
        self.assertFalse(hasattr(mainloop.Main, "handleRequest"))
        self.assertTrue(hasattr(mainloop.Main, "_call_handler"))

    def test_errors_module_no_longer_exposes_the_unused_symbols(self) -> None:
        for name in (
            "get_error_metadata",
            "is_critical_error",
            "requires_user_action",
            "ENDPOINT_ERROR_MAPPING",
        ):
            self.assertFalse(
                hasattr(errors, name),
                f"errors.{name} should have been removed (item 16) but still exists",
            )
        # ERROR_METADATA and ErrorCategory are still genuinely used inside
        # VRCTError/get metadata construction and must NOT be removed.
        self.assertTrue(hasattr(errors, "ERROR_METADATA"))
        self.assertTrue(hasattr(errors, "ErrorCategory"))


if __name__ == "__main__":
    unittest.main()
