# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from datetime import datetime, time

import pytz

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

from .bond_sql import ledger_base_sql

MANAGER_GROUP = 'nelsis_bond_reconciliation.group_bond_recon_manager'
EDITABLE_STATES = ('draft', 'in_progress', 'discrepancy')

STATES = [
    ('draft', 'Draft'),
    ('in_progress', 'In Progress'),
    ('discrepancy', 'Discrepancy Found'),
    ('review', 'Review'),
    ('approval', 'Approval'),
    ('reconciled', 'Reconciled'),
    ('closed', 'Closed'),
]


class BondWarehouseReconciliation(models.Model):
    _name = 'bond.warehouse.reconciliation'
    _description = 'Bond Stock Reconciliation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_to desc, id desc'

    name = fields.Char(string='Reference', default='/', copy=False, readonly=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda s: s.env.company,
                                 tracking=True)
    state = fields.Selection(STATES, default='draft', required=True, copy=False,
                             tracking=True, index=True)
    date_from = fields.Date(string='Period Start', required=True, tracking=True,
                            default=lambda s: fields.Date.context_today(s).replace(day=1))
    date_to = fields.Date(string='Period End', required=True, tracking=True,
                          default=fields.Date.context_today)
    # ---- scope ------------------------------------------------------
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',
                                   domain="[('company_id', '=', company_id)]")
    location_ids = fields.Many2many(
        'stock.location', 'bond_recon_location_rel', 'recon_id', 'location_id',
        string='Locations', domain="[('usage', '=', 'internal')]",
        help="Selected locations and all their children. Empty = all internal locations "
             "matching the other scope filters.")
    bond_classification = fields.Selection(
        [('all', 'All Internal Locations'), ('bonded', 'Bonded Only'), ('non_bonded', 'Non-Bonded Only')],
        string='Bond Classification', default='bonded', required=True)
    product_ids = fields.Many2many('product.product', 'bond_recon_product_rel', 'recon_id',
                                   'product_id', string='Products')
    lot_ids = fields.Many2many('stock.lot', 'bond_recon_lot_rel', 'recon_id', 'lot_id',
                               string='Lots/Batches')
    license_ref = fields.Char(string='License')
    lc_ref = fields.Char(string='LC Reference')
    boe_ref = fields.Char(string='Bill of Entry')
    entitlement_ref = fields.Char(string='Entitlement')
    tolerance = fields.Float(string='Tolerance', default=0.0, digits='Product Unit of Measure',
                             help="Differences up to this quantity (product UoM) are not discrepancies.")
    # ---- results ----------------------------------------------------
    line_ids = fields.One2many('bond.warehouse.reconciliation.line', 'reconciliation_id', string='Lines')
    line_count = fields.Integer(compute='_compute_line_count')
    discrepancy_count = fields.Integer(compute='_compute_counts', store=True)
    unapproved_adjustment_count = fields.Integer(compute='_compute_counts', store=True)
    system_check_applicable = fields.Boolean(readonly=True, copy=False)
    computed_on = fields.Datetime(readonly=True, copy=False)
    computed_by = fields.Many2one('res.users', readonly=True, copy=False)
    notes = fields.Text()
    # ---- workflow audit ---------------------------------------------
    prepared_by_id = fields.Many2one('res.users', string='Prepared By', readonly=True, copy=False,
                                     default=lambda s: s.env.user)
    reviewer_id = fields.Many2one('res.users', string='Reviewed By', readonly=True, copy=False)
    reviewed_on = fields.Datetime(readonly=True, copy=False)
    approver_id = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    approved_on = fields.Datetime(readonly=True, copy=False)
    closed_on = fields.Datetime(readonly=True, copy=False)
    reopen_ids = fields.One2many('bond.warehouse.reconciliation.reopen', 'reconciliation_id',
                                 string='Reopen History', readonly=True)
    reopen_count = fields.Integer(compute='_compute_reopen_count')

    _sql_constraints = [
        ('date_check', 'CHECK(date_from <= date_to)', 'Period start must not be after period end.'),
    ]

    # ------------------------------------------------------------------
    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.depends('line_ids.has_discrepancy', 'line_ids.unapproved_adjustment_qty')
    def _compute_counts(self):
        for rec in self:
            rec.discrepancy_count = len(rec.line_ids.filtered('has_discrepancy'))
            rec.unapproved_adjustment_count = len(
                rec.line_ids.filtered(lambda l: l.unapproved_adjustment_qty))

    @api.depends('reopen_ids')
    def _compute_reopen_count(self):
        for rec in self:
            rec.reopen_count = len(rec.reopen_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('bond.warehouse.reconciliation') or '/'
        return super().create(vals_list)

    def unlink(self):
        if any(rec.state != 'draft' for rec in self):
            raise UserError(_("Only draft reconciliations can be deleted. Close or reopen others instead."))
        return super().unlink()

    def write(self, vals):
        scope_fields = {'company_id', 'date_from', 'date_to', 'warehouse_id', 'location_ids',
                        'bond_classification', 'product_ids', 'lot_ids', 'license_ref', 'lc_ref',
                        'boe_ref', 'entitlement_ref', 'tolerance'}
        if scope_fields & set(vals) and any(r.state not in EDITABLE_STATES for r in self):
            raise UserError(_("The scope can only be changed while the reconciliation is in "
                              "Draft, In Progress or Discrepancy Found state."))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Scope helpers
    # ------------------------------------------------------------------
    def _get_scope_location_ids(self):
        self.ensure_one()
        domain = [('usage', '=', 'internal'),
                  ('company_id', 'in', [self.company_id.id, False])]
        if self.location_ids:
            domain.append(('id', 'child_of', self.location_ids.ids))
        if self.warehouse_id and self.warehouse_id.view_location_id.parent_path:
            domain.append(('parent_path', '=like',
                           self.warehouse_id.view_location_id.parent_path + '%'))
        if self.bond_classification != 'all':
            domain.append(('bond_scope_effective', '=', self.bond_classification))
        return self.env['stock.location'].search(domain).ids

    def _get_period_bounds(self):
        """Return naive UTC datetimes (start of first day, end of last day in user tz)."""
        self.ensure_one()
        tz = pytz.timezone(self.env.user.tz or 'UTC')
        start = tz.localize(datetime.combine(self.date_from, time.min)).astimezone(pytz.utc)
        end = tz.localize(datetime.combine(self.date_to, time.max)).astimezone(pytz.utc)
        return start.replace(tzinfo=None), end.replace(tzinfo=None)

    # ------------------------------------------------------------------
    # Calculation
    # ------------------------------------------------------------------
    def _compute_reconciliation_data(self):
        """Compute line values from validated stock move lines.

        Closing = Opening + Receipts + Returns In + Transfers In
                  - Issues - Returns Out - Transfers Out + Approved Adjustments

        Stock scope: validated (done) move lines only; movements between two
        locations that are both inside the scope are ignored (net zero), so
        internal transfers never change the scoped total. Transfers In/Out are the
        movements crossing the scope boundary from/to other internal locations and
        are zero whenever the scope is closed. Unapproved adjustments are excluded
        from the closing quantity and reported separately.
        """
        self.ensure_one()
        scope = self._get_scope_location_ids()
        if not scope:
            raise UserError(_("The selected scope contains no internal locations. "
                              "Check warehouse, locations and bond classification."))
        start, end = self._get_period_bounds()
        params = {'company': self.company_id.id, 'scope': scope, 'start': start, 'end': end}
        where = ["l.company_id = %(company)s",
                 "l.location_id = ANY(%(scope)s)",
                 "NOT (l.counterpart_location_id = ANY(%(scope)s))"]
        quant_where = ["q.company_id = %(company)s", "q.location_id = ANY(%(scope)s)"]
        if self.product_ids:
            params['products'] = self.product_ids.ids
            where.append("l.product_id = ANY(%(products)s)")
            quant_where.append("q.product_id = ANY(%(products)s)")
        if self.lot_ids:
            params['lots'] = self.lot_ids.ids
            where.append("l.lot_id = ANY(%(lots)s)")
            quant_where.append("q.lot_id = ANY(%(lots)s)")
        trace_filters = False
        for fname, col in (('license_ref', 'license_ref'), ('lc_ref', 'lc_ref'),
                           ('boe_ref', 'boe_ref'), ('entitlement_ref', 'entitlement_ref')):
            value = (self[fname] or '').strip()
            if value:
                trace_filters = True
                params[fname] = value
                where.append("l.%s = %%(%s)s" % (col, fname))

        signed = "(CASE WHEN l.side = 'in' THEN l.qty ELSE -l.qty END)"
        in_period = "(l.date >= %(start)s AND l.date <= %(end)s)"
        counted = "(l.move_type <> 'adjustment' OR l.adj_approved)"
        query = """
            SELECT l.product_id, l.lot_id,
                SUM(CASE WHEN l.date < %(start)s AND {counted} THEN {signed} ELSE 0 END) AS opening_qty,
                SUM(CASE WHEN {period} AND l.move_type = 'receipt' THEN l.qty ELSE 0 END) AS receipt_qty,
                SUM(CASE WHEN {period} AND l.move_type = 'return_in' THEN l.qty ELSE 0 END) AS return_in_qty,
                SUM(CASE WHEN {period} AND l.move_type = 'transfer' AND l.side = 'in' THEN l.qty ELSE 0 END) AS transfer_in_qty,
                SUM(CASE WHEN {period} AND l.move_type = 'issue' THEN l.qty ELSE 0 END) AS issue_qty,
                SUM(CASE WHEN {period} AND l.move_type = 'return_out' THEN l.qty ELSE 0 END) AS return_out_qty,
                SUM(CASE WHEN {period} AND l.move_type = 'transfer' AND l.side = 'out' THEN l.qty ELSE 0 END) AS transfer_out_qty,
                SUM(CASE WHEN {period} AND l.move_type = 'adjustment' AND l.adj_approved THEN {signed} ELSE 0 END) AS adjustment_qty,
                SUM(CASE WHEN l.date <= %(end)s AND l.move_type = 'adjustment' AND NOT l.adj_approved THEN {signed} ELSE 0 END) AS unapproved_adjustment_qty,
                SUM(CASE WHEN l.date > %(end)s THEN {signed} ELSE 0 END) AS after_net_qty,
                STRING_AGG(DISTINCT l.lc_ref, ', ') AS lc_refs,
                STRING_AGG(DISTINCT l.boe_ref, ', ') AS boe_refs,
                STRING_AGG(DISTINCT l.license_ref, ', ') AS license_refs
              FROM ({base}) l
             WHERE {where}
             GROUP BY l.product_id, l.lot_id
        """.format(counted=counted, signed=signed, period=in_period,
                   base=ledger_base_sql(), where=' AND '.join(where))
        cr = self.env.cr
        cr.execute(query, params)
        rows = {(r['product_id'], r['lot_id'] or 0): dict(r) for r in cr.dictfetchall()}

        system_applicable = not trace_filters
        quants = {}
        if system_applicable:
            cr.execute("""
                SELECT q.product_id, q.lot_id, SUM(q.quantity) AS qty
                  FROM stock_quant q
                 WHERE %s
                 GROUP BY q.product_id, q.lot_id
            """ % ' AND '.join(quant_where), params)
            quants = {(r['product_id'], r['lot_id'] or 0): r['qty'] or 0.0 for r in cr.dictfetchall()}

        keys = set(rows) | {k for k, v in quants.items() if v}
        products = self.env['product.product'].browse({k[0] for k in keys})
        uom_by_product = {p.id: p.uom_id.id for p in products}
        precision_rounding = {p.id: p.uom_id.rounding for p in products}
        lines = []
        for key in sorted(keys):
            product_id, lot_id = key
            data = rows.get(key, {})
            vals = {
                'product_id': product_id,
                'lot_id': lot_id or False,
                'uom_id': uom_by_product.get(product_id),
                'opening_qty': data.get('opening_qty') or 0.0,
                'receipt_qty': data.get('receipt_qty') or 0.0,
                'return_in_qty': data.get('return_in_qty') or 0.0,
                'transfer_in_qty': data.get('transfer_in_qty') or 0.0,
                'issue_qty': data.get('issue_qty') or 0.0,
                'return_out_qty': data.get('return_out_qty') or 0.0,
                'transfer_out_qty': data.get('transfer_out_qty') or 0.0,
                'adjustment_qty': data.get('adjustment_qty') or 0.0,
                'unapproved_adjustment_qty': data.get('unapproved_adjustment_qty') or 0.0,
                'lc_refs': data.get('lc_refs') or False,
                'boe_refs': data.get('boe_refs') or False,
                'license_refs': data.get('license_refs') or False,
                'system_available': system_applicable,
                'system_qty': (quants.get(key, 0.0) - (data.get('after_net_qty') or 0.0))
                              if system_applicable else 0.0,
            }
            numeric = [v for k, v in vals.items() if k.endswith('_qty')]
            rounding = precision_rounding.get(product_id) or 0.001
            if all(float_is_zero(v, precision_rounding=rounding) for v in numeric):
                continue
            lines.append(vals)
        return lines, system_applicable

    def _compute_lines(self):
        self.ensure_one()
        lines, system_applicable = self._compute_reconciliation_data()
        # keep manual inputs across recomputation
        saved = {(l.product_id.id, l.lot_id.id or 0): (l.physical_counted, l.physical_qty, l.reason)
                 for l in self.line_ids}
        commands = [Command.clear()]
        for vals in lines:
            counted, physical, reason = saved.get((vals['product_id'], vals['lot_id'] or 0),
                                                  (False, 0.0, False))
            vals.update({'physical_counted': counted, 'physical_qty': physical, 'reason': reason})
            commands.append(Command.create(vals))
        self.with_context(bond_recon_compute=True).write({
            'line_ids': commands,
            'system_check_applicable': system_applicable,
            'computed_on': fields.Datetime.now(),
            'computed_by': self.env.user.id,
        })

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_compute(self):
        for rec in self:
            if rec.state not in EDITABLE_STATES:
                raise UserError(_("%s cannot be recalculated in its current state.", rec.name))
            rec._compute_lines()
            new_state = 'discrepancy' if rec.discrepancy_count else 'in_progress'
            if rec.state != new_state:
                rec.state = new_state
            rec.message_post(body=_("Reconciliation calculated: %(lines)s lines, %(disc)s discrepancies.",
                                    lines=rec.line_count, disc=rec.discrepancy_count))
        return True

    def action_refresh_state(self):
        """Re-evaluate Discrepancy Found / In Progress after manual physical counts."""
        for rec in self:
            if rec.state in ('in_progress', 'discrepancy'):
                rec.state = 'discrepancy' if rec.discrepancy_count else 'in_progress'
        return True

    def action_submit_review(self):
        for rec in self:
            if rec.state not in ('in_progress', 'discrepancy'):
                raise UserError(_("Only In Progress or Discrepancy Found reconciliations can be sent to review."))
            if not rec.line_ids:
                raise UserError(_("Calculate the reconciliation first."))
            missing = rec.line_ids.filtered(lambda l: l.has_discrepancy and not (l.reason or '').strip())
            if missing:
                raise UserError(_("Enter an explanation for every discrepancy before review:\n%s",
                                  '\n'.join(missing.mapped(lambda l: l.product_id.display_name))))
            rec.state = 'review'
        return True

    def action_request_approval(self):
        for rec in self:
            if rec.state != 'review':
                raise UserError(_("Only reconciliations in Review can be sent for approval."))
            rec.write({'state': 'approval', 'reviewer_id': self.env.user.id,
                       'reviewed_on': fields.Datetime.now()})
        return True

    def _check_manager(self):
        if not self.env.user.has_group(MANAGER_GROUP):
            raise UserError(_("This action requires the Bond Reconciliation Manager role."))

    def action_approve(self):
        self._check_manager()
        allow_self = self.env['ir.config_parameter'].sudo().get_param(
            'nelsis_bond_reconciliation.allow_self_approval') in ('1', 'True', 'true')
        for rec in self:
            if rec.state != 'approval':
                raise UserError(_("Only reconciliations awaiting approval can be approved."))
            if not allow_self and rec.prepared_by_id == self.env.user:
                raise UserError(_("Segregation of duties: the preparer cannot approve their own reconciliation."))
            rec.write({'state': 'reconciled', 'approver_id': self.env.user.id,
                       'approved_on': fields.Datetime.now()})
            rec.message_post(body=_("Reconciliation approved."))
        return True

    def action_close(self):
        self._check_manager()
        for rec in self:
            if rec.state != 'reconciled':
                raise UserError(_("Only Reconciled records can be closed."))
            rec.write({'state': 'closed', 'closed_on': fields.Datetime.now()})
        return True

    def action_send_back(self):
        for rec in self:
            if rec.state not in ('review', 'approval'):
                raise UserError(_("Only records in Review or Approval can be sent back."))
            rec.state = 'in_progress'
            rec.message_post(body=_("Sent back to In Progress by %s.", self.env.user.name))
        return True

    def action_open_reopen_wizard(self):
        self._check_manager()
        self.ensure_one()
        if self.state not in ('reconciled', 'closed'):
            raise UserError(_("Only Reconciled or Closed records can be reopened."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reopen Reconciliation'),
            'res_model': 'bond.reconciliation.reopen.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_reconciliation_id': self.id},
        }

    # ------------------------------------------------------------------
    def _ledger_domain(self):
        self.ensure_one()
        start, end = self._get_period_bounds()
        domain = [('company_id', '=', self.company_id.id),
                  ('location_id', 'in', self._get_scope_location_ids()),
                  ('date', '>=', start), ('date', '<=', end)]
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        if self.lot_ids:
            domain.append(('lot_id', 'in', self.lot_ids.ids))
        for fname in ('license_ref', 'lc_ref', 'boe_ref', 'entitlement_ref'):
            if self[fname]:
                domain.append((fname, '=', self[fname].strip()))
        return domain

    def action_open_ledger(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ledger - %s', self.name),
            'res_model': 'bond.warehouse.ledger',
            'view_mode': 'tree,pivot,graph',
            'domain': self._ledger_domain(),
        }

    def action_open_discrepancies(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Discrepancies - %s', self.name),
            'res_model': 'bond.warehouse.reconciliation.line',
            'view_mode': 'tree,form',
            'domain': [('reconciliation_id', '=', self.id), ('has_discrepancy', '=', True)],
        }


class BondWarehouseReconciliationLine(models.Model):
    _name = 'bond.warehouse.reconciliation.line'
    _description = 'Bond Reconciliation Line'
    _order = 'product_id, lot_id, id'

    reconciliation_id = fields.Many2one('bond.warehouse.reconciliation', required=True,
                                        ondelete='cascade', index=True)
    company_id = fields.Many2one(related='reconciliation_id.company_id', store=True, index=True)
    state = fields.Selection(related='reconciliation_id.state', store=True)
    product_id = fields.Many2one('product.product', required=True, readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Batch', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='UoM', readonly=True)
    lc_refs = fields.Char(string='LC', readonly=True)
    boe_refs = fields.Char(string='Bill of Entry', readonly=True)
    license_refs = fields.Char(string='License', readonly=True)
    opening_qty = fields.Float(string='Opening', readonly=True, digits='Product Unit of Measure')
    receipt_qty = fields.Float(string='Receipts', readonly=True, digits='Product Unit of Measure')
    return_in_qty = fields.Float(string='Returns In', readonly=True, digits='Product Unit of Measure')
    transfer_in_qty = fields.Float(string='Transfers In', readonly=True, digits='Product Unit of Measure')
    issue_qty = fields.Float(string='Issues', readonly=True, digits='Product Unit of Measure')
    return_out_qty = fields.Float(string='Returns Out', readonly=True, digits='Product Unit of Measure')
    transfer_out_qty = fields.Float(string='Transfers Out', readonly=True, digits='Product Unit of Measure')
    adjustment_qty = fields.Float(string='Approved Adj.', readonly=True, digits='Product Unit of Measure')
    closing_qty = fields.Float(string='Closing (Book)', compute='_compute_closing', store=True,
                               digits='Product Unit of Measure')
    system_available = fields.Boolean(readonly=True)
    system_qty = fields.Float(string='Odoo Stock', readonly=True, digits='Product Unit of Measure',
                              help="Standard Odoo stock.quant quantity at period end.")
    system_diff = fields.Float(string='Odoo - Book', compute='_compute_diff', store=True,
                               digits='Product Unit of Measure')
    unapproved_adjustment_qty = fields.Float(string='Unapproved Adj.', readonly=True,
                                             digits='Product Unit of Measure')
    physical_counted = fields.Boolean(string='Counted')
    physical_qty = fields.Float(string='Physical Count', digits='Product Unit of Measure')
    physical_diff = fields.Float(string='Physical - Book', compute='_compute_diff', store=True,
                                 digits='Product Unit of Measure')
    has_discrepancy = fields.Boolean(compute='_compute_diff', store=True, index=True)
    reason = fields.Text(string='Explanation')

    @api.depends('opening_qty', 'receipt_qty', 'return_in_qty', 'transfer_in_qty', 'issue_qty',
                 'return_out_qty', 'transfer_out_qty', 'adjustment_qty')
    def _compute_closing(self):
        for l in self:
            l.closing_qty = (l.opening_qty + l.receipt_qty + l.return_in_qty + l.transfer_in_qty
                             - l.issue_qty - l.return_out_qty - l.transfer_out_qty + l.adjustment_qty)

    @api.depends('closing_qty', 'system_qty', 'system_available', 'physical_counted', 'physical_qty',
                 'reconciliation_id.tolerance', 'uom_id')
    def _compute_diff(self):
        for l in self:
            rounding = l.uom_id.rounding or 0.001
            tol = l.reconciliation_id.tolerance or 0.0
            l.system_diff = (l.system_qty - l.closing_qty) if l.system_available else 0.0
            l.physical_diff = (l.physical_qty - l.closing_qty) if l.physical_counted else 0.0
            l.has_discrepancy = (
                float_compare(abs(l.system_diff), tol, precision_rounding=rounding) > 0
                or float_compare(abs(l.physical_diff), tol, precision_rounding=rounding) > 0)

    # ---- protect results once the record leaves the editable states --
    def _check_parent_editable(self):
        if self.env.context.get('bond_recon_compute'):
            return
        for l in self:
            if l.reconciliation_id.state not in EDITABLE_STATES:
                raise UserError(_("Lines of %s cannot be changed in state '%s'.",
                                  l.reconciliation_id.name, l.reconciliation_id.state))

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get('bond_recon_compute'):
            raise UserError(_("Lines are generated by the Calculate action."))
        return super().create(vals_list)

    def write(self, vals):
        self._check_parent_editable()
        allowed_manual = {'physical_counted', 'physical_qty', 'reason'}
        if not self.env.context.get('bond_recon_compute') and not self.env.su:
            if set(vals) - allowed_manual - {'closing_qty', 'system_diff', 'physical_diff', 'has_discrepancy'}:
                raise UserError(_("Only the physical count and the explanation can be edited manually."))
        return super().write(vals)

    def unlink(self):
        if not self.env.context.get('bond_recon_compute'):
            for l in self:
                if l.reconciliation_id.state != 'draft' and l.reconciliation_id.exists():
                    raise UserError(_("Reconciliation lines cannot be deleted."))
        return super().unlink()


class BondWarehouseReconciliationReopen(models.Model):
    _name = 'bond.warehouse.reconciliation.reopen'
    _description = 'Bond Reconciliation Reopen Log'
    _order = 'date desc, id desc'

    reconciliation_id = fields.Many2one('bond.warehouse.reconciliation', required=True,
                                        ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='Reopened By', required=True, readonly=True)
    date = fields.Datetime(required=True, default=fields.Datetime.now, readonly=True)
    from_state = fields.Selection(STATES, readonly=True)
    reason = fields.Text(required=True, readonly=True)

    def write(self, vals):
        raise UserError(_("The reopen history cannot be modified."))

    def unlink(self):
        if not self.env.context.get('force_cascade') and not self.env.su:
            raise UserError(_("The reopen history cannot be deleted."))
        return super().unlink()
