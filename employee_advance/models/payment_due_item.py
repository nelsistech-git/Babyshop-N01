# -*- coding: utf-8 -*-
from odoo import _, fields, models


class PaymentDueItem(models.Model):
    """Employee advances above the payment limit (default BDT 5,000) that reached Accounts Review
    are listed in 'Due for Payment'; they are paid from the bank account of the Payment Request."""
    _inherit = 'payment.due.item'

    source_type = fields.Selection(
        selection_add=[('advance', 'Advance')], ondelete={'advance': 'cascade'})
    employee_advance_id = fields.Many2one(
        'employee.advance', string='Employee Advance', ondelete='cascade', index=True, readonly=True)

    _sql_constraints = [
        ('employee_advance_unique', 'unique(employee_advance_id)', 'This advance is already listed.'),
    ]

    def _sync(self):
        res = super()._sync()
        self._sync_advances()
        return res

    def _sync_advances(self):
        self = self.sudo()
        today = fields.Date.context_today(self)
        Advance = self.env['employee.advance']
        from odoo.addons.payment_request_due_sync.models.hr_expense_sheet import get_payment_threshold
        threshold = get_payment_threshold(self.env)
        wanted = {}
        for adv in Advance.search([('state', '=', 'approved')]):
            if adv.amount <= threshold:
                continue
            partner = adv.employee_id.work_contact_id
            wanted[adv.id] = {
                'source_type': 'advance', 'employee_advance_id': adv.id, 'name': adv.name,
                'ref': adv.purpose, 'partner_id': partner.id, 'company_id': adv.company_id.id,
                'amount': adv.amount, 'due_date': today,
            }
        existing = {i.employee_advance_id.id: i for i in self.search([('source_type', '=', 'advance')])}
        to_create = [v for k, v in wanted.items() if k not in existing]
        if to_create:
            self.create(to_create)
        for aid, item in existing.items():
            if aid in wanted:
                item.write({k: v for k, v in wanted[aid].items()
                            if k not in ('source_type', 'employee_advance_id', 'due_date')})
            elif item.state == 'pending':
                item.unlink()           # returned / cancelled before a request was made

    def _source_is_paid(self):
        self.ensure_one()
        if self.source_type == 'advance':
            return self.employee_advance_id.state in ('paid', 'adjusted')
        return super()._source_is_paid()

    def _settle_source(self):
        advances = self.filtered(lambda i: i.source_type == 'advance')
        for item in advances:
            line = item.request_line_ids.filtered(
                lambda l: l.request_state not in ('cancelled', 'rejected'))[:1]
            item.employee_advance_id.sudo()._post_from_payment_request(line)
        return super()._settle_source()

    def _prepare_request_line_vals(self):
        self.ensure_one()
        if self.source_type != 'advance':
            return super()._prepare_request_line_vals()
        adv = self.employee_advance_id
        return {
            'partner_id': self.partner_id.id, 'bill_amount': self.amount,
            'due_item_id': self.id, 'due_date': self.due_date,
            'employee_advance_id': adv.id, 'invoice_ref': adv.name, 'invoice_date': adv.date,
            'purpose': _('Advance %s - %s - %s') % (adv.name, adv.employee_id.name, adv.purpose),
        }

    def action_open_source(self):
        self.ensure_one()
        if self.source_type != 'advance':
            return super().action_open_source()
        return {'type': 'ir.actions.act_window', 'res_model': 'employee.advance',
                'view_mode': 'form', 'res_id': self.employee_advance_id.id}


class PaymentRequestLine(models.Model):
    _inherit = 'payment.request.line'

    employee_advance_id = fields.Many2one(
        'employee.advance', string='Employee Advance', copy=False, readonly=True, index=True,
        ondelete='set null')
