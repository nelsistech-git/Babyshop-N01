from datetime import timedelta

from odoo import api, fields, models

PAID_STATES = ('done',)
STAGE = {
    'draft': 'Draft', 'supervisor': 'With Accounts', 'vice_president': 'With Line Manager', 'ceo': 'With HoF',
    'approved': 'Approved', 'posted': 'Posted', 'done': 'Paid', 'refused': 'Refused',
}


class NelsisAppService(models.AbstractModel):
    _inherit = 'nelsis.app.service'

    @api.model
    def sheet_dict(self, s, detail=False):
        geo = s.line_ids.mapped('nl_geo_status')
        d = {
            'id': s.id, 'ref': s.name, 'date_from': s.date_from and fields.Date.to_string(s.date_from),
            'date_to': s.date_to and fields.Date.to_string(s.date_to), 'total': s.total_amount,
            'state': s.state, 'state_label': STAGE.get(s.state, s.state), 'lines': len(s.line_ids),
            'paid': s.state in PAID_STATES, 'refuse_reason': s.refuse_reason or '',
            'created': fields.Datetime.to_string(s.create_date).replace(' ', 'T') + 'Z',
            'map_ok': s.nl_geo_ok, 'map_mismatch': s.nl_mismatch_count,
            'map_checked': any(g != 'pending' for g in geo),
        }
        if detail:
            d['line_items'] = [{
                'id': l.id, 'date': fields.Date.to_string(l.date), 'from': l.from_location or '', 'to': l.to_location or '',
                'purpose': l.purpose or '', 'transport': l.transport or '', 'conveyance': l.conveyance_amount,
                'food': l.food_bill, 'other': l.amount, 'total': l.total_amount, 'remarks': l.remarks or '',
                'receipt_ref': l.x_receipt_reference or '', 'geo_status': l.nl_geo_status, 'geo_ok': l.nl_geo_ok,
                'geo_note': l.nl_geo_note or '', 'geo_km': l.nl_geo_km, 'dup_bill': l.nl_dup_bill,
                'attachments': [{'id': a.id, 'name': a.name, 'mime': a.mimetype} for a in l.attachment_ids],
            } for l in s.line_ids]
        return d

    @api.model
    def advance_dict(self, a):
        adjs = a.adjustment_ids.filtered(lambda x: x.state != 'cancel')
        adjusted = sum(x.expense_total for x in adjs.filtered(lambda x: x.state in ('payable', 'done')))
        pending = a.state == 'paid' and not adjs
        stage = {'draft': 'Draft', 'submitted': 'Supervisor review', 'approved': 'Accounts review',
                 'paid': 'Paid - adjustment due', 'closed': 'Adjusted', 'cancel': 'Cancelled'}
        return {
            'id': a.id, 'ref': a.name, 'date': fields.Date.to_string(a.date), 'purpose': a.purpose, 'amount': a.amount,
            'state': a.state, 'state_label': stage.get(a.state, a.state), 'remark': a.remark or '',
            'adjusted': adjusted, 'outstanding': max(a.amount - adjusted, 0) if a.state == 'paid' else 0,
            'needs_adjustment': pending,
            'adjustments': [{'id': x.id, 'ref': x.name, 'state': x.state, 'expense_total': x.expense_total,
                             'refund': x.refund_amount, 'payable': x.payable_amount} for x in adjs],
        }

    @api.model
    def dashboard(self, employee):
        res = super().dashboard(employee)
        Sheet = self.env['conveyance.sheet']
        Adv = self.env['employee.advance']
        sheets = Sheet.search([('employee_id', '=', employee.id)], order='id desc')
        today = fields.Date.context_today(self)
        month = [s for s in sheets if s.create_date and s.create_date.month == today.month and s.create_date.year == today.year]
        by_state = {}
        for s in sheets:
            by_state[s.state] = by_state.get(s.state, 0) + 1
        # last 6 months of claims
        months = []
        for i in range(5, -1, -1):
            y, m = today.year, today.month - i
            while m <= 0:
                m += 12
                y -= 1
            tot = sum(s.total_amount for s in sheets if s.create_date and (s.create_date.year, s.create_date.month) == (y, m))
            months.append({'label': '%d-%02d' % (y, m), 'total': tot})
        advs = Adv.search([('employee_id', '=', employee.id), ('state', '!=', 'cancel')], order='id desc')
        ad = [self.advance_dict(a) for a in advs]
        res['expense'] = {
            'month_total': sum(s.total_amount for s in month),
            'pending_amount': sum(s.total_amount for s in sheets if s.state in ('supervisor', 'vice_president', 'ceo', 'approved', 'posted')),
            'paid_amount': sum(s.total_amount for s in sheets if s.state == 'done'),
            'draft_count': by_state.get('draft', 0), 'refused_count': by_state.get('refused', 0),
            'by_state': by_state, 'monthly': months,
            'recent': [self.sheet_dict(s) for s in sheets[:5]],
        }
        res['advance'] = {
            'total_taken': sum(a['amount'] for a in ad if a['state'] in ('paid', 'closed')),
            'outstanding': sum(a['outstanding'] for a in ad),
            'open_count': len([a for a in ad if a['state'] in ('submitted', 'approved', 'paid')]),
            'items': ad[:5],
        }
        return res
