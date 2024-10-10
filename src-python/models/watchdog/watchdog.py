from typing import Callable
import time
from utils import printLog

class Watchdog:
    def __init__(self, timeout:int=60, interval:int=20):
        self.timeout = timeout
        self.interval = interval
        self.last_feed_time = time.time()

    def feed(self):
        self.last_feed_time = time.time()

    def setCallback(self, callback):
        self.callback = callback

    def start(self):
        if time.time() - self.last_feed_time > self.timeout:
            printLog("Watchdog timeout! Shutting down...")
            if isinstance(self.callback, Callable):
                self.callback()
        time.sleep(self.interval)