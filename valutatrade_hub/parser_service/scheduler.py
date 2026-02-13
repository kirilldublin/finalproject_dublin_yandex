from __future__ import annotations

import threading
import time

from valutatrade_hub.parser_service.updater import RatesUpdater


class RatesScheduler:
    def __init__(self, updater: RatesUpdater, interval_seconds: int = 300) -> None:
        self._updater = updater
        self._interval_seconds = interval_seconds
        self._stop_event = threading.Event()

    def run_forever(self) -> None:
        while not self._stop_event.is_set():
            self._updater.run_update()
            self._stop_event.wait(self._interval_seconds)

    def stop(self) -> None:
        self._stop_event.set()

    def run_once_after_delay(self, delay_seconds: int) -> None:
        time.sleep(delay_seconds)
        if not self._stop_event.is_set():
            self._updater.run_update()
