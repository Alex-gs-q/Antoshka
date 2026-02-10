from services.time_parse import parse_duration_seconds, parse_time_of_day


def test_parse_duration_seconds():
    assert parse_duration_seconds("5 минут") == 300
    assert parse_duration_seconds("2 часа") == 7200
    assert parse_duration_seconds("10 сек") == 10
    assert parse_duration_seconds("10 секунд") == 10
    assert parse_duration_seconds("1 час 20 минут") == 4800
    assert parse_duration_seconds("через 2 минуты") == 120
    assert parse_duration_seconds("") is None
    assert parse_duration_seconds("abc") is None


def test_parse_time_of_day():
    dt = parse_time_of_day("18:30")
    assert dt is not None
    assert dt.hour == 18
    assert dt.minute == 30
