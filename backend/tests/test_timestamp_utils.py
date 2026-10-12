from app.rag.timestamp_utils import (
    timestamp_to_seconds,
    seconds_to_timestamp,
    extract_timestamps_from_text,
    parse_relative_time_question,
    calculate_time_window
)


def test_timestamp_to_seconds_valid():
    assert timestamp_to_seconds("00:01:00") == 60.0
    assert timestamp_to_seconds("01:00:00") == 3600.0
    assert timestamp_to_seconds("01:27:37,500") == 5257.5
    assert timestamp_to_seconds("01:27:37.500") == 5257.5
    assert timestamp_to_seconds("05:30") == 330.0


def test_timestamp_to_seconds_invalid():
    assert timestamp_to_seconds("invalid_time") is None
    assert timestamp_to_seconds("") is None
    assert timestamp_to_seconds(None) is None


def test_seconds_to_timestamp():
    assert seconds_to_timestamp(60.0, include_millis=False) == "00:01:00"
    assert seconds_to_timestamp(3600.0, include_millis=False) == "01:00:00"
    assert seconds_to_timestamp(5257.5, include_millis=True) == "01:27:37,500"


def test_extract_timestamps_from_text():
    text = "The scene starts at 00:05:56 and runs until 00:06:16 in the film."
    ts = extract_timestamps_from_text(text)
    assert len(ts) == 2
    assert ts[0] == "00:05:56"
    assert ts[1] == "00:06:16"


def test_parse_relative_time_before():
    q = "What happens 5 minutes before 01:27:00 in Interstellar?"
    s, e = parse_relative_time_question(q)
    assert s is not None and e is not None
    # 01:27:00 = 5220s. 5 mins before = 4920s to 5220s
    assert s == 4920.0
    assert e == 5220.0


def test_parse_relative_time_after():
    q = "What happens 10 minutes after 00:40:00?"
    s, e = parse_relative_time_question(q)
    assert s is not None and e is not None
    # 00:40:00 = 2400s. 10 mins after = 2400s to 3000s
    assert s == 2400.0
    assert e == 3000.0


def test_parse_relative_time_around():
    q = "What occurs around 00:05:00 in the movie?"
    s, e = parse_relative_time_question(q)
    assert s is not None and e is not None
    # 00:05:00 = 300s. around = [240, 360]
    assert s == 240.0
    assert e == 360.0


def test_calculate_time_window_clamping():
    s, e = calculate_time_window("What happened at 00:00:10?", default_window=60.0, min_val=0.0, max_val=1000.0)
    assert s == 0.0  # Clamped to min_val
    assert e == 70.0
