import math


def weekly_delta(stars: int, old: int | None) -> int | None:
    return stars - old if old is not None else None


def score(stars: int, weekly_delta: int | None, days_since_push: float) -> float:
    growth = math.log1p(max(weekly_delta or 0, 0)) * 3
    popularity = math.log1p(max(stars, 0))
    freshness = max(0.0, 1 - max(days_since_push, 0) / 90) * 2
    return round(growth + popularity + freshness, 3)
