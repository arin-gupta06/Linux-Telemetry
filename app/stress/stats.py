from typing import Any, Dict, List


def percentile(values: List[float], pct: float) -> float:
    """Compute exact percentile value with linear interpolation."""
    if not values:
        return 0.0

    ordered = sorted(values)
    index = (len(ordered) - 1) * (pct / 100.0)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)

    if lower == upper:
        return ordered[lower]

    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def latency_stats(values: List[float]) -> Dict[str, float]:
    """Calculate comprehensive latency distribution statistics in seconds."""
    if not values:
        return {
            "avg": 0.0,
            "min": 0.0,
            "p50": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "max": 0.0,
        }

    return {
        "avg": round(sum(values) / len(values), 4),
        "min": round(min(values), 4),
        "p50": round(percentile(values, 50), 4),
        "p90": round(percentile(values, 90), 4),
        "p95": round(percentile(values, 95), 4),
        "p99": round(percentile(values, 99), 4),
        "max": round(max(values), 4),
    }


def calculate_fairness(user_completions: Dict[str, int]) -> Dict[str, Any]:
    """Calculate fairness distribution across simulated concurrent users."""
    if not user_completions:
        return {
            "active_users_completed": 0,
            "min_completed_per_user": 0,
            "max_completed_per_user": 0,
            "avg_completed_per_user": 0.0,
        }

    counts = list(user_completions.values())
    return {
        "active_users_completed": len(user_completions),
        "min_completed_per_user": min(counts),
        "max_completed_per_user": max(counts),
        "avg_completed_per_user": round(sum(counts) / len(counts), 2),
    }
