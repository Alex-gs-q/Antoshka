from services.time_parse import parse_duration_seconds, parse_time_of_day


def test_parse_duration_seconds():
    assert parse_duration_seconds("5 \u043c\u0438\u043d\u0443\u0442") == 300
    assert parse_duration_seconds("2 \u0447\u0430\u0441\u0430") == 7200
    assert parse_duration_seconds("10 \u0441\u0435\u043a") == 10
    assert parse_duration_seconds("") is None
    assert parse_duration_seconds("abc") is None


def test_parse_time_of_day():
    dt = parse_time_of_day("18:30")
    assert dt is not None
    assert dt.hour == 18
    assert dt.minute == 30
