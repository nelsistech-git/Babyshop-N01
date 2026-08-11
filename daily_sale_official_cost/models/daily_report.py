# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DailySaleOfficialCostReport(models.Model):
    """Header record: one per company per date.

    Every figure on this report is derived from posted accounting entries
    (account.move / account.move.line / account.payment). Nothing on this
    form is meant to be typed in by hand except the date filter and the
    one-time 'management partners' configuration used to detect MD/owner
    cash draws.
    """
    _name = 'daily.sale.official.cost.report'
    _description = 'Daily Sale & Official Cost Report'
    _order = 'report_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Report', compute='_compute_name', store=True)
    report_date = fields.Date(
        string='Date', required=True, default=fields.Date.context_today,
        index=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda s: s.env.company)
    currency_id = fields.Many2one(
        related='company_id.currency_id', store=True, string='Currency')

    state = fields.Selection([
        ('draft', 'Draft (Live)'),
        ('locked', 'Locked'),
    ], default='draft', required=True, tracking=True,
        help="Draft reports are recalculated live from the ledger every time "
             "they are opened or refreshed. Locking freezes today's figures "
             "so later edits to historical entries can never change a "
             "report that has already been issued.")

    # ------------------------------------------------------------------
    # Section 1: Showroom Sales  <-  account.move (out_invoice)
    # ------------------------------------------------------------------
    showroom_sale_line_ids = fields.One2many(
        'daily.report.sale.line', 'report_id', string='Showroom Sales')

    # ------------------------------------------------------------------
    # Section 2: Official Cost  <-  account.move.line (expense accounts)
    # ------------------------------------------------------------------
    official_cost_line_ids = fields.One2many(
        'daily.report.cost.line', 'report_id', string='Official Cost')

    # ------------------------------------------------------------------
    # Section 3: Supplier Transaction  <-  account.payment (outbound)
    # ------------------------------------------------------------------
    supplier_line_ids = fields.One2many(
        'daily.report.supplier.line', 'report_id', string='Supplier Transaction')

    # ------------------------------------------------------------------
    # Section 4: Mobile & Bank Transaction  <-  account.payment (inbound)
    # ------------------------------------------------------------------
    collection_line_ids = fields.One2many(
        'daily.report.collection.line', 'report_id', string='Mobile & Bank Transaction')

    # ------------------------------------------------------------------
    # Reconciliation summary (bottom panel)
    # ------------------------------------------------------------------
    previous_report_id = fields.Many2one(
        'daily.sale.official.cost.report', compute='_compute_previous_report',
        string='Previous Day Report', store=True)
    net_office_cash_adjustment = fields.Monetary(
        string='Net Office Cash Adjustment', compute='_compute_net_office_cash_adjustment',
        store=True, readonly=False,
        help="Automatically pulled from the previous day's Current Office "
             "Cash. Editable only to seed the very first report.")

    total_amount_tk = fields.Monetary(
        string='Total Amount Tk. (Bank + bKash)', compute='_compute_totals', store=True)
    total_official_cost = fields.Monetary(
        string='Total Cost Tk. (Official Cost)', compute='_compute_totals', store=True)
    total_supplier_paid = fields.Monetary(
        string='Total Paid to Suppliers', compute='_compute_totals', store=True)
    md_sir_cash_paid = fields.Monetary(
        string='MD Sir Cash Paid', compute='_compute_totals', store=True)

    current_office_cash = fields.Monetary(
        string='Current Office Cash', compute='_compute_totals', store=True,
        help="(Net Office Cash Adjustment + Total Amount Tk.) - "
             "(MD Sir Cash Paid + Total Cost Tk. + Total Paid to Suppliers)")

    management_partner_ids = fields.Many2many(
        related='company_id.daily_report_management_partner_ids',
        string='Management / MD Partners', readonly=False,
        help="Payments (outbound) to these partners are counted as "
             "'MD Sir Cash Paid' instead of ordinary Official Cost.")

    _sql_constraints = [
        ('date_company_uniq', 'unique(report_date, company_id)',
         'A Daily Sale & Official Cost report already exists for this date '
         'and company.'),
    ]

    # ------------------------------------------------------------------
    # Name
    # ------------------------------------------------------------------
    @api.depends('report_date')
    def _compute_name(self):
        for rec in self:
            rec.name = _('Daily Sale & Official Cost - %s') % (
                fields.Date.to_string(rec.report_date) if rec.report_date else '')

    # ------------------------------------------------------------------
    # Previous day linkage / opening balance
    # ------------------------------------------------------------------
    @api.depends('report_date', 'company_id')
    def _compute_previous_report(self):
        for rec in self:
            if not rec.report_date:
                rec.previous_report_id = False
                continue

            domain = [
                ('report_date', '<', rec.report_date),
                ('company_id', '=', rec.company_id.id),
            ]
            # rec.id is a NewId (not a real DB integer) while the record is
            # still unsaved, e.g. during a live onchange on a new form.
            # Passing that into ('id', '!=', rec.id) breaks the SQL cast
            # ("invalid input syntax for type integer: NewId_0x..."), and
            # it's a no-op anyway since a new record can't be found by
            # search() until it's actually saved.
            if not isinstance(rec.id, models.NewId):
                domain.append(('id', '!=', rec.id))

            rec.previous_report_id = self.search(
                domain, order='report_date desc', limit=1)

    @api.depends('previous_report_id.current_office_cash')
    def _compute_net_office_cash_adjustment(self):
        for rec in self:
            if rec.previous_report_id:
                rec.net_office_cash_adjustment = rec.previous_report_id.current_office_cash
            elif not rec.net_office_cash_adjustment:
                rec.net_office_cash_adjustment = 0.0

    # ------------------------------------------------------------------
    # Totals / final reconciliation
    # ------------------------------------------------------------------
    @api.depends('official_cost_line_ids.amount', 'supplier_line_ids.amount',
                 'collection_line_ids.amount', 'collection_line_ids.channel',
                 'net_office_cash_adjustment', 'management_partner_ids')
    def _compute_totals(self):
        for rec in self:
            rec.total_official_cost = sum(rec.official_cost_line_ids.mapped('amount'))
            rec.total_supplier_paid = sum(rec.supplier_line_ids.mapped('amount'))
            rec.total_amount_tk = sum(rec.collection_line_ids.mapped('amount'))
            rec.md_sir_cash_paid = sum(
                rec.supplier_line_ids.filtered(
                    lambda l: l.partner_id in rec.management_partner_ids
                ).mapped('amount')
            )
            # supplier payments to management partners are NOT ordinary
            # supplier spend, so exclude them from total_supplier_paid
            rec.total_supplier_paid -= rec.md_sir_cash_paid
            rec.current_office_cash = (
                (rec.net_office_cash_adjustment + rec.total_amount_tk)
                - (rec.md_sir_cash_paid + rec.total_official_cost + rec.total_supplier_paid)
            )

    # ------------------------------------------------------------------
    # Refresh (pull latest ledger data)
    # ------------------------------------------------------------------
    def action_refresh(self):
        for rec in self:
            if rec.state == 'locked':
                raise UserError(_(
                    "This report is locked for %s. Unlock it first if you "
                    "really need to re-pull ledger data.") % rec.report_date)
            rec._refresh_lines()
        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._refresh_lines()
        return records

    def _refresh_lines(self):
        for rec in self:
            rec.showroom_sale_line_ids.unlink()
            rec.official_cost_line_ids.unlink()
            rec.supplier_line_ids.unlink()
            rec.collection_line_ids.unlink()
            rec.showroom_sale_line_ids = rec._build_sale_lines()
            rec.official_cost_line_ids = rec._build_cost_lines()
            rec.supplier_line_ids = rec._build_supplier_lines()
            rec.collection_line_ids = rec._build_collection_lines()

    # -- builders --------------------------------------------------------
    def _date_domain(self, date_field='date'):
        self.ensure_one()
        return [
            (date_field, '=', self.report_date),
            ('company_id', '=', self.company_id.id),
        ]

    def _build_sale_lines(self):
        self.ensure_one()
        moves = self.env['account.move'].search(
            self._date_domain('invoice_date') + [
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
            ])
        vals = []
        for move in moves:
            paid = move.amount_total - move.amount_residual
            vals.append((0, 0, {
                'move_id': move.id,
                'partner_id': move.partner_id.id,
                'paid_advance': paid,
                'invoice_total': move.amount_total,
                'due_amount': move.amount_residual,
            }))
        return vals

    def _build_cost_lines(self):
        self.ensure_one()
        lines = self.env['account.move.line'].search(
            self._date_domain('date') + [
                ('move_id.state', '=', 'posted'),
                ('move_id.move_type', '=', 'entry'),
                ('account_id.account_type', 'in',
                 ('expense', 'expense_direct_cost')),
                ('debit', '>', 0),
            ])
        vals = []
        for line in lines:
            vals.append((0, 0, {
                'move_line_id': line.id,
                'cost_detail': line.name or line.move_id.ref or '/',
                'payee': line.partner_id.name or line.move_id.ref or '',
                'amount': line.debit,
            }))
        return vals

    def _build_supplier_lines(self):
        self.ensure_one()
        payments = self.env['account.payment'].search(
            self._date_domain('date') + [
                ('payment_type', '=', 'outbound'),
                ('partner_type', '=', 'supplier'),
                ('state', '=', 'posted'),
            ])
        vals = []
        for pay in payments:
            vals.append((0, 0, {
                'payment_id': pay.id,
                'partner_id': pay.partner_id.id,
                'payment_method': pay.journal_id.name,
                'amount': pay.amount,
            }))
        return vals

    def _build_collection_lines(self):
        self.ensure_one()
        payments = self.env['account.payment'].search(
            self._date_domain('date') + [
                ('payment_type', '=', 'inbound'),
                ('partner_type', '=', 'customer'),
                ('journal_id.type', 'in', ('bank', 'cash')),
                ('state', '=', 'posted'),
            ])
        vals = []
        for pay in payments:
            journal_name = (pay.journal_id.name or '').lower()
            channel = 'bkash' if 'bkash' in journal_name or 'mobile' in journal_name else 'bank'
            vals.append((0, 0, {
                'payment_id': pay.id,
                'partner_id': pay.partner_id.id,
                'channel': channel,
                'journal_id': pay.journal_id.id,
                'payment_ref': pay.ref or pay.memo or '',
                'amount': pay.amount,
            }))
        return vals

    # ------------------------------------------------------------------
    # Lock / unlock
    # ------------------------------------------------------------------
    def action_lock(self):
        for rec in self:
            rec._refresh_lines()  # capture the latest data one last time
            rec.state = 'locked'

    def action_unlock(self):
        # Restricted to the 'Daily Report Manager' group via the button's
        # groups attribute in the view.
        self.write({'state': 'draft'})