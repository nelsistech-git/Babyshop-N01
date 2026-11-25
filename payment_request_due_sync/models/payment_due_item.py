# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

INACTIVE_REQUEST_STATES = ('cancelled', 'rejected')


class PaymentDueItem(models.Model):
    _name = 'payment.due.item'
    _description = 'Due for Payment'
    _order = 'due_date, id'

    source_type = fields.Selection([('bill', 'Vendor Bill'), ('expense', 'Expense')],
                                   string='Type', required=True, readonly=True)
    move_id = fields.Many2one('account.move', string='Vendor Bill', ondelete='cascade',
                              index=True, readonly=True)
    sheet_id = fields.Many2one('hr.expense.sheet', string='Expense Report', ondelete='cascade',
                               index=True, readonly=True)
    name = fields.Char(string='Reference', readonly=True)
    ref = fields.Char(string="Vendor's Invoice Ref.", readonly=True)
    partner_id = fields.Many2one('res.partner', string='Vendor / Employee', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id', string='Currency')
    amount = fields.Monetary(string='Amount Due', currency_field='currency_id', readonly=True)
    due_date = fields.Date(string='Due Date', readonly=True)
    is_overdue = fields.Boolean(string='Overdue', compute='_compute_is_overdue')

    request_line_ids = fields.One2many('payment.request.line', 'due_item_id', string='Request Lines')
    state = fields.Selection(
        [('pending', 'Pending'), ('requested', 'In Payment Request'), ('paid', 'Paid')],
        string='Status', compute='_compute_state', store=True, index=True)
    request_id = fields.Many2one('payment.request', string='Payment Request',
                                 compute='_compute_state', store=True)
    source_paid = fields.Boolean(
        string='Source Paid', readonly=True, copy=False,
        help='The bill / expense report / conveyance sheet was found paid (by any route).')

    _sql_constraints = [
        ('move_unique', 'unique(move_id)', 'This vendor bill is already listed.'),
        ('sheet_unique', 'unique(sheet_id)', 'This expense report is already listed.'),
    ]

    @api.depends('due_date')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_overdue = bool(rec.due_date and rec.due_date < today)

    @api.depends('request_line_ids.request_state', 'request_line_ids.request_id',
                 'request_line_ids.is_paid', 'source_paid')
    def _compute_state(self):
        for rec in self:
            active = rec.request_line_ids.filtered(
                lambda l: l.request_state not in INACTIVE_REQUEST_STATES)
            if rec.source_paid or (active and any(
                    l.request_state == 'paid' or l.is_paid for l in active)):
                rec.state = 'paid'          # settled through the request: never listed again
            else:
                rec.state = 'requested' if active else 'pending'
            rec.request_id = active[:1].request_id

    def _source_is_paid(self):
        """True when the underlying document is already paid / finished (any payment route)."""
        self.ensure_one()
        if self.source_type == 'bill':
            return bool(self.move_id) and self.move_id.payment_state in ('paid', 'in_payment')
        if self.source_type == 'expense':
            sheet = self.sheet_id
            return bool(sheet) and (sheet.state == 'done' or (
                'payment_state' in sheet._fields and sheet.payment_state in ('paid', 'in_payment')))
        # other source types (e.g. conveyance, added by its own module): finished sheet
        sheet = self['conveyance_sheet_id'] if 'conveyance_sheet_id' in self._fields else False
        return bool(sheet) and sheet.state == 'done'

    def _settle_source(self):
        """The Payment Request of these rows was paid: mark the rows paid and finish the source
        (a posted conveyance sheet becomes Done)."""
        for item in self:
            item.source_paid = True
            if 'conveyance_sheet_id' in item._fields and item.conveyance_sheet_id \
                    and item.conveyance_sheet_id.state == 'posted':
                sheet = item.conveyance_sheet_id.sudo()
                sheet.write({'state': 'done'})
                sheet.message_post(body=_('Paid through Payment Request %s.')
                                   % item.request_id.display_name)
        return True

    # ------------------------------------------------------------------
    # Sync: bills (any amount) + expense reports (over the minimum)
    # ------------------------------------------------------------------
    @api.model
    def _sync(self):
        """Create / refresh / clean up the rows. Safe to call as often as needed."""
        self = self.sudo()
        icp = self.env['ir.config_parameter'].sudo()
        min_expense = float(icp.get_param('payment_request_due_sync.expense_min_amount', 5000) or 0)
        today = fields.Date.context_today(self)

        claimed_bills = self.env['payment.request.line'].search([
            ('invoice_id', '!=', False), ('request_state', 'not in', INACTIVE_REQUEST_STATES),
            ('due_item_id', '=', False)]).mapped('invoice_id')
        claimed_sheets = self.env['payment.request.line'].search([
            ('expense_sheet_id', '!=', False), ('request_state', 'not in', INACTIVE_REQUEST_STATES),
            ('due_item_id', '=', False)]).mapped('expense_sheet_id')

        wanted = {}      # (type, source id) -> values
        # A bill is listed as soon as the Head of Finance has POSTED it (bill_stage = Due for
        # Payment) - whatever its due date. Bills still waiting for approval are never listed.
        bills = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'), ('state', '=', 'posted'),
            ('bill_stage', '=', 'due_for_payment'),
            ('payment_state', 'in', ('not_paid', 'partial'))])
        for bill in bills - claimed_bills:
            company = bill.company_id
            amount = bill.amount_residual if bill.currency_id == company.currency_id \
                else abs(bill.amount_residual_signed)
            wanted[('bill', bill.id)] = {
                'source_type': 'bill', 'move_id': bill.id, 'name': bill.name,
                'ref': bill.ref, 'partner_id': bill.partner_id.id, 'company_id': company.id,
                'amount': amount,
                'due_date': bill.invoice_date_due or bill.invoice_date or today}

        if 'hr.expense.sheet' in self.env:
            Sheet = self.env['hr.expense.sheet']
            domain = [('state', 'in', ('approve', 'post'))]
            if 'payment_state' in Sheet._fields:
                domain.append(('payment_state', 'not in', ('paid', 'in_payment')))
            for sheet in Sheet.search(domain) - claimed_sheets:
                company = sheet.company_id
                amount = sheet.total_amount
                if sheet.currency_id and sheet.currency_id != company.currency_id:
                    amount = sheet.currency_id._convert(amount, company.currency_id, company, today)
                if amount <= min_expense:
                    continue            # up to the limit: paid directly from Expenses
                partner = sheet.employee_id.work_contact_id
                wanted[('expense', sheet.id)] = {
                    'source_type': 'expense', 'sheet_id': sheet.id, 'name': sheet.name,
                    'ref': sheet.employee_id.name, 'partner_id': partner.id,
                    'company_id': company.id, 'amount': amount,
                    'due_date': sheet.accounting_date or today}

        existing = {}
        for item in self.search([('source_type', 'in', ('bill', 'expense'))]):
            key = ('bill', item.move_id.id) if item.source_type == 'bill' \
                else ('expense', item.sheet_id.id)
            existing[key] = item
        to_create = [vals for key, vals in wanted.items() if key not in existing]
        if to_create:
            self.create(to_create)
        for key, item in existing.items():
            if key in wanted:
                item.write({k: v for k, v in wanted[key].items()
                            if k not in ('source_type', 'move_id', 'sheet_id')})
            elif item.state == 'pending':
                item.unlink()            # paid / cancelled / claimed elsewhere: drop it
        # rows already in a request whose source got paid (Accounting Pay, Register Payment...)
        for item in self.search([('state', '=', 'requested')]):
            if item._source_is_paid():
                item.source_paid = True
        return True

    @api.model
    def _cron_sync(self):
        self._sync()

    @api.model
    def action_open_due_items(self):
        """Menu entry: refresh first, then open the list (Pending rows by default)."""
        self._sync()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Due for Payment'),
            'res_model': self._name,
            'view_mode': 'tree',
            'search_view_id': self.env.ref('payment_request_due_sync.view_payment_due_item_search').id,
            'context': {'search_default_pending': 1},
            'target': 'main',
        }

    # ------------------------------------------------------------------
    # Selected rows -> one Draft Payment Request
    # ------------------------------------------------------------------
    def _prepare_request_line_vals(self):
        self.ensure_one()
        vals = {'partner_id': self.partner_id.id, 'bill_amount': self.amount,
                'due_item_id': self.id, 'due_date': self.due_date}
        if self.source_type == 'bill':
            bill = self.move_id
            vals.update({
                'invoice_id': bill.id, 'invoice_ref': bill.ref or bill.name,
                'invoice_date': bill.invoice_date,
                'purpose': self.env['payment.request.line']._purpose_from_bill(bill)})
        else:
            sheet = self.sheet_id
            vals.update({
                'expense_sheet_id': sheet.id, 'invoice_ref': sheet.name,
                'invoice_date': sheet.accounting_date,
                'purpose': _('Expense %s - %s') % (sheet.name, sheet.employee_id.name)})
        return vals

    def action_create_payment_request(self):
        items = self.filtered(lambda i: i.state == 'pending')
        if not items:
            raise UserError(_('Select at least one Pending row. Rows already in a Payment '
                              'Request cannot be added again.'))
        if len(items.company_id) > 1:
            raise UserError(_('Select rows of one company at a time.'))
        request = self.env['payment.request'].create({
            'company_id': items.company_id.id,
            'line_ids': [(0, 0, item._prepare_request_line_vals()) for item in items],
        })
        return {
            'type': 'ir.actions.act_window', 'name': _('Payment Request'),
            'res_model': 'payment.request', 'view_mode': 'form', 'res_id': request.id,
        }

    def action_open_source(self):
        self.ensure_one()
        record = self.move_id if self.source_type == 'bill' else self.sheet_id
        return {'type': 'ir.actions.act_window', 'res_model': record._name,
                'view_mode': 'form', 'res_id': record.id}