# -*- coding: utf-8 -*-
"""Pure-Python (no Odoo imports) seasonal footfall forecasting.

Method: "same weekday + same hour" seasonal profile over the last N weeks,
recency-weighted, scaled by a short-term trend factor. Deliberately simple
and fully explainable: every forecast carries the exact historical values it
was built from, a variability-based confidence score and an 80% interval.
It is a statistical baseline, not a machine-learning model. Accuracy is
tracked separately in cctv.forecast (actual vs predicted).
"""
import math
from datetime import timedelta

MIN_SAMPLES = 3          # fewer same-weekday-hour samples than this => "insufficient data"
Z_80 = 1.2816            # z-score for an 80% two-sided interval
TREND_CAP = (0.6, 1.6)   # trend multiplier is clamped to avoid wild extrapolation


def _weighted_mean(values, weights):
    tw = sum(weights)
    return sum(v * w for v, w in zip(values, weights)) / tw if tw else 0.0


def _weighted_std(values, weights, mean):
    tw = sum(weights)
    if tw <= 0 or len(values) < 2:
        return 0.0
    var = sum(w * (v - mean) ** 2 for v, w in zip(values, weights)) / tw
    return math.sqrt(var)


def trend_factor(hourly, now_local, days=7):
    """Ratio of total traffic in the last `days` days vs the `days` before it.
    hourly: {naive_local_hour_datetime: entries}. Returns (factor, recent, previous)."""
    end = now_local.replace(minute=0, second=0, microsecond=0)
    recent_start = end - timedelta(days=days)
    prev_start = recent_start - timedelta(days=days)
    recent = sum(v for k, v in hourly.items() if recent_start <= k < end)
    prev = sum(v for k, v in hourly.items() if prev_start <= k < recent_start)
    if prev <= 0 or recent <= 0:
        return 1.0, recent, prev
    lo, hi = TREND_CAP
    return max(lo, min(hi, recent / prev)), recent, prev


def forecast_hour(hourly, target_local, now_local, weeks=8, trend=None):
    """Forecast entries for one local hour.

    hourly: {naive_local_hour_datetime: entries} - history only.
    target_local: naive local datetime at the top of the target hour.
    Returns a dict, or None if there is no history at all.
    """
    samples = []   # (value, weight, date)
    for w in range(1, weeks + 1):
        ts = target_local - timedelta(weeks=w)
        if ts in hourly:
            # most recent week weighs most: weights 1.0, 0.85, 0.72, ...
            samples.append((float(hourly[ts]), 0.85 ** (w - 1), ts))
    if not samples:
        return None

    values = [s[0] for s in samples]
    weights = [s[1] for s in samples]
    base = _weighted_mean(values, weights)
    std = _weighted_std(values, weights, base)
    if trend is None:
        trend = trend_factor(hourly, now_local)
    factor, recent, prev = trend
    predicted = max(0.0, base * factor)
    std_scaled = std * factor
    lower = max(0.0, predicted - Z_80 * std_scaled)
    upper = predicted + Z_80 * std_scaled

    n = len(samples)
    cv = (std / base) if base > 0 else (0.0 if std == 0 else 1.0)
    # Confidence: shrinks with high variability (cv) and few samples.
    sample_factor = min(1.0, n / float(weeks))
    confidence = 100.0 * max(0.0, 1.0 - min(cv, 1.0)) * (0.5 + 0.5 * sample_factor)
    if n < MIN_SAMPLES:
        confidence = min(confidence, 35.0)
    confidence = round(max(5.0, min(95.0, confidence)), 1)

    wd = target_local.strftime('%A')
    hh = target_local.strftime('%H:00')
    vals_txt = ', '.join(
        '%s: %d' % (s[2].strftime('%d %b'), int(s[0])) for s in samples)
    trend_pct = (factor - 1.0) * 100.0
    parts = [
        'Built from %d of the last %d %ss at %s -> [%s].' % (n, weeks, wd, hh, vals_txt),
        'Recency-weighted average %.1f entries, spread (std dev) %.1f, variability %.0f%%.' % (
            base, std, cv * 100.0),
        'Short-term trend factor x%.2f (%+.0f%%): last 7 days = %d entries vs previous 7 days = %d.' % (
            factor, trend_pct, int(recent), int(prev)),
        '80%% range %.0f-%.0f. Confidence %.0f%% (fewer samples and noisier history lower it).' % (
            lower, upper, confidence),
    ]
    if n < MIN_SAMPLES:
        parts.append('WARNING: only %d comparable week(s) of history - treat as a rough guess.' % n)
    return {
        'predicted': round(predicted, 1),
        'lower': round(lower, 1),
        'upper': round(upper, 1),
        'confidence': confidence,
        'sample_count': n,
        'evidence': '\n'.join(parts),
    }


def peak_hours(hourly, top=3, days=28, now_local=None):
    """Top `top` local hours-of-day by average entries over the last `days` days.
    Returns (list of (hour, avg_entries), n_days_with_data)."""
    if not hourly:
        return [], 0
    end = (now_local or max(hourly)).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days)
    by_hour, day_set = {}, set()
    for ts, v in hourly.items():
        if start <= ts <= end:
            by_hour.setdefault(ts.hour, []).append(v)
            day_set.add(ts.date())
    ranked = sorted(((h, sum(v) / len(v)) for h, v in by_hour.items()),
                    key=lambda x: x[1], reverse=True)
    return ranked[:top], len(day_set)


def confidence_from_days(n_days, target_days=28):
    """Simple data-sufficiency confidence for descriptive insights (not forecasts)."""
    if n_days <= 0:
        return 5.0
    return round(min(95.0, 30.0 + 65.0 * min(1.0, n_days / float(target_days))), 1)
