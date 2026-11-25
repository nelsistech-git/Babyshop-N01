"""Expense / advance / payment endpoints for the Nelsis mobile app."""
import base64
import binascii
import logging

from odoo import http, fields, _
from odoo.exceptions import AccessError, UserError
from odoo.http import request

from odoo.addons.nelsis_field_tracking.controllers.main import api_route, _err

from ..models.ir_attachment import normalize_bill_image

_logger = logging.getLogger(__name__)

MAX_UPLOAD = 12 * 1024 * 1024
TRANSPORTS = [
    ('rickshaw', 'Rickshaw'), ('cng', 'CNG'), ('uber', 'Uber'), ('bus', 'Bus'), ('pathao', 'Pathao'),
    ('metro_rail', 'Metro Rail'), ('car', 'Car'), ('walked', 'Walked'), ('others', 'Others'),
]


def _own_sheet(env, employee, sheet_id):
    sheet = env['conveyance.sheet'].browse(int(sheet_id)).exists()
    if not sheet or sheet.employee_id != employee:
        raise AccessError(_('Record not found.'))
    return sheet


def _attach_bill(env, line, att):
    """Store one bill file on a conveyance line. Images are resized/normalised, PDFs kept as is."""
    try:
        raw = base64.b64decode(att.get('data') or '', validate=False)
    except (binascii.Error, ValueError):
        raise UserError(_('Invalid file data.'))
    if not raw or len(raw) > MAX_UPLOAD:
        raise UserError(_('File is empty or larger than 12 MB.'))
    name = (att.get('filename') or 'bill').rsplit('/', 1)[-1][:80]
    vals = {'res_model': 'conveyance.sheet.line', 'res_id': line.id}
    if raw[:4] == b'%PDF':
        vals.update(name=name if name.lower().endswith('.pdf') else name + '.pdf', mimetype='application/pdf', raw=raw)
        digest = False
    else:
        try:
            jpeg, digest, w, h = normalize_bill_image(raw)
        except Exception:  # noqa: BLE001
            raise UserError(_('This file is not a valid image or PDF.'))
        base = name.rsplit('.', 1)[0] or 'bill'
        vals.update(name=base + '.jpg', mimetype='image/jpeg', raw=jpeg, nl_bill_hash=digest)
    if att.get('lat') and att.get('lng'):
        vals.update(nl_capture_lat=float(att['lat']), nl_capture_lng=float(att['lng']))
    cap = att.get('captured_at')
    if cap:
        from odoo.addons.nelsis_field_tracking.models.location_log import parse_dt
        vals['nl_captured_at'] = parse_dt(cap)
    a = env['ir.attachment'].sudo().create(vals)
    line.sudo().write({'attachment_ids': [(4, a.id)]})
    if vals['mimetype'] == 'image/jpeg' and not line.x_receipt_attachment:
        line.sudo().write({'x_receipt_attachment': a.datas, 'x_receipt_filename': a.name})
    if digest and _is_duplicate_bill(env, a, digest):
        line.sudo().write({'nl_dup_bill': True})
    return a


NEAR_DUP_BITS = 4          # difference-hash distance (of 64 bits) still treated as "the same bill"


def _is_duplicate_bill(env, att, digest):
    """Exact hash match, or a near match (same bill re-photographed, cropped slightly, different light)."""
    Att = env['ir.attachment'].sudo()
    base = [('id', '!=', att.id), ('res_model', '=', 'conveyance.sheet.line'), ('nl_bill_hash', '!=', False)]
    if Att.search_count(base + [('nl_bill_hash', '=', digest)]):
        return True
    me = int(digest, 16)
    others = Att.search_read(base, ['nl_bill_hash'], limit=20000, order='id desc')
    for o in others:
        try:
            if bin(me ^ int(o['nl_bill_hash'], 16)).count('1') <= NEAR_DUP_BITS:
                return True
        except ValueError:
            continue
    return False


class NelsisExpenseApi(http.Controller):

    @api_route('/expenses/meta', methods=('GET',))
    def meta(self, env, employee, body):
        cats = env['product.product'].sudo().search([('can_be_expensed', '=', True)], limit=60)
        return {
            'transports': [{'key': k, 'label': v} for k, v in TRANSPORTS],
            'categories': [{'id': c.id, 'name': c.display_name} for c in cats],
        }

    @api_route('/expenses', methods=('GET',))
    def list_sheets(self, env, employee, body, state='', limit='30', offset='0'):
        dom = [('employee_id', '=', employee.id)]
        if state:
            dom.append(('state', '=', state))
        recs = env['conveyance.sheet'].search(dom, limit=max(1, min(int(limit), 100)), offset=int(offset), order='id desc')
        svc = env['nelsis.app.service']
        return {'items': [svc.sheet_dict(s) for s in recs]}

    @api_route('/expenses/<int:sheet_id>', methods=('GET',))
    def sheet_detail(self, env, employee, body, sheet_id):
        s = _own_sheet(env, employee, sheet_id)
        return {'item': env['nelsis.app.service'].sheet_dict(s, detail=True)}

    @api_route('/expenses/conveyance')
    def create_sheet(self, env, employee, body):
        uid = (body.get('uuid') or '')[:64]
        Sheet = env['conveyance.sheet']
        if uid:
            dup = Sheet.sudo().search([('nl_client_uuid', '=', uid), ('employee_id', '=', employee.id)], limit=1)
            if dup:
                return {'item': env['nelsis.app.service'].sheet_dict(dup, detail=True), 'duplicate': True}
        lines = body.get('lines') or []
        if not lines or len(lines) > 60:
            raise UserError(_('Add between 1 and 60 lines.'))
        vals_lines = []
        for ln in lines:
            if not ln.get('date'):
                raise UserError(_('Every line needs a date.'))
            conv, food, other = (float(ln.get(k) or 0) for k in ('conveyance', 'food', 'other'))
            if min(conv, food, other) < 0 or conv + food + other <= 0:
                raise UserError(_('Line amounts must be positive.'))
            transport = ln.get('transport')
            vals_lines.append((0, 0, {
                'date': ln['date'], 'from_location': (ln.get('from') or '')[:120] or '-', 'to_location': (ln.get('to') or '')[:120] or '-',
                'purpose': (ln.get('purpose') or '')[:200], 'transport': transport if transport in dict(TRANSPORTS) else False,
                'category_id': int(ln['category_id']) if ln.get('category_id') else False,
                'conveyance_amount': conv, 'food_bill': food, 'amount': other,
                'remarks': (ln.get('remarks') or '')[:200], 'x_receipt_reference': (ln.get('receipt_ref') or '')[:80],
                'nl_claimed_km': float(ln.get('claimed_km') or 0),
                'nl_from_lat': float(ln.get('from_lat') or 0), 'nl_from_lng': float(ln.get('from_lng') or 0),
                'nl_to_lat': float(ln.get('to_lat') or 0), 'nl_to_lng': float(ln.get('to_lng') or 0),
            }))
        sheet = Sheet.create({
            'employee_id': employee.id, 'designation': employee.job_id.id or False,
            'date_from': body.get('date_from') or False, 'date_to': body.get('date_to') or False,
            'nl_client_uuid': uid or False, 'line_ids': vals_lines,
        })
        # attachments are matched to lines by position
        for line, src in zip(sheet.line_ids.sorted('id'), lines):
            for att in (src.get('attachments') or [])[:6]:
                _attach_bill(env, line, att)
        sheet.sudo().action_geo_verify()
        if body.get('submit', True):
            sheet.action_submit()
        return {'item': env['nelsis.app.service'].sheet_dict(sheet, detail=True)}

    @api_route('/expenses/<int:sheet_id>/submit')
    def submit_sheet(self, env, employee, body, sheet_id):
        s = _own_sheet(env, employee, sheet_id)
        if s.state != 'draft':
            raise UserError(_('Only draft sheets can be submitted.'))
        s.sudo().action_geo_verify()
        s.action_submit()
        return {'item': env['nelsis.app.service'].sheet_dict(s, detail=True)}

    @api_route('/expenses/<int:sheet_id>/attachments')
    def add_attachment(self, env, employee, body, sheet_id):
        s = _own_sheet(env, employee, sheet_id)
        if s.state != 'draft':
            raise UserError(_('Bills can only be added while the sheet is a draft.'))
        line = s.line_ids.filtered(lambda l: l.id == int(body.get('line_id') or 0))
        if not line:
            raise UserError(_('Line not found.'))
        a = _attach_bill(env, line, body)
        return {'attachment': {'id': a.id, 'name': a.name, 'mime': a.mimetype}}

    @api_route('/attachments/<int:att_id>', methods=('GET',))
    def get_attachment(self, env, employee, body, att_id):
        a = env['ir.attachment'].sudo().browse(att_id).exists()
        if not a or a.res_model != 'conveyance.sheet.line':
            raise AccessError(_('Not found.'))
        line = env['conveyance.sheet.line'].sudo().browse(a.res_id)
        if line.sheet_id.employee_id != employee:
            raise AccessError(_('Not found.'))
        safe_name = ''.join(c for c in (a.name or 'bill') if c.isalnum() or c in ' ._-')[:80] or 'bill'
        return request.make_response(a.raw, headers=[
            ('Content-Type', a.mimetype or 'application/octet-stream'),
            ('Content-Disposition', 'inline; filename="%s"' % safe_name),
            ('Cache-Control', 'private, max-age=3600'), ('X-Content-Type-Options', 'nosniff')])

    # ---------------------------------------------------------------- advances
    @api_route('/advances', methods=('GET',))
    def list_advances(self, env, employee, body):
        recs = env['employee.advance'].search([('employee_id', '=', employee.id)], order='id desc', limit=100)
        svc = env['nelsis.app.service']
        return {'items': [svc.advance_dict(a) for a in recs]}

    @api_route('/advances/request')
    def request_advance(self, env, employee, body):
        Adv = env['employee.advance']
        amount = float(body.get('amount') or 0)
        purpose = (body.get('purpose') or '').strip()
        if amount <= 0 or not purpose:
            raise UserError(_('Amount and purpose are required.'))
        uid = (body.get('uuid') or '')[:64]
        if uid:
            mark = '[app:%s]' % uid
            dup = Adv.search([('employee_id', '=', employee.id), ('purpose', 'like', mark)], limit=1)
            if dup:
                return {'item': env['nelsis.app.service'].advance_dict(dup), 'duplicate': True}
            purpose = '%s %s' % (purpose[:180], mark)
        defaults = Adv.default_get(['journal_id', 'advance_account_id'])
        if not defaults.get('journal_id') or not defaults.get('advance_account_id'):
            raise UserError(_('Advance accounts are not configured yet. Please contact Accounts.'))
        adv = Adv.create({'employee_id': employee.id, 'amount': amount, 'purpose': purpose})
        adv.action_submit()
        return {'item': env['nelsis.app.service'].advance_dict(adv)}

    # ---------------------------------------------------------------- payment history
    @api_route('/payments', methods=('GET',))
    def payments(self, env, employee, body, limit='60'):
        limit = str(max(1, min(int(limit) if str(limit).isdigit() else 60, 200)))
        svc = env['nelsis.app.service']
        items = []
        for s in env['conveyance.sheet'].search([('employee_id', '=', employee.id)], order='id desc', limit=int(limit)):
            d = svc.sheet_dict(s)
            items.append({'kind': 'conveyance', 'id': s.id, 'ref': s.name, 'date': (d['date_to'] or d['created'][:10]),
                          'amount': s.total_amount, 'state': s.state, 'state_label': d['state_label'], 'paid': d['paid'],
                          'map_ok': s.nl_geo_ok})
        for a in env['employee.advance'].search([('employee_id', '=', employee.id)], order='id desc', limit=int(limit)):
            d = svc.advance_dict(a)
            items.append({'kind': 'advance', 'id': a.id, 'ref': a.name, 'date': d['date'], 'amount': a.amount,
                          'state': a.state, 'state_label': d['state_label'], 'paid': a.state in ('paid', 'closed'),
                          'map_ok': None})
        for j in env['employee.advance.adjustment'].search([('employee_id', '=', employee.id)], order='id desc', limit=int(limit)):
            items.append({'kind': 'adjustment', 'id': j.id, 'ref': j.name, 'date': fields.Date.to_string(j.create_date.date()),
                          'amount': j.expense_total, 'state': j.state, 'state_label': dict(j._fields['state'].selection).get(j.state),
                          'paid': j.state == 'done', 'map_ok': None})
        items.sort(key=lambda x: (x['date'] or ''), reverse=True)
        return {'items': items[:int(limit)]}
