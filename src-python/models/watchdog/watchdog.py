"""Provides a Watchdog class for monitoring process liveness."""
import time
from typing import Callable, Optional


class Watchdog:
    """
    A simple watchdog timer. It checks if `feed()` has been called within a
    `timeout` period. If not, a registered callback is invoked during the
    `start()` method's execution. The `start()` method performs one check cycle.
    """
    timeout: int
    interval: int
    last_feed_time: float
    callback: Optional[Callable[[], None]]

    def __init__(self, timeout: int = 60, interval: int = 20) -> None:
        """
        Initializes the watchdog with timeout, check interval, and sets the
        initial feed time. Callback is initially not set.
        """
        self.timeout = timeout
        self.interval = interval
        self.last_feed_time = time.time()
        self.callback = None

    def feed(self) -> None:
        """Updates the last feed time, effectively resetting the watchdog timer."""
        self.last_feed_time = time.time()

    def setCallback(self, callback: Callable[[], None]) -> None:
        """Registers a callback function to be executed upon timeout."""
        self.callback = callback

    def start(self) -> None:
        """
        Performs a timeout check. If a timeout occurred since the last feed,
        it executes the registered callback. Then, it sleeps for `self.interval`.
        This method is designed to be called repeatedly by an external mechanism
        (e.g., a looping thread).
        """
        if time.time() - self.last_feed_time > self.timeout:
            if callable(self.callback): # Use callable() for type safety
                try:
                    self.callback()
                except Exception as e:
                    # Log the error from the callback if an error logger is available
                    # For now, just printing to stderr or could use a local basic logger
                    print(f"Error in Watchdog callback: {e}") 
        time.sleep(self.interval)