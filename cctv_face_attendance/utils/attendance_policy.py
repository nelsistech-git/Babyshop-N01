# -*- coding: utf-8 -*-
"""Pure-Python decision rules for face attendance (no Odoo imports, easy to unit test).

A *sighting* is "camera X confidently recognised employee Y at time T".  Whether that
turns into a check-in, a check-out or nothing depends on what the camera is for
(entry / exit / single door) and on the employee's current attendance state.

Why direction matters: an office camera sees the same person dozens of times a day.
If every sighting toggled in/out, hours would be wrong.  So an *entry* camera only
ever checks in, an *exit* camera only ever checks out, and only a *single-door*
camera toggles (with a minimum gap between toggles).
"""
from datetime import timedelta

CHECK_IN = 'check_in'
CHECK_OUT = 'check_out'
CLOSE_STALE_AND_CHECK_IN = 'close_stale_check_in'
IGNORE = 'ignore'

ACCEPT = 'accept'
REVIEW = 'review'
REJECT = 'reject'


def classify_confidence(confidence, min_confidence, review_confidence):
    """accept -> punch automatically; review -> HR approves; reject -> not good enough."""
    if confidence is None:
        return REJECT
    if confidence >= min_confidence:
        return ACCEPT
    if confidence >= review_confidence:
        return REVIEW
    return REJECT


def normalize_time(when, now, max_age_minutes=30, max_future_seconds=60):
    """Return (time_to_use, is_old).

    * missing / in the future (clock skew) -> `now`
    * older than max_age_minutes (spooled while offline) -> kept, but flagged old so the
      punch goes to HR review instead of silently rewriting history.
    """
    if when is None:
        return now, False
    if when > now + timedelta(seconds=max_future_seconds):
        return now, False
    if max_age_minutes and (now - when) > timedelta(minutes=max_age_minutes):
        return when, True
    return when, False


def decide(direction, is_checked_in, check_in_time, last_punch_time, when, *,
           min_gap_seconds=60, min_stay_minutes=5, both_gap_minutes=10, stale_open_hours=16):
    """Decide what a sighting at `when` does.  Returns (action, reason).

    direction       'in' | 'out' | 'both'
    is_checked_in   employee has an open attendance (no check-out)
    check_in_time   check-in of that open attendance (or None)
    last_punch_time latest check-in / check-out time of the employee (or None)
    """
    if direction not in ('in', 'out', 'both'):
        return IGNORE, 'camera has no attendance role'

    # a punch older than what is already recorded must never rewrite history
    if last_punch_time and when <= last_punch_time:
        return IGNORE, 'older than the last recorded attendance'

    # open attendance that is far too old = the employee forgot to check out
    if is_checked_in and check_in_time and stale_open_hours \
            and (when - check_in_time) > timedelta(hours=stale_open_hours):
        if direction in ('in', 'both'):
            return CLOSE_STALE_AND_CHECK_IN, 'previous attendance was never closed (%sh+)' % stale_open_hours
        return IGNORE, 'open attendance is too old to close from an exit camera'

    if last_punch_time and (when - last_punch_time).total_seconds() < min_gap_seconds:
        return IGNORE, 'too soon after the previous punch'

    if direction == 'in':
        if is_checked_in:
            return IGNORE, 'already checked in'
        return CHECK_IN, 'entry camera'

    if direction == 'out':
        if not is_checked_in:
            return IGNORE, 'not checked in'
        if check_in_time and (when - check_in_time) < timedelta(minutes=min_stay_minutes):
            return IGNORE, 'too soon after check-in'
        return CHECK_OUT, 'exit camera'

    # single door: toggle, with a minimum gap so one walk through the door is one punch
    if last_punch_time and (when - last_punch_time) < timedelta(minutes=both_gap_minutes):
        return IGNORE, 'too soon after the previous punch (single-door camera)'
    return (CHECK_OUT, 'single-door camera') if is_checked_in else (CHECK_IN, 'single-door camera')
