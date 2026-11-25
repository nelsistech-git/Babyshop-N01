# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PaymentDueItem(models.Model):
    """Posted Conveyance Sheets above the threshold (default BDT 5,000) show up in the
    'Due for Payment' window of the Payment Request module."""
    _inherit = 'payment.due.item'

    source_type = fields.Selection(
        selection_add=[('conveyance', 'Conveyance')],
        ondelete={'conveyance': 'cascade'},
    )
    conveyance_sheet_id = fields.Many2one(
        'conveyance.sheet', string='Conveyance Sheet', ondelete='cascade',
        index=True, readonly=True)

    _sql_constraints = [
        ('conveyance_unique', 'unique(conveyance_sheet_id)', 'This conveyance sheet is already listed.'),
    ]

    def unlink(self):
        # the standard sync only knows bills / expense reports and would drop our rows
        if self.env.context.get('keep_conveyance_items'):
            self = self.filtered(lambda i: i.source_type != 'conveyance')
        return super().unlink()

    @api.model
    def _sync(self):
        super(PaymentDueItem, self.with_context(keep_conveyance_items=True))._sync()
        self._sync_conveyance()
        self._drop_conveyance_expense_duplicates()
        return True

    @api.model
    def _drop_conveyance_expense_duplicates(self):
        """A conveyance expense is paid through its Conveyance Sheet row. Its Expense Report
        row (created by the standard sync) would list the same money twice, so remove the
        still-pending 'expense' rows - but ONLY when the conveyance sheet really has its own
        row. If the sheet is not Posted (no row of its own) the Expense Report row must stay,
        otherwise the report is listed nowhere and cannot go to a Payment Request."""
        listed = self.sudo().search([('source_type', '=', 'conveyance')]).conveyance_sheet_id
        if not listed:
            return
        items = self.sudo().search([('source_type', '=', 'expense'), ('state', '=', 'pending')])
        dup = items.filtered(
            lambda i: i.sheet_id and (i.sheet_id.expense_line_ids.conveyance_sheet_ids & listed))
        if dup:
            dup.unlink()

    @api.model
    def _sync_conveyance(self):
        self = self.sudo()
        today = fields.Date.context_today(self)
        Sheet = self.env['conveyance.sheet']
        threshold = Sheet._payment_threshold()
        wanted = {}
        for sheet in Sheet.search([('state', '=', 'posted')]):
            if sheet.total_amount <= threshold:
                continue
            company = sheet.company_id or sheet.employee_id.company_id
            partner = (sheet.employee_id.work_contact_id
                       or sheet.employee_id.user_id.partner_id)
            wanted[sheet.id] = {
                'source_type': 'conveyance', 'conveyance_sheet_id': sheet.id,
                'name': sheet.name, 'ref': sheet.employee_id.name,
                'partner_id': partner.id, 'company_id': company.id,
                'amount': sheet.total_amount, 'due_date': today,
            }
        existing = {i.conveyance_sheet_id.id: i for i in self.search([('source_type', '=', 'conveyance')])}
        to_create = [v for k, v in wanted.items() if k not in existing]
        if to_create:
            self.create(to_create)
        for sid, item in existing.items():
            if sid in wanted:
                item.write({k: v for k, v in wanted[sid].items()
                            if k not in ('source_type', 'conveyance_sheet_id', 'due_date')})
            elif item.state == 'pending':
                item.with_context(keep_conveyance_items=False).unlink()

    def _prepare_request_line_vals(self):
        self.ensure_one()
        if self.source_type != 'conveyance':
            return super()._prepare_request_line_vals()
        sheet = self.conveyance_sheet_id
        return {
            'partner_id': self.partner_id.id, 'bill_amount': self.amount,
            'due_item_id': self.id, 'due_date': self.due_date,
            'conveyance_sheet_id': sheet.id, 'invoice_ref': sheet.name,
            'invoice_date': fields.Date.context_today(self),
            'purpose': _('Conveyance %s - %s') % (sheet.name, sheet.employee_id.name),
        }

    def action_open_source(self):
        self.ensure_one()
        if self.source_type != 'conveyance':
            return super().action_open_source()
        return {'type': 'ir.actions.act_window', 'res_model': 'conveyance.sheet',
                'view_mode': 'form', 'res_id': self.conveyance_sheet_id.id}


class PaymentRequestLine(models.Model):
    _inherit = 'payment.request.line'

    conveyance_sheet_id = fields.Many2one(
        'conveyance.sheet', string='Conveyance Sheet', copy=False, readonly=True, index=True,
        ondelete='set null')