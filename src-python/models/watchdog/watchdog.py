import os
import time
from threading import Thread, Event
from utils import printLog

class Watchdog:
    def __init__(self, timeout:int=60, interval:int=1):
        self.timeout = timeout
        self.interval = interval
        self.last_feed_time = time.time()
        self._stop_event = Event()
        self._watchdog_thread = Thread(target=self._watchdog_loop)

    def start(self):
        self._watchdog_thread.start()

    def stop(self):
        self._stop_event.set()
        self._watchdog_thread.join()

    def feed(self):
        self.last_feed_time = time.time()

    def _watchdog_loop(self):
        while not self._stop_event.is_set():
            if time.time() - self.last_feed_time > self.timeout:
                printLog("Watchdog timeout! Shutting down...")
                os._exit(1)

            time.sleep(self.interval)