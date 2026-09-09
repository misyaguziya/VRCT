"""_AudioDeviceSession.resume() のTOCTOUハング修正に関するテスト
(コードレビュー指摘)。

対象の欠陥: 以前は
    while not self._audio_queue.empty():
        self._audio_queue.get()
という非アトミックな check-then-act だったため、_print_transcript
スレッド (transcribeAudioQueue) が同時に同じキューを drain している
と、resume() が empty()==False を見た直後にその最後の1件を向こうに
取られ、後続のブロッキング get() (タイムアウト無し) が、もう誰も put
しないため永久にハングし、self._recorder.resume() が一生呼ばれなく
なるバグがあった。VRChatでの素早いミュート/アンミュート切り替えで
再現しうる (mic_lifecycle_lock を握ったままハングするため、後続の
ミュート操作・デバイス切替・shutdown まで巻き添えでデッドロックする)。

修正: get_nowait() のみを使う drain に変更。get_nowait() は他スレッド
と競合してもブロックせず即座に Empty を返すだけなので、原理的に
ハングし得ない。
"""

import threading
import time
import unittest
from queue import Empty, Queue

from model import MicSession


class _StubRecorder:
    def __init__(self) -> None:
        self.resume_calls = 0

    def resume(self) -> None:
        self.resume_calls += 1


class ResumeDrainDoesNotHangTests(unittest.TestCase):
    def test_resume_drains_queued_items_and_calls_recorder_resume(self) -> None:
        session = MicSession()
        session._audio_queue = Queue()
        session._audio_queue.put((b"stale-1", "t1"))
        session._audio_queue.put((b"stale-2", "t2"))
        session._recorder = _StubRecorder()

        session.resume()

        self.assertTrue(session._audio_queue.empty())
        self.assertEqual(session._recorder.resume_calls, 1)

    def test_resume_does_not_hang_when_a_concurrent_thread_drains_the_same_queue(self) -> None:
        """_print_transcript 相当の別スレッドが同時に同じキューを
        get_nowait() で吸い出し続けても、resume() は永久にブロックせず
        速やかに戻ること (実際のバグ再現条件)。"""
        session = MicSession()
        session._audio_queue = Queue()
        session._audio_queue.put((b"stale", "t1"))
        session._recorder = _StubRecorder()

        stop_event = threading.Event()

        def concurrent_drainer() -> None:
            while not stop_event.is_set():
                try:
                    session._audio_queue.get_nowait()
                except Empty:
                    time.sleep(0.001)

        drainer = threading.Thread(target=concurrent_drainer, daemon=True)
        drainer.start()
        try:
            done = threading.Event()

            def run_resume() -> None:
                session.resume()
                done.set()

            t = threading.Thread(target=run_resume, daemon=True)
            t.start()
            finished = done.wait(timeout=2.0)
            self.assertTrue(finished, "resume() が2秒以内に戻らなかった (ハングしている)")
        finally:
            stop_event.set()
            drainer.join(timeout=1.0)

        self.assertEqual(session._recorder.resume_calls, 1)

    def test_resume_tolerates_a_missing_recorder(self) -> None:
        session = MicSession()
        session._audio_queue = Queue()
        session._recorder = None

        session.resume()  # 例外が出ないこと


if __name__ == "__main__":
    unittest.main()
