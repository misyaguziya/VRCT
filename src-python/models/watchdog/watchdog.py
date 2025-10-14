from typing import Callable, Optional
import time
from threading import Thread, Event


class Watchdog:
    """A lightweight watchdog utility.

    This class provides a minimal watchdog which records the last "feed"
    timestamp and can invoke a user-supplied callback when the timeout
    is exceeded. The design is intentionally simple: callers are expected
    to either call `start()` periodically (e.g. from a loop) or extend the
    class to run `start()` in a background thread.

    Args:
        timeout: seconds without feed after which the callback is invoked
        interval: suggested sleep interval (seconds) for callers that poll
    """

    def __init__(self, timeout: int = 60, interval: int = 20) -> None:
        self.timeout = timeout
        self.interval = interval
        self.last_feed_time = time.time()
        self.callback: Optional[Callable[[], None]] = None
        # Background thread control
        self._thread: Optional[Thread] = None
        self._stop_event: Optional[Event] = None

    def feed(self) -> None:
        """Refresh the watchdog timer (set last feed time to now)."""
        self.last_feed_time = time.time()

    def setCallback(self, callback: Callable[[], None]) -> None:
        """Register a zero-argument callback invoked on timeout."""
        self.callback = callback

    def start(self) -> None:
        """Perform a single watchdog check and optionally sleep `interval` seconds.

        The method checks if the duration since the last feed exceeds
        `timeout`. If so and a callback is registered, the callback is called.

        Note: `start()` does not run in the background by itself; callers
        should call it repeatedly (or run it inside a thread) if continuous
        monitoring is required.
        """
        now = time.time()
        if now - self.last_feed_time > self.timeout:
            if callable(self.callback):
                try:
                    self.callback()
                except Exception:
                    # Do not let callback exceptions propagate out of watchdog
                    import traceback
                    traceback.print_exc()
        time.sleep(self.interval)

    def _run_loop(self) -> None:
        """Internal run loop used by `start_in_thread`.

        It repeatedly calls `start()` until `_stop_event` is set. The
        implementation relies on `start()` sleeping for `self.interval`.
        """
        # Defensive: ensure stop_event exists
        if self._stop_event is None:
            return
        while not self._stop_event.is_set():
            self.start()

    def start_in_thread(self, daemon: bool = True) -> None:
        """Start the watchdog in a background thread.

        If the watchdog is already running, this is a no-op. The created
        thread will repeatedly call `start()` until `stop()` is invoked.

        Args:
            daemon: if True, thread is a daemon thread (won't block process exit)
        """
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event = Event()
        self._thread = Thread(target=self._run_loop, daemon=daemon)
        self._thread.start()

    def stop(self, timeout: Optional[float] = None) -> None:
        """Stop background thread started by `start_in_thread`.

        If no background thread is running this is a no-op.

        Args:
            timeout: optional timeout to wait for thread join (seconds). If
                None, join will block until the thread exits.
        """
        if self._stop_event is None or self._thread is None:
            return
        # signal stop and wait for thread to finish
        self._stop_event.set()
        self._thread.join(timeout=timeout)
        # cleanup
        if self._thread.is_alive():
            # thread did not stop within timeout; leave objects for another stop()
            return
        self._thread = None
        self._stop_event = None