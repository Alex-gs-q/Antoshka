from services.voice_timeout import apply_timeout_ms, get_voice_timeout_seconds


def test_apply_timeout_ms():
    assert apply_timeout_ms(7) == 7000


def test_get_voice_timeout_seconds():
    settings = {"ui": {"voice_response_timeout_sec": 9}}
    assert get_voice_timeout_seconds(settings) == 9
