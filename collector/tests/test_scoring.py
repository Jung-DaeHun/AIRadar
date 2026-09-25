from collector.scoring import score, weekly_delta


def test_weekly_delta_none_without_old_snapshot():
    assert weekly_delta(100, None) is None
    assert weekly_delta(100, 80) == 20


def test_growth_beats_raw_popularity():
    assert score(500, 300, 1) > score(5000, 0, 1)


def test_fresh_beats_stale():
    assert score(100, 10, 1) > score(100, 10, 80)


def test_negative_delta_and_old_push_do_not_go_negative():
    assert score(0, -50, 400) == 0.0
