"""Pure-python simulation of a field team's days around Dhaka (no Odoo imports, so it can be unit-tested).

Everything is deterministic for a given `random.Random` seed. Times handed in / out are naive UTC datetimes;
the story itself is written in Asia/Dhaka local time (UTC+6, no DST).
"""
import math
from datetime import datetime, timedelta

import pytz

TZ = pytz.timezone('Asia/Dhaka')
UTC = pytz.UTC
ROAD_FACTOR = 1.3
CITY_KMH = 18.0

# name, lat, lng, radius_m, address
SITES = [
    ('Nelsis HQ - Gulshan', 23.7925, 90.4078, 150, 'Gulshan Avenue, Gulshan-2, Dhaka'),
    ('Motijheel Branch', 23.7330, 90.4172, 120, 'Dilkusha C/A, Motijheel, Dhaka'),
    ('Tejgaon Warehouse', 23.7640, 90.3920, 200, 'Tejgaon Industrial Area, Dhaka'),
    ('Uttara Service Point', 23.8759, 90.3795, 120, 'Sector 7, Uttara, Dhaka'),
    ('Narayanganj Factory', 23.6238, 90.5000, 250, 'Fatullah, Narayanganj'),
]

# customer / visit places: name, lat, lng, address
PLACES = [
    ('Mirpur-10 Market', 23.8069, 90.3687, 'Mirpur-10 Circle, Dhaka'),
    ('Dhanmondi 27', 23.7561, 90.3733, 'Road 27, Dhanmondi, Dhaka'),
    ('Farmgate Bazar', 23.7561, 90.3872, 'Farmgate, Tejgaon, Dhaka'),
    ('Mohakhali Wireless Gate', 23.7781, 90.4005, 'Mohakhali, Dhaka'),
    ('Badda Link Road', 23.7806, 90.4261, 'Link Road, Badda, Dhaka'),
    ('Malibagh Rail Gate', 23.7497, 90.4126, 'Malibagh, Dhaka'),
    ('Jatrabari Crossing', 23.7104, 90.4344, 'Jatrabari, Dhaka'),
    ('Mohammadpur Town Hall', 23.7662, 90.3584, 'Town Hall, Mohammadpur, Dhaka'),
    ('Kawran Bazar', 23.7506, 90.3934, 'Kawran Bazar, Dhaka'),
    ('Pallabi Mirpur-12', 23.8281, 90.3655, 'Pallabi, Mirpur-12, Dhaka'),
    ('Khilgaon Taltola', 23.7488, 90.4283, 'Taltola, Khilgaon, Dhaka'),
    ('Shyamoli Square', 23.7745, 90.3655, 'Shyamoli, Dhaka'),
]
FAR_PLACES = [
    ('Savar Bazar Stand', 23.8583, 90.2667, 'Savar Bus Stand, Savar'),
    ('Gazipur Chowrasta', 23.9999, 90.4203, 'Chowrasta, Gazipur'),
]

RESTAURANTS = ['Star Kabab', 'Haji Biryani', 'Kacchi Bhai', "Sultan's Dine", "Nando's Gulshan", 'Pizza Inn',
               'Fakruddin Biryani', 'Cafe Rio', 'Takeout Banani', 'Madchef']
OTHER_COSTS = [('Courier charge', 'SA Paribahan Courier'), ('Photocopy & printing', 'Print Corner'),
               ('Parking fee', 'Dhaka City Parking'), ('Mobile recharge for client calls', 'Grameenphone'),
               ('Sample packaging', 'Packaging House'), ('Toll fee', 'Bridge Authority')]

# login, name, department, job, field staff?, base site index, phone
EMPLOYEES = [
    ('demo.manager', 'Tanvir Ahmed', 'Management', 'Operations Manager', False, 0, '01711000001'),
    ('demo.rahim', 'Rahim Uddin', 'Sales', 'Sales Executive', True, 0, '01711000002'),
    ('demo.karim', 'Karim Hossain', 'Sales', 'Sales Executive', True, 1, '01711000003'),
    ('demo.nusrat', 'Nusrat Jahan', 'Sales', 'Senior Sales Officer', False, 0, '01711000004'),
    ('demo.sabbir', 'Sabbir Rahman', 'Field Operations', 'Field Technician', True, 2, '01711000005'),
    ('demo.mahmud', 'Mahmudul Hasan', 'Field Operations', 'Field Supervisor', True, 2, '01711000006'),
    ('demo.farhana', 'Farhana Akter', 'Collections', 'Collection Officer', True, 1, '01711000007'),
    ('demo.jamal', 'Jamal Chowdhury', 'Collections', 'Collection Executive', True, 1, '01711000008'),
    ('demo.shirin', 'Shirin Sultana', 'Accounts', 'Accounts Officer', False, 0, '01711000009'),
    ('demo.imran', 'Imran Khan', 'Field Operations', 'Delivery Officer', True, 3, '01711000010'),
    ('demo.tasnim', 'Tasnim Rahman', 'Sales', 'Sales Officer', True, 0, '01711000011'),
    ('demo.mannan', 'Abdul Mannan', 'Warehouse', 'Store Keeper', False, 2, '01711000012'),
]
MANAGER_LOGIN = 'demo.manager'
DEVICES = [('Samsung Galaxy A54', 'android', '1.0.0'), ('Xiaomi Redmi Note 12', 'android', '1.0.0'),
           ('iPhone 13', 'ios', '1.0.1'), ('Realme C55', 'android', '1.0.1'), ('Google Pixel 6a', 'android', '1.0.1'),
           ('Samsung Galaxy M34', 'android', '1.0.0')]

# story: which login has which problem on which day offset (0 = today, 1 = yesterday ...)
MOCK_DAYS = {'demo.imran': {2, 6}}
DRIFT_DAYS = {'demo.jamal': {3}}
JUMP_DAYS = {'demo.farhana': {4}}
OFFLINE_DAYS = {'demo.mahmud': {1, 3, 7}}
OUTSIDE_DAYS = {'demo.shirin': {5}}
OFFLINE_PUNCH_DAYS = {'demo.mahmud': {1}}
FAR_TRIP_DAYS = {'demo.rahim': {2}, 'demo.karim': {6}}
ABSENT_TODAY = {'demo.karim'}
LATE_LOGINS = {'demo.tasnim'}
SIGNAL_LOST_NOW = {'demo.sabbir'}
STORY_TABLES = (MOCK_DAYS, DRIFT_DAYS, JUMP_DAYS, OFFLINE_DAYS, OUTSIDE_DAYS, FAR_TRIP_DAYS)


def haversine_m(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371008.8 * math.asin(min(1.0, math.sqrt(a)))


def bearing(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def to_utc(local_naive):
    return TZ.localize(local_naive).astimezone(UTC).replace(tzinfo=None)


def to_local(utc_naive):
    return UTC.localize(utc_naive).astimezone(TZ).replace(tzinfo=None)


def _jitter(rnd, lat, lng, metres):
    dlat = rnd.gauss(0, metres) / 111000.0
    dlng = rnd.gauss(0, metres) / (111000.0 * math.cos(math.radians(lat)))
    return lat + dlat, lng + dlng


def _segments(t0, t1, stops, weights):
    """[(start, end, from_xy, to_xy)] - stationary dwell segments and travel legs between the stops."""
    legs = [haversine_m(stops[i][0], stops[i][1], stops[i + 1][0], stops[i + 1][1]) * ROAD_FACTOR / 1000.0
            for i in range(len(stops) - 1)]
    travel = [max(km / CITY_KMH * 60.0, 4.0) for km in legs]
    window = (t1 - t0).total_seconds() / 60.0
    tt = sum(travel)
    if tt > window * 0.75:
        f = window * 0.75 / tt
        travel = [x * f for x in travel]
        tt = window * 0.75
    dwell_total = window - tt
    wsum = sum(weights) or 1.0
    segs, t = [], t0
    for i, st in enumerate(stops):
        d = dwell_total * weights[i] / wsum
        if d > 0:
            segs.append((t, t + timedelta(minutes=d), st, st))
            t += timedelta(minutes=d)
        if i < len(stops) - 1:
            segs.append((t, t + timedelta(minutes=travel[i]), st, stops[i + 1]))
            t += timedelta(minutes=travel[i])
    return segs


def _pos(segs, t):
    for a, b, p, q in segs:
        if a <= t <= b:
            if p == q:
                return p, 0.0
            f = (t - a).total_seconds() / max((b - a).total_seconds(), 1.0)
            km = haversine_m(p[0], p[1], q[0], q[1]) * ROAD_FACTOR / 1000.0
            hours = max((b - a).total_seconds() / 3600.0, 0.01)
            return (p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f), min(km / hours, 45.0)
    return segs[-1][3], 0.0


def _clip(rnd, mean, sd, lo, hi):
    return max(lo, min(hi, rnd.gauss(mean, sd)))


def build_day(rnd, spec, day, offset, now_utc):
    """Simulate one working day for one employee. `day` is a local date, `offset` = days back from today.
    Returns None when the person is absent / not there yet, otherwise a dict describing the attendance,
    the GPS points, the online/offline events and the places visited."""
    login, field, base_idx = spec[0], spec[4], spec[5]
    wd = day.weekday()          # Fri = 4, Sat = 5
    if wd == 4 or (wd == 5 and not field):
        return None
    story = any(offset in t.get(login, ()) for t in STORY_TABLES)
    if offset == 0 and login in ABSENT_TODAY:
        return None
    if not story and rnd.random() < 0.08:
        return None
    base = SITES[base_idx]
    now_l = to_local(now_utc)
    midnight = datetime.combine(day, datetime.min.time())

    # ---- schedule (local time)
    if login in LATE_LOGINS:
        tin = midnight + timedelta(hours=10, minutes=rnd.randint(5, 50))
    elif field:
        tin = midnight + timedelta(hours=8, minutes=int(_clip(rnd, 50, 22, 15, 85)))
    else:
        tin = midnight + timedelta(hours=9, minutes=int(_clip(rnd, 0, 14, -25, 30)))
    tout = midnight + timedelta(hours=18 if field else 17, minutes=int(_clip(rnd, 0 if field else 30, 28, -40, 60)))
    if offset == 0 and tin >= now_l - timedelta(minutes=25):
        return None                                  # has not arrived yet
    open_now = offset == 0 and tout > now_l
    end_l = tout
    cutoff = None
    if open_now:
        end_l = now_l - timedelta(minutes=rnd.randint(1, 3))
        if login in SIGNAL_LOST_NOW:
            end_l = now_l - timedelta(minutes=rnd.randint(38, 48))
            cutoff = end_l
        if end_l < tin + timedelta(minutes=20):
            return None

    # ---- the route
    base_xy = (base[1], base[2])
    if field:
        pool = list(PLACES)
        rnd.shuffle(pool)
        visits = pool[:rnd.randint(2, 4)]
        if offset in FAR_TRIP_DAYS.get(login, ()):
            visits = [rnd.choice(FAR_PLACES)] + visits[:1]
        stops = [base_xy] + [(v[1], v[2]) for v in visits] + [base_xy]
        weights = [0.08] + [1.0] * len(visits) + [0.1]
    else:
        lunch = (base[1] + 0.0021, base[2] + 0.0013)
        stops = [base_xy, lunch, base_xy]
        weights = [0.55, 0.08, 0.37]
        visits = [('Lunch break', lunch[0], lunch[1], 'near ' + base[0])]
    segs = _segments(tin, tout, stops, weights)

    # ---- sample times
    times = [tin]
    t = tin
    lo, hi = (11, 18) if field else (25, 35)
    while True:
        t = t + timedelta(minutes=rnd.randint(lo, hi))
        if t >= end_l:
            break
        times.append(t)
    closed = not open_now
    times.append(tout if closed else end_l)
    if len(times) < 3:
        return None

    mock_day = offset in MOCK_DAYS.get(login, ())
    drift_day = offset in DRIFT_DAYS.get(login, ())
    jump_day = offset in JUMP_DAYS.get(login, ())
    off_day = offset in OFFLINE_DAYS.get(login, ())
    off_from = midnight + timedelta(hours=12)
    off_to = midnight + timedelta(hours=13, minutes=30)
    sync_back = off_to + timedelta(minutes=10 + rnd.randint(0, 4))
    batt = rnd.randint(82, 100)
    pts = []
    for i, tl in enumerate(times):
        (lat, lng), speed = _pos(segs, tl)
        lat, lng = _jitter(rnd, lat, lng, 3.0 if speed == 0.0 else 9.0)
        acc = round(rnd.uniform(4, 28), 1)
        if rnd.random() < 0.03:
            acc = round(rnd.uniform(110, 160), 1)       # occasional poor fix -> "Low accuracy" KPI
        src = 'punch_in' if i == 0 else ('punch_out' if (closed and i == len(times) - 1) else 'auto')
        dev = to_utc(tl)
        srv = dev + timedelta(seconds=rnd.randint(2, 14))
        mock = False
        if mock_day and (i == 0 or rnd.random() < 0.35):
            mock, acc = True, 1.0
        if drift_day and tl.hour >= 14:
            srv = dev - timedelta(minutes=22)            # phone clock ahead of the server -> "Clock mismatch"
        if off_day and off_from <= tl <= off_to:
            srv = to_utc(sync_back) + timedelta(seconds=rnd.randint(0, 40))   # captured offline, synced later
        pts.append({'dt_local': tl, 'device_time': dev, 'server_time': srv, 'lat': lat, 'lng': lng,
                    'accuracy': acc, 'speed_kmh': round(speed, 1), 'source': src, 'mock': mock, 'teleport': False})
    if offset in OUTSIDE_DAYS.get(login, ()):
        # punched in ~650 m from the site (office worker, not field staff) -> "Outside work site"
        pts[0]['lat'], pts[0]['lng'] = base[1] + 0.0059, base[2]
    if jump_day and len(pts) > 6:
        k = int(len(pts) * 0.6)
        pts[k]['lat'], pts[k]['lng'] = 23.6238, 90.5000      # 25+ km away, minutes after the previous fix
        pts[k]['teleport'] = True
        pts[k + 1]['teleport'] = True

    # ---- battery, heading, distance (same rules as the server's ingest())
    prev = None
    for p in pts:
        hrs = (p['dt_local'] - tin).total_seconds() / 3600.0
        p['battery'] = int(max(8, batt - hrs * rnd.uniform(4.5, 8.5)))
        dist = 0.0
        p['heading'] = 0.0
        if prev:
            gap = (p['device_time'] - prev['device_time']).total_seconds() / 60.0
            p['heading'] = round(bearing(prev['lat'], prev['lng'], p['lat'], p['lng']), 0)
            if 0 < gap <= 30:
                dist = haversine_m(prev['lat'], prev['lng'], p['lat'], p['lng'])
                if dist < 8:
                    dist = 0.0
        p['distance_m'] = round(dist, 1)
        p['address'] = base[4] if p['source'] != 'auto' else False
        prev = p

    first, last = pts[0], pts[-1]
    in_dist = round(haversine_m(first['lat'], first['lng'], base[1], base[2]), 1)
    in_site = (not field) and in_dist <= base[3]

    # ---- presence (online / offline) events
    pres = [('online', 'login', first['device_time'])]
    if off_day:
        inside = [p for p in pts if off_from <= p['dt_local'] <= off_to]
        if inside:
            pres.append(('offline', 'signal_lost', inside[0]['device_time']))
            pres.append(('online', 'app', to_utc(sync_back)))
    elif rnd.random() < 0.35 and len(pts) > 8:
        a = midnight + timedelta(hours=12, minutes=rnd.randint(5, 40))
        if a < end_l - timedelta(hours=1):
            pres.append(('offline', 'app', to_utc(a)))
            pres.append(('online', 'app', to_utc(a + timedelta(minutes=rnd.randint(6, 25)))))
    if cutoff:
        pres.append(('offline', 'signal_lost', to_utc(cutoff)))
    if closed:
        pres.append(('offline', 'logout', last['device_time']))

    return {
        'day': day, 'offset': offset, 'closed': closed,
        'check_in': first['device_time'], 'check_out': last['device_time'] if closed else None,
        'in_pos': (first['lat'], first['lng']), 'out_pos': (last['lat'], last['lng']),
        'in_acc': first['accuracy'], 'out_acc': last['accuracy'],
        'mock_in': first['mock'], 'mock_out': bool(last['mock'] and closed),
        'offline_in': offset in OFFLINE_PUNCH_DAYS.get(login, ()), 'in_site': in_site, 'in_dist': in_dist,
        'base_idx': base_idx, 'visits': visits, 'points': pts, 'presence': pres,
        'km': round(sum(p['distance_m'] for p in pts) / 1000.0, 2),
    }
