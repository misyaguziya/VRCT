import unittest
from unittest.mock import MagicMock, patch

import openvr

from models import openvr_session
from models.clipboard.clipboard import Clipboard
from models.overlay.overlay import Overlay

# Real classes, captured before any test patches openvr.IVRSystem/IVROverlay
# themselves -- MagicMock(spec=...) needs the genuine class, not a mock of it.
_RealIVRSystem = openvr.IVRSystem
_RealIVROverlay = openvr.IVROverlay


def _overlay_settings() -> dict:
    return {
        "small": {
            "x_pos": 0.0, "y_pos": 0.0, "z_pos": 0.0,
            "x_rotation": 0.0, "y_rotation": 0.0, "z_rotation": 0.0,
            "display_duration": 5, "fadeout_duration": 2,
            "opacity": 1.0, "ui_scaling": 1.0, "tracker": "HMD",
        },
    }


class OpenvrSessionRefCountTests(unittest.TestCase):
    """Unit tests of the shared session's own acquire()/release() bookkeeping."""

    def setUp(self) -> None:
        # openvr_session holds process-wide module state; start every test
        # from a clean slate regardless of test order or a prior failure.
        openvr_session._ref_count = 0
        openvr_session._system = None

    tearDown = setUp

    @patch("openvr.shutdown")
    @patch("openvr.init")
    def test_second_acquire_reuses_session_without_reinitializing(
        self, openvr_init: MagicMock, openvr_shutdown: MagicMock,
    ) -> None:
        sentinel = object()
        openvr_init.return_value = sentinel

        first = openvr_session.acquire()
        second = openvr_session.acquire()

        self.assertIs(first, sentinel)
        self.assertIs(second, sentinel)
        openvr_init.assert_called_once()

    @patch("openvr.shutdown")
    @patch("openvr.init")
    def test_shutdown_only_runs_after_the_last_release(
        self, openvr_init: MagicMock, openvr_shutdown: MagicMock,
    ) -> None:
        openvr_init.return_value = object()

        openvr_session.acquire()
        openvr_session.acquire()
        openvr_session.release()
        openvr_shutdown.assert_not_called()

        openvr_session.release()
        openvr_shutdown.assert_called_once()

    @patch("openvr.shutdown")
    def test_release_without_a_matching_acquire_is_a_noop(
        self, openvr_shutdown: MagicMock,
    ) -> None:
        openvr_session.release()
        openvr_shutdown.assert_not_called()

    @patch("openvr.shutdown")
    @patch("openvr.init")
    def test_failed_acquire_does_not_bump_the_ref_count(
        self, openvr_init: MagicMock, openvr_shutdown: MagicMock,
    ) -> None:
        openvr_init.side_effect = RuntimeError("no HMD connected")

        with self.assertRaises(RuntimeError):
            openvr_session.acquire()

        self.assertFalse(openvr_session.is_active())
        # A stray release() after a failed acquire must stay a no-op.
        openvr_session.release()
        openvr_shutdown.assert_not_called()


class OpenvrSessionSharingTests(unittest.TestCase):
    """Regression coverage for item 14: neither Clipboard nor Overlay may
    call the real (process-wide) openvr.shutdown() while the other still
    holds a reference to the shared OpenVR session.
    """

    def setUp(self) -> None:
        openvr_session._ref_count = 0
        openvr_session._system = None

    tearDown = setUp

    @patch("openvr.shutdown")
    @patch("openvr.init")
    @patch("openvr.VRApplications")
    def test_clipboard_lookup_does_not_tear_down_an_active_overlay_session(
        self,
        vr_applications: MagicMock,
        openvr_init: MagicMock,
        openvr_shutdown: MagicMock,
    ) -> None:
        fake_system = MagicMock(spec=_RealIVRSystem)
        openvr_init.return_value = fake_system
        vr_applications.return_value.getApplicationCount.return_value = 0

        # Simulate Overlay already holding an active reference to the
        # shared session (Overlay.init()/shutdownOverlay() route through
        # these same acquire()/release() calls -- see the dedicated test
        # below for that wiring).
        overlay_system_ref = openvr_session.acquire()
        self.assertIs(overlay_system_ref, fake_system)

        # Simulate SteamVR being detected by Clipboard's monitor thread
        # while Overlay's session is still active. Construct the instance
        # without running __init__ so no background thread is spawned;
        # _setup_vr_app_name() is called directly instead.
        clipboard = Clipboard.__new__(Clipboard)
        clipboard.app_name = None
        clipboard._setup_vr_app_name()

        # The whole point of the shared, reference-counted session:
        # Clipboard's one-shot lookup must not call the real
        # openvr.shutdown() while Overlay is still holding a reference.
        openvr_shutdown.assert_not_called()
        self.assertTrue(openvr_session.is_active())

        # Overlay releasing afterwards (Clipboard already released its own
        # reference) is what should finally shut the shared session down.
        openvr_session.release()
        openvr_shutdown.assert_called_once()

    @patch("openvr.shutdown")
    @patch("openvr.init")
    @patch("openvr.VRApplications")
    def test_clipboard_releases_its_reference_even_if_the_lookup_fails(
        self,
        vr_applications: MagicMock,
        openvr_init: MagicMock,
        openvr_shutdown: MagicMock,
    ) -> None:
        # A failure between acquire() and release() (e.g. VRApplications()
        # raising) must not leak the reference -- otherwise the shared
        # session would stay "held" forever and shutdown() would never run
        # again for the rest of the process.
        openvr_init.return_value = MagicMock(spec=_RealIVRSystem)
        vr_applications.side_effect = RuntimeError("VRApplications unavailable")

        clipboard = Clipboard.__new__(Clipboard)
        clipboard.app_name = None
        clipboard._setup_vr_app_name()

        self.assertIsNone(clipboard.app_name)
        self.assertFalse(openvr_session.is_active())

    def test_overlay_init_and_shutdown_route_through_the_shared_session(
        self,
    ) -> None:
        # Proves Overlay's own lifecycle goes through openvr_session too
        # (not just Clipboard's) -- otherwise a fix that only routed
        # Clipboard through the shared module would leave Overlay's own
        # openvr.shutdown() call able to tear itself down early just the
        # same, or worse, mask the sharing bug entirely in the test above.
        with patch("models.openvr_session.acquire") as acquire_mock, \
             patch("models.openvr_session.release") as release_mock:
            acquire_mock.return_value = MagicMock(spec=_RealIVRSystem)

            # openvr.IVROverlay/IVRSystem only need faking for the init()
            # call itself; scoping this patch tighter than acquire/release
            # means it is back to the real class before shutdownOverlay()
            # runs its isinstance() checks below.
            with patch("openvr.IVROverlay") as ivroverlay_cls, patch("openvr.IVRSystem"):
                ivroverlay_cls.return_value = MagicMock(spec=_RealIVROverlay)
                overlay = Overlay(_overlay_settings())
                overlay.init()

            acquire_mock.assert_called_once_with(openvr.VRApplication_Background)
            self.assertTrue(overlay.initialized)

            # acquire/release are still patched here, so this exercises the
            # real shutdownOverlay() -> openvr_session.release() wiring.
            overlay.shutdownOverlay()
            release_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
