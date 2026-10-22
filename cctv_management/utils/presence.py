# -*- coding: utf-8 -*-
"""Pure (Odoo-free) presence / gap maths for employee monitoring.

All datetimes are naive UTC ``datetime`` objects. ``brk`` is an optional
``(break_start, break_end)`` tuple in the same representation; time inside it
is never counted as absence.
"""


def overlap_minutes(a1, a2, b1, b2):
    lo, hi = max(a1, b1), min(a2, b2)
    return max(0.0, (hi - lo).total_seconds() / 60.0)


def effective_minutes(a, b, brk=None):
    """Minutes between a and b, minus any overlap with the break window."""
    if b <= a:
        return 0.0
    total = (b - a).total_seconds() / 60.0
    if brk:
        total -= overlap_minutes(a, b, brk[0], brk[1])
    return max(0.0, total)


def analyze_presence(sightings, start, end, now, threshold, brk=None):
    """Analyse one shift.

    :param sightings: iterable of datetimes the employee was detected
    :param start/end: shift window
    :param now: current time (the analysed span is start .. min(now, end))
    :param threshold: minutes without detection that count as a *gap*
    :return: dict, see bottom of function
    """
    cap = min(now, end)
    pts = sorted(set(sightings))
    first = pts[0] if pts else None
    last = pts[-1] if pts else None

    res = {
        'first_seen': first, 'last_seen': last,
        'late_minutes': 0.0, 'early_minutes': 0.0,
        'gaps': [], 'gap_count': 0, 'total_gap_minutes': 0.0, 'longest_gap_minutes': 0.0,
        'open_gap_minutes': 0.0, 'basis_minutes': 0.0,
        'presence_minutes': 0.0, 'presence_rate': 0.0,
    }
    if cap <= start:
        return res

    basis = effective_minutes(start, cap, brk)
    res['basis_minutes'] = basis
    if first and first > start:
        res['late_minutes'] = (first - start).total_seconds() / 60.0

    inside = [min(max(p, start), cap) for p in pts if p <= cap]
    if not inside:
        res['open_gap_minutes'] = basis
        res['presence_minutes'] = 0.0
        return res

    gaps = []
    for a, b in zip(inside, inside[1:]):
        m = effective_minutes(a, b, brk)
        if m >= threshold:
            gaps.append((a, b, m))

    lead = effective_minutes(start, inside[0], brk)
    trailing = effective_minutes(inside[-1], cap, brk)
    shift_over = now >= end
    absent = lead + sum(g[2] for g in gaps)
    if shift_over or trailing >= threshold:
        absent += trailing

    if shift_over and last and last < end:
        res['early_minutes'] = (end - last).total_seconds() / 60.0

    presence = max(0.0, basis - absent)
    res.update({
        'gaps': gaps,
        'gap_count': len(gaps),
        'total_gap_minutes': sum(g[2] for g in gaps),
        'longest_gap_minutes': max((g[2] for g in gaps), default=0.0),
        'open_gap_minutes': 0.0 if shift_over else trailing,
        'presence_minutes': presence,
        'presence_rate': (presence / basis * 100.0) if basis else 0.0,
    })
    return res
