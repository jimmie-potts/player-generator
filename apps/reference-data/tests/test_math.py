from reference_data_app.math import parse_minutes


def test_parse_minutes() -> None:
    assert parse_minutes("12:30") == 12.5
    assert parse_minutes("0:45") == 0.75
    assert parse_minutes(7.25) == 7.25
    assert parse_minutes(None) == 0.0
    assert parse_minutes("not-a-minute") == 0.0
