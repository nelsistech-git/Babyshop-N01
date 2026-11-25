import base64
import hashlib
import io
import logging
import random
import secrets
from datetime import timedelta

from odoo import api, fields, models

from . import sim

_logger = logging.getLogger(__name__)

MODULE = 'nelsis_field_demo'
PREFIX = 'demo_rec_'
PASSWORD = 'demo1234'
SEED = 20261118
DAYS_BACK = 14

# deletion order (children first)
REMOVE_ORDER = [
    'nelsis.ai.insight', 'conveyance.sheet', 'employee.advance.adjustment', 'employee.advance',
    'nelsis.location.log', 'nelsis.presence.log', 'hr.attendance', 'nelsis.announcement', 'nelsis.api.token',
    'nelsis.work.site', 'hr.employee', 'res.users', 'res.partner', 'hr.job', 'hr.department',
]


class NelsisDemoGenerator(models.AbstractModel):
    _name = 'nelsis.demo.generator'
    _description = 'Nelsis demo data generator'

    # ------------------------------------------------------------------ bookkeeping
    @api.model
    def _reg(self, recs):
        """Remember a record as demo data (so it can be removed again, and is dropped on module uninstall)."""
        imd = self.env['ir.model.data'].sudo()
        imd.create([{
            'module': MODULE, 'name': '%s%s_%s' % (PREFIX, r._name.replace('.', '_'), r.id),
            'model': r._name, 'res_id': r.id, 'noupdate': True,
        } for r in recs])
        return recs

    @api.model
    def _reg_once(self, rec):
        if rec and rec.exists() and not self._is_registered(rec):
            self._reg(rec)
        return rec

    @api.model
    def _is_registered(self, rec):
        return bool(self.env['ir.model.data'].sudo().search_count([
            ('module', '=', MODULE), ('model', '=', rec._name), ('res_id', '=', rec.id)]))

    @api.model
    def demo_exists(self):
        return bool(self.env['ir.model.data'].sudo().search_count(
            [('module', '=', MODULE), ('name', '=like', PREFIX + '%')]))

    @api.model
    def counts(self):
        data = self.env['ir.model.data'].sudo()._read_group(
            [('module', '=', MODULE), ('name', '=like', PREFIX + '%')], ['model'], ['__count'])
        return {m: c for m, c in data}

    # ------------------------------------------------------------------ remove
    @api.model
    def remove_all(self):
        imd = self.env['ir.model.data'].sudo()
        rows = imd.search_read([('module', '=', MODULE), ('name', '=like', PREFIX + '%')], ['model', 'res_id'])
        by_model = {}
        for r in rows:
            by_model.setdefault(r['model'], []).append(r['res_id'])
        order = [m for m in REMOVE_ORDER if m in by_model] + [m for m in by_model if m not in REMOVE_ORDER]
        removed, failed = 0, []
        for model in order:
            if model not in self.env:
                continue
            recs = self.env[model].sudo().with_context(active_test=False).browse(by_model[model]).exists()
            try:
                with self.env.cr.savepoint():
                    if model == 'conveyance.sheet' and 'state' in recs._fields:
                        recs.write({'state': 'draft'})
                    if model == 'employee.advance' and 'state' in recs._fields:
                        recs.write({'state': 'draft'})
                    recs.unlink()
                removed += len(recs)
            except Exception as e:  # noqa: BLE001
                _logger.warning('demo remove %s failed: %s', model, e)
                failed.append('%s (%s)' % (model, str(e).splitlines()[0][:80]))
        # anything left behind (e.g. a user that could not be deleted) is archived instead
        left = imd.search([('module', '=', MODULE), ('name', '=like', PREFIX + '%')])
        for r in left:
            rec = self.env[r.model].sudo().with_context(active_test=False).browse(r.res_id).exists() \
                if r.model in self.env else None
            if rec and 'active' in rec._fields:
                rec.write({'active': False})
        left.unlink()
        return removed, failed

    # ------------------------------------------------------------------ generate
    @api.model
    def generate(self):
        """Create the whole demo story. Returns a list of human-readable notes."""
        notes = []
        rnd = random.Random(SEED)
        now = fields.Datetime.now()
        today = sim.to_local(now).date()
        ctx = {'rnd': rnd, 'now': now, 'today': today, 'emps': {}, 'users': {}, 'days': {}, 'sites': [], 'notes': notes}
        steps = [
            ('Work sites', self._gen_sites),
            ('Employees & users', self._gen_employees),
            ('Attendance & GPS tracks', self._gen_tracks),
            ('Announcements', self._gen_announcements),
            ('App devices', self._gen_devices),
            ('Expense claims', self._gen_expenses),
            ('Employee advances', self._gen_advances),
            ('AI insights', self._gen_insights),
        ]
        for title, fn in steps:
            try:
                with self.env.cr.savepoint():
                    msg = fn(ctx)
                notes.append('OK    %s%s' % (title, (' - ' + msg) if msg else ''))
            except Exception as e:  # noqa: BLE001
                _logger.exception('demo data step "%s" failed', title)
                notes.append('SKIP  %s - %s' % (title, str(e).strip().splitlines()[-1][:160] if str(e).strip() else e))
                if title in ('Work sites', 'Employees & users'):
                    break
        return notes

    # ------------------------------------------------------------------ steps
    def _get_or_create(self, model, domain, vals):
        Model = self.env[model].sudo()
        rec = Model.search(domain, limit=1)
        if rec:
            return rec
        rec = Model.create(vals)
        self._reg(rec)
        return rec

    def _gen_sites(self, ctx):
        Site = self.env['nelsis.work.site'].sudo()
        for name, lat, lng, radius, addr in sim.SITES:
            rec = Site.create({'name': name, 'latitude': lat, 'longitude': lng, 'radius_m': radius, 'address': addr})
            self._reg(rec)
            ctx['sites'].append(rec)
        return '%d work sites around Dhaka' % len(ctx['sites'])

    def _gen_employees(self, ctx):
        env = self.env
        g_user = env.ref('nelsis_field_tracking.group_nelsis_user')
        g_mgr = env.ref('nelsis_field_tracking.group_nelsis_manager')
        Users = env['res.users'].sudo().with_context(no_reset_password=True, mail_create_nolog=True,
                                                     mail_notrack=True, tracking_disable=True)
        Emp = env['hr.employee'].sudo()
        created = 0
        for i, (login, name, dept, job, field, base_idx, phone) in enumerate(sim.EMPLOYEES):
            d = self._get_or_create('hr.department', [('name', '=', dept)], {'name': dept})
            j = self._get_or_create('hr.job', [('name', '=', job)], {'name': job})
            grp = g_mgr if login == sim.MANAGER_LOGIN else g_user
            gids = (grp | grp.trans_implied_ids).ids
            user = Users.create({
                'name': name, 'login': login, 'password': PASSWORD, 'email': '%s@demo.nelsis.local' % login,
                'tz': 'Asia/Dhaka', 'groups_id': [(6, 0, gids)],
            })
            self._reg(user)
            emp = Emp.search([('user_id', '=', user.id)], limit=1)     # hr may have auto-created it
            vals = {
                'name': name, 'user_id': user.id, 'department_id': d.id, 'job_id': j.id, 'job_title': job,
                'work_email': user.email, 'mobile_phone': phone, 'tz': 'Asia/Dhaka',
                'nl_field_staff': bool(field), 'nl_tracking_enabled': True,
                'nl_last_app_version': sim.DEVICES[i % len(sim.DEVICES)][2],
            }
            if emp:
                emp.write(vals)
            else:
                emp = Emp.create(vals)
            self._reg(emp)
            self._reg_once(user.partner_id)           # contact cards of the demo people go with them
            self._reg_once(emp.work_contact_id if 'work_contact_id' in emp._fields else False)
            ctx['emps'][login] = emp
            ctx['users'][login] = user
            created += 1
        # department managers (nice org chart)
        mgr = ctx['emps'][sim.MANAGER_LOGIN]
        for login, emp in ctx['emps'].items():
            if login != sim.MANAGER_LOGIN:
                emp.write({'parent_id': mgr.id, 'coach_id': mgr.id})
        return '%d users / employees (password %s)' % (created, PASSWORD)

    # ---- tracks
    @staticmethod
    def _selfie(initials, seed):
        try:
            from PIL import Image, ImageDraw
            rnd = random.Random(seed)
            col = (rnd.randint(60, 160), rnd.randint(60, 160), rnd.randint(120, 220))
            im = Image.new('RGB', (256, 256), col)
            dr = ImageDraw.Draw(im)
            dr.ellipse((78, 40, 178, 140), fill=(245, 224, 205))
            dr.ellipse((38, 150, 218, 330), fill=(245, 224, 205))
            dr.text((106, 82), initials, fill=(60, 40, 30))
            out = io.BytesIO()
            im.save(out, 'JPEG', quality=70)
            return base64.b64encode(out.getvalue())
        except Exception:  # noqa: BLE001
            return False

    def _gen_tracks(self, ctx):
        env = self.env
        Att, Log, Pres = env['hr.attendance'].sudo(), env['nelsis.location.log'].sudo(), env['nelsis.presence.log'].sudo()
        n_att = n_log = n_pres = 0
        rnd, now, today = ctx['rnd'], ctx['now'], ctx['today']
        for spec in sim.EMPLOYEES:
            login = spec[0]
            emp = ctx['emps'][login]
            site_rec = ctx['sites']
            last_day = None
            for off in range(DAYS_BACK - 1, -1, -1):
                day = today - timedelta(days=off)
                d = sim.build_day(rnd, spec, day, off, now)
                if not d:
                    continue
                base = site_rec[d['base_idx']]
                vals = {
                    'employee_id': emp.id, 'check_in': d['check_in'], 'check_out': d['check_out'] or False,
                    'in_latitude': d['in_pos'][0], 'in_longitude': d['in_pos'][1], 'nl_in_accuracy': d['in_acc'],
                    'nl_in_mock': d['mock_in'], 'nl_in_offline': d['offline_in'], 'nl_in_device_time': d['check_in'],
                    'nl_in_trust': 'delayed' if d['offline_in'] else 'ok',
                    'nl_in_site_id': base.id if d['in_site'] else False, 'nl_in_distance_m': d['in_dist'],
                    'nl_in_address': base.address, 'nl_in_uuid': 'demo-in-%s-%s' % (emp.id, day),
                    'nl_in_photo': self._selfie(''.join(w[0] for w in emp.name.split()[:2]), emp.id * 1000 + off),
                }
                if d['check_out']:
                    vals.update({
                        'out_latitude': d['out_pos'][0], 'out_longitude': d['out_pos'][1],
                        'nl_out_accuracy': d['out_acc'], 'nl_out_mock': d['mock_out'],
                        'nl_out_device_time': d['check_out'], 'nl_out_trust': 'ok',
                        'nl_out_site_id': base.id if d['in_site'] else False,
                        'nl_out_distance_m': round(sim.haversine_m(d['out_pos'][0], d['out_pos'][1],
                                                                   base.latitude, base.longitude), 1),
                        'nl_out_address': base.address, 'nl_out_uuid': 'demo-out-%s-%s' % (emp.id, day),
                    })
                att = Att.create(vals)
                self._reg(att)
                n_att += 1
                logs = Log.create([{
                    'employee_id': emp.id, 'latitude': p['lat'], 'longitude': p['lng'], 'accuracy': p['accuracy'],
                    'speed_kmh': p['speed_kmh'], 'heading': p['heading'], 'battery': p['battery'],
                    'source': p['source'], 'device_time': p['device_time'], 'server_time': p['server_time'],
                    'is_mock': p['mock'], 'is_teleport': p['teleport'], 'distance_m': p['distance_m'],
                    'address': p['address'], 'attendance_id': att.id,
                } for p in d['points']])
                self._reg(logs)
                n_log += len(logs)
                pres = Pres.create([{
                    'employee_id': emp.id, 'state': s, 'kind': k, 'device_time': t,
                    'server_time': t + timedelta(seconds=rnd.randint(2, 20)),
                } for s, k, t in d['presence']])
                self._reg(pres)
                n_pres += len(pres)
                last_day = d
                ctx['days'].setdefault(login, {})[day] = d
            # live position for the map / dashboard (last fix of the latest day)
            if last_day:
                lp = last_day['points'][-1]
                emp.write({
                    'nl_last_lat': lp['lat'], 'nl_last_lng': lp['lng'], 'nl_last_accuracy': lp['accuracy'],
                    'nl_last_battery': lp['battery'], 'nl_last_device_time': lp['device_time'],
                    'nl_last_sync': lp['server_time'],
                })
        return '%d attendances, %d GPS points, %d online/offline events (last %d days)' % (
            n_att, n_log, n_pres, DAYS_BACK)

    def _gen_announcements(self, ctx):
        now = ctx['now']
        mgr_user = ctx['users'][sim.MANAGER_LOGIN]
        sales = self.env['hr.department'].sudo().search([('name', '=', 'Sales')], limit=1)
        items = [
            ('Eid-ul-Adha office schedule', 'Dear team, the office will be closed from 10 June to 14 June. '
             'Field staff: please punch out before leaving and punch in on the first working day.',
             'all', False, now - timedelta(days=5), False, 'sent'),
            ('Submit TA/DA bills by the 25th', 'Please submit all TA/DA claims for this month with clear, scanned '
             'bills before the 25th. Use "Scan bill" in the app so receipts are cropped and readable.',
             'all', False, now - timedelta(days=1), now + timedelta(days=10), 'sent'),
            ('Sales team: client visit report', 'Sales team - add the customer name in the purpose field of every '
             'trip line from today. Food and Other expenses can now be added as separate lines.',
             'department', sales, now - timedelta(hours=3), False, 'sent'),
            ('App update 1.0.1 available', 'A new version of the Nelsis Expense app is ready. Please update from '
             'the store this week.', 'all', False, False, False, 'draft'),
        ]
        for name, body, aud, dept, sent, exp, state in items:
            rec = self.env['nelsis.announcement'].sudo().create({
                'name': name, 'body': body, 'audience': aud,
                'department_ids': [(6, 0, dept.ids)] if dept else False,
                'state': state, 'sent_date': sent or False, 'sent_by_id': mgr_user.id if sent else False,
                'expire_date': exp or False, 'push_state': 'skipped' if state == 'sent' else 'none',
            })
            self._reg(rec)
        return '%d announcements (3 sent, 1 draft)' % len(items)

    def _gen_devices(self, ctx):
        Tok = self.env['nelsis.api.token'].sudo()
        n = 0
        for i, (login, user) in enumerate(ctx['users'].items()):
            name, plat, ver = sim.DEVICES[i % len(sim.DEVICES)]
            emp = ctx['emps'][login]
            rec = Tok.create({
                'user_id': user.id, 'token_hash': hashlib.sha256(secrets.token_bytes(16)).hexdigest(),
                'device_uid': 'demo-device-%d' % (i + 1), 'device_name': name, 'platform': plat, 'app_version': ver,
                'last_ip': '192.168.1.%d' % (20 + i), 'last_used': emp.nl_last_sync or ctx['now'],
                'expires_at': ctx['now'] + timedelta(days=30),
            })
            self._reg(rec)
            n += 1
        return '%d app devices (tokens are random - nobody can use them to sign in)' % n

    # ---- expenses
    @staticmethod
    def _receipt(rnd, shop, amount, day, ref):
        from PIL import Image, ImageDraw, ImageFont
        w, h = 480, 640
        im = Image.new('RGB', (w, h), (250, 249, 245))
        dr = ImageDraw.Draw(im)
        # a 9x8 grid of random paper tones: the server's duplicate-bill hash is a 9x8 difference hash, so
        # every demo receipt gets its own fingerprint (only the deliberate duplicate re-uses the same bytes)
        cw, ch = w / 9.0, h / 8.0
        for r in range(8):
            for c in range(9):
                g = rnd.randint(165, 252)
                dr.rectangle((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch), fill=(g, g - rnd.randint(0, 8), g - rnd.randint(0, 18)))
        try:
            dr.font = ImageFont.load_default(size=17)     # readable text on Pillow >= 10.1
        except TypeError:
            pass
        y = 40
        for line, big in [(shop.upper(), True), ('Dhaka, Bangladesh', False), ('-' * 34, False),
                          ('DATE: %s' % day, False), ('BILL NO: %s' % ref, False), ('-' * 34, False)]:
            dr.text((40, y), line, fill=(20, 20, 20))
            y += 32 if big else 26
        items = max(2, min(5, int(amount // 90) + 1))
        part = round(amount / items, 0)
        for k in range(items):
            dr.text((40, y), 'Item %d' % (k + 1), fill=(40, 40, 40))
            dr.text((330, y), 'BDT %6.0f' % part, fill=(40, 40, 40))
            y += 30
        y += 16
        dr.text((40, y), '-' * 34, fill=(20, 20, 20))
        dr.text((40, y + 24), 'TOTAL', fill=(0, 0, 0))
        dr.text((330, y + 24), 'BDT %6.0f' % amount, fill=(0, 0, 0))
        dr.text((40, y + 64), 'DEMO RECEIPT - NOT A REAL BILL', fill=(150, 20, 20))
        out = io.BytesIO()
        im.save(out, 'JPEG', quality=80)
        return out.getvalue()

    def _expense_lines(self, ctx, login, categ, kinds, days_used, same_bill=None):
        """Lines for one claim. kinds: list of 'travel' | 'food' | 'other'. Uses days the employee really worked."""
        rnd = ctx['rnd']
        worked = [dd for dd in sorted(ctx['days'].get(login, {})) if dd not in days_used]
        lines = []
        for kind in kinds:
            if not worked:
                break
            day = worked.pop(rnd.randrange(len(worked)))
            days_used.add(day)
            info = ctx['days'][login][day]
            if kind == 'travel':
                km = info['km']
                if km < 1.0:
                    kind = 'food'
            if kind == 'travel':
                visit = info['visits'][0]
                base = sim.SITES[info['base_idx']]
                claimed = round(km * rnd.uniform(0.85, 1.0), 1)
                transport = rnd.choice(['rickshaw', 'cng', 'uber', 'bus', 'pathao'])
                conv = round(max(claimed * rnd.uniform(11, 17), 60) / 10.0) * 10
                lines.append({
                    'kind': kind, 'date': day, 'from_location': base[0], 'to_location': visit[0],
                    'purpose': 'Client visit - %s' % visit[0], 'transport': transport,
                    'conveyance_amount': conv, 'food_bill': 0.0, 'amount': 0.0, 'nl_claimed_km': claimed,
                    'nl_from_lat': base[1], 'nl_from_lng': base[2], 'nl_to_lat': visit[1], 'nl_to_lng': visit[2],
                    'shop': transport.title(), 'cost': conv,
                })
            elif kind == 'food':
                shop = rnd.choice(sim.RESTAURANTS)
                amt = float(rnd.choice([180, 220, 260, 320, 380, 450]))
                lines.append({
                    'kind': kind, 'date': day, 'from_location': '-', 'to_location': '-',
                    'purpose': 'Lunch - %s' % shop, 'transport': False, 'conveyance_amount': 0.0,
                    'food_bill': amt, 'amount': 0.0, 'shop': shop, 'cost': amt,
                })
            else:
                what, shop = rnd.choice(sim.OTHER_COSTS)
                amt = float(rnd.choice([80, 120, 150, 200, 300]))
                lines.append({
                    'kind': kind, 'date': day, 'from_location': '-', 'to_location': '-', 'purpose': what,
                    'transport': False, 'conveyance_amount': 0.0, 'food_bill': 0.0, 'amount': amt,
                    'shop': shop, 'cost': amt,
                })
        return lines

    def _gen_expenses(self, ctx):
        env = self.env
        if 'conveyance.sheet' not in env or 'conveyance.sheet.line' not in env \
                or 'nl_geo_status' not in env['conveyance.sheet.line']._fields:
            return 'TA/DA modules (conveyance_expense + nelsis_field_expense) are not installed - skipped'
        from odoo.addons.nelsis_field_expense.controllers.expense import _attach_bill
        Sheet = env['conveyance.sheet'].sudo()
        categ = env['product.product'].sudo().search([('can_be_expensed', '=', True)], limit=1)
        rnd = ctx['rnd']
        now = ctx['now']
        # (login, state, kinds, flavour)
        plan = [
            ('demo.rahim', 'draft', ['travel', 'food', 'other'], None),
            ('demo.rahim', 'done', ['travel', 'travel', 'food'], None),
            ('demo.karim', 'supervisor', ['travel', 'food', 'travel'], None),
            ('demo.nusrat', 'vice_president', ['food', 'other', 'food'], None),
            ('demo.mahmud', 'ceo', ['travel', 'travel', 'other'], None),
            ('demo.farhana', 'approved', ['travel', 'food'], None),
            ('demo.jamal', 'refused', ['travel', 'food', 'other'], 'refused'),
            ('demo.imran', 'supervisor', ['travel', 'travel'], 'mismatch'),
            ('demo.tasnim', 'supervisor', ['travel', 'food', 'food'], 'dup'),
            ('demo.sabbir', 'done', ['travel', 'other'], None),
            ('demo.shirin', 'posted', ['food', 'other'], None),
            ('demo.farhana', 'done', ['travel', 'travel', 'food'], None),
        ]
        used = {}
        made = 0
        shared_bill = None
        for login, state, kinds, flavour in plan:
            emp = ctx['emps'].get(login)
            if not emp:
                continue
            lines = self._expense_lines(ctx, login, categ, kinds, used.setdefault(login, set()))
            if not lines:
                continue
            if flavour == 'mismatch':
                for ln in lines:
                    if ln['kind'] == 'travel':
                        ln['nl_claimed_km'] = 85.0          # GPS shows far less -> "Mismatch (False)"
                        ln['conveyance_amount'] = 1300.0
                        ln['cost'] = 1300.0
                        break
            dates = [ln['date'] for ln in lines]
            vals_lines = []
            for ln in lines:
                v = {k: ln[k] for k in ('date', 'from_location', 'to_location', 'purpose', 'transport',
                                        'conveyance_amount', 'food_bill', 'amount') if k in ln}
                v['remarks'] = 'Demo %s expense' % ln['kind']
                v['x_receipt_reference'] = 'DEMO-%04d' % rnd.randint(1000, 9999)
                if categ:
                    v['category_id'] = categ.id
                for k in ('nl_claimed_km', 'nl_from_lat', 'nl_from_lng', 'nl_to_lat', 'nl_to_lng'):
                    if k in ln:
                        v[k] = ln[k]
                ln['ref'] = v['x_receipt_reference']
                vals_lines.append((0, 0, v))
            sheet = Sheet.create({
                'employee_id': emp.id, 'designation': emp.job_id.id or False,
                'date_from': min(dates), 'date_to': max(dates), 'nl_client_uuid': 'demo-sheet-%s-%d' % (login, made),
                'line_ids': vals_lines,
            })
            self._reg(sheet)
            # bills: one scanned receipt per line (the Tasnim claim re-uses one bill -> duplicate detection)
            for line, ln in zip(sheet.line_ids.sorted('id'), lines):
                if flavour == 'dup' and ln['kind'] == 'food':
                    if shared_bill is None:
                        shared_bill = self._receipt(rnd, ln['shop'], ln['cost'], ln['date'], 'DUP-0001')
                    raw = shared_bill
                else:
                    raw = self._receipt(rnd, ln['shop'], ln['cost'], ln['date'], ln['ref'])
                try:
                    _attach_bill(env, line, {
                        'data': base64.b64encode(raw).decode(), 'filename': 'bill_%s.jpg' % ln['kind'],
                        'captured_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    })
                except Exception as e:  # noqa: BLE001
                    _logger.warning('demo bill attach failed: %s', e)
            sheet.sudo().action_geo_verify()
            if flavour == 'dup':
                dup_lines = sheet.line_ids.filtered(lambda l: l.food_bill and not l.conveyance_amount)
                if len(dup_lines) > 1:
                    dup_lines[1:].write({'nl_dup_bill': True})
            vals = {'state': state}
            if state == 'refused' and 'refuse_reason' in Sheet._fields:
                vals['refuse_reason'] = 'Bill photo is not readable and the purpose is missing. Please re-scan and resubmit.'
            if state != 'draft':
                sheet.write(vals)
            # date the claim shortly after its last trip (nicer history / charts in the app)
            when = fields.Datetime.to_datetime(max(dates).strftime('%Y-%m-%d')) + timedelta(hours=14)
            if when > now:
                when = now - timedelta(minutes=30)
            env.cr.execute('UPDATE %s SET create_date = %%s WHERE id = %%s' % Sheet._table, (when, sheet.id))
            sheet.invalidate_recordset(['create_date'])
            made += 1
        return '%d TA/DA claims (draft / in approval / paid / refused, with Travel, Food and Other lines and scanned bills)' % made

    def _gen_advances(self, ctx):
        env = self.env
        if 'employee.advance' not in env:
            return 'advance module not installed - skipped'
        Adv = env['employee.advance'].sudo()
        defaults = Adv.default_get(['journal_id', 'advance_account_id'])
        if not defaults.get('journal_id') or not defaults.get('advance_account_id'):
            return 'advance journal / account not configured yet - skipped'
        plan = [('demo.rahim', 5000.0, 'Chattogram client visit', 'paid'),
                ('demo.karim', 3000.0, 'Demo kit for Motijheel dealers', 'submitted'),
                ('demo.farhana', 2000.0, 'Collection trip - Narayanganj', 'approved'),
                ('demo.imran', 4000.0, 'Delivery run fuel & tolls', 'paid')]
        n = 0
        for login, amount, purpose, state in plan:
            emp = ctx['emps'][login]
            adv = Adv.create({'employee_id': emp.id, 'amount': amount, 'purpose': purpose})
            self._reg(adv)
            if state != 'draft':
                adv.write({'state': state})
            n += 1
        return '%d advances' % n

    def _gen_insights(self, ctx):
        env = self.env
        if 'nelsis.ai.insight' not in env:
            return 'AI Insights module not installed - skipped'
        Ins = env['nelsis.ai.insight'].sudo()
        before = set(Ins.with_context(active_test=False).search([]).ids)
        try:
            with env.cr.savepoint():
                env['nelsis.ai.engine'].sudo().scan(days=DAYS_BACK + 1)
        except Exception as e:  # noqa: BLE001
            _logger.warning('demo: AI scan failed: %s', e)
        new = Ins.with_context(active_test=False).search([('id', 'not in', list(before))])
        self._reg(new)
        emps = ctx['emps']
        samples = [
            ('demo-digest-1', 'digest', '0', 0, None, 'Daily digest - yesterday',
             'Yesterday 9 of 11 field staff punched in. 2 location points were flagged as mock GPS and 1 claim '
             'did not match the map.',
             'AI explanation (demo): activity is normal overall. Review the mock-GPS points of one employee and '
             'ask him to disable developer mock-location apps. One TA/DA line claims far more kilometres than '
             'the GPS track supports - check the bill and the visit report before approving.'),
            ('demo-late-1', 'late_pattern', '1', 40, 'demo.tasnim', 'Tasnim Rahman arrived after 10:00 on most days',
             'Review attendance pattern.', False),
        ]
        added = 0
        for fp, kind, sev, score, login, name, desc, expl in samples:
            if Ins.with_context(active_test=False).search_count([('fingerprint', '=', fp)]):
                continue
            rec = Ins.create({
                'fingerprint': fp, 'kind': kind, 'severity': sev, 'score': score, 'name': name, 'description': desc,
                'employee_id': emps[login].id if login else False, 'date': ctx['today'],
                'ai_explanation': expl or False,
            })
            self._reg(rec)
            added += 1
        # show a mix of states
        opened = new.filtered(lambda r: r.state == 'open')[:4]
        if len(opened) >= 3:
            opened[0].write({'state': 'reviewed'})
            opened[1].write({'state': 'dismissed'})
        return '%d findings from the risk engine + %d samples' % (len(new), added)
