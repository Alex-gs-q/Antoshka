import queue


from core.stt_vosk import VoskSTT


def test_safe_queue_get_empty():

    class Dummy:

        def get(self, timeout):

            raise queue.Empty()

    assert VoskSTT._safe_queue_get(Dummy(), 0.01) is None


def test_safe_queue_get_value():

    q = queue.Queue()

    q.put(b"abc")

    assert VoskSTT._safe_queue_get(q, 0.01) == b"abc"
