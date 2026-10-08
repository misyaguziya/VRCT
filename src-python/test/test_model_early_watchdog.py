"""An early frontend heartbeat must not take ownership of Model initialization."""
import threading
import unittest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import controller as controller_module
import model as model_module


class EarlyWatchdogTests(unittest.TestCase):
    def setUp(self):
        self.model = object.__new__(model_module.Model)
        self.model._inited = False
        self.model._init_failed = False

    def test_prebootstrap_feed_does_not_initialize_resources_or_arm_dump(self):
        for initialization_started in (False, True):
            with self.subTest(initialization_started=initialization_started):
                self.model._init_failed = initialization_started
                with patch.object(self.model, "init") as init, \
                     patch.object(self.model, "_armFreezeDump") as arm:
                    self.assertIsNone(self.model.feedWatchdog())
                init.assert_not_called()
                arm.assert_not_called()
                self.assertFalse(hasattr(self.model, "watchdog"))
                self.assertFalse(self.model._inited)
                self.assertEqual(self.model._init_failed, initialization_started)

    def test_existing_watchdog_is_fed_without_retrying_failed_initialization(self):
        self.model._init_failed = True
        self.model.watchdog = MagicMock()
        with patch.object(self.model, "init") as init, \
             patch.object(self.model, "_armFreezeDump") as arm:
            self.model.feedWatchdog()
        init.assert_not_called()
        self.model.watchdog.feed.assert_called_once_with()
        arm.assert_called_once_with()

    def test_initialized_watchdog_keeps_feeding_and_arming_dump(self):
        self.model._inited = True
        self.model.watchdog = MagicMock()
        with patch.object(self.model, "init") as init, \
             patch.object(self.model, "_armFreezeDump") as arm:
            self.model.feedWatchdog()
        init.assert_not_called()
        self.model.watchdog.feed.assert_called_once_with()
        arm.assert_called_once_with()

    def test_early_feed_then_bootstrap_keeps_all_resource_callbacks(self):
        controller = object.__new__(controller_module.Controller)
        controller._model = self.model
        overlay_callbacks = {
            "position_changed_callback": "_onOverlayPositionChanged",
            "pointer_callback": "_onVrPanelPointer",
            "panel_out_of_view_callback": "_onVrPanelLogOutOfView",
            "launcher_intro_callback": "_onVrPanelLauncherIntro",
            "layout_callback": "_onVrPanelLayout",
        }
        for method in [*overlay_callbacks.values(), "_changeMicTranscriptStatusLocked"]:
            setattr(controller, method, MagicMock())
        watchdog_callback = MagicMock()
        # Keep the real Model/Controller initialization and callback setters;
        # replace only constructors that would create devices/services/threads.
        with ExitStack() as stack:
            constructors = {name: stack.enter_context(patch.object(model_module, name)) for name in (
                "MicSession", "SpeakerSession", "AudioLifecycleWorker", "ThreadPoolExecutor",
                "Translator", "KeywordProcessor", "Overlay", "OverlayImage", "OSCHandler",
                "Clipboard", "Telemetry",
            )}
            stack.enter_context(patch.object(model_module, "launcherOutOfReach", return_value=False))
            stack.enter_context(patch.object(controller_module, "model", self.model))
            errors = stack.enter_context(patch.object(controller_module, "errorLogging"))
            self.model.feedWatchdog()
            for constructor in constructors.values():
                constructor.assert_not_called()
            controller.setWatchdogCallback(watchdog_callback)
            controller._bootstrapModel()
            self.assertTrue(self.model._inited)
            self.assertFalse(self.model._init_failed)
            self.assertIs(self.model.watchdog.callback, watchdog_callback)
            self.assertIs(self.model.mic_mute_status_change_callback, controller._changeMicTranscriptStatusLocked)
            for attribute, method in overlay_callbacks.items():
                self.assertIs(getattr(self.model.overlay, attribute), getattr(controller, method))
            errors.assert_not_called()

    def test_feed_remains_available_while_main_thread_initializes_resources(self):
        entered = threading.Event()
        release = threading.Event()
        failures = []

        class EndInit(Exception):
            pass

        def stalled_session():
            entered.set()
            if not release.wait(5):
                raise TimeoutError("Test did not release initialization")
            raise EndInit()

        def initialize():
            try:
                self.model.init()
            except EndInit:
                pass
            except Exception as exc:
                failures.append(exc)

        with patch.object(model_module, "MicSession", side_effect=stalled_session), \
             patch.object(self.model, "_armFreezeDump") as arm:
            initializer = threading.Thread(target=initialize)
            initializer.start()
            try:
                self.assertTrue(entered.wait(5))
                with patch.object(self.model.watchdog, "feed") as feed:
                    self.model.feedWatchdog()
                    feed.assert_called_once_with()
                arm.assert_called_once_with()
                self.assertTrue(initializer.is_alive())
            finally:
                release.set()
                initializer.join(5)
        self.assertFalse(initializer.is_alive())
        self.assertEqual(failures, [])

    def test_feed_failure_is_propagated_without_arming_dump(self):
        self.model.watchdog = MagicMock()
        self.model.watchdog.feed.side_effect = RuntimeError("feed failed")
        with patch.object(self.model, "_armFreezeDump") as arm, \
             self.assertRaisesRegex(RuntimeError, "feed failed"):
            self.model.feedWatchdog()
        arm.assert_not_called()


if __name__ == "__main__":
    unittest.main()
