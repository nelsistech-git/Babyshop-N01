# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

GROUP_USER = 'nelsis_bond_movement.group_bond_movement_user'
GROUP_MANAGER = 'nelsis_bond_movement.group_bond_movement_manager'
GROUP_CONTROLLER = 'nelsis_bond_movement.group_bond_movement_controller'

MOVEMENT_TYPES = [
    ('transfer', 'Internal Transfer'),
    ('issue', 'Material Issue'),
    ('return', 'Material Return'),
    ('adjustment', 'Stock Adjustment'),
]
STATES = [
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('approved', 'Approved'),
    ('done', 'Validated'),
    ('reversed', 'Reversed'),
    ('cancel', 'Cancelled'),
]
# Fields that workflow methods may write on non-draft documents.
WORKFLOW_FIELDS = {
    'state', 'approved_by_id', 'approval_date', 'validation_date', 'move_id',
    'system_qty', 'prepared_by_id', 'reversal_reason', 'reversal_move_id',
    'reversed_by_id', 'reversal_date', 'exception_approved',
    'exception_approved_by_id', 'message_main_attachment_id',
}


class BondWarehouseMovement(models.Model):
    _name = 'bond.warehouse.movement'
    _description = 'Bonded Warehouse Stock Movement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    _check_company_auto = True

    _sql_constraints = [
        ('move_unique', 'unique(move_id)', 'A stock move can only be linked to one bond movement (duplicate posting).'),
        ('reversal_move_unique', 'unique(reversal_move_id)', 'A reversal stock move can only be linked once.'),
    ]

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------
    name = fields.Char(string='Reference', default='New', readonly=True, copy=False, index=True, tracking=True)
    movement_type = fields.Selection(MOVEMENT_TYPES, required=True, index=True, tracking=True)
    state = fields.Selection(STATES, default='draft', required=True, readonly=True,
                             copy=False, index=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, index=True,
                                 default=lambda self: self.env.company)
    date = fields.Datetime(string='Document Date', required=True, default=fields.Datetime.now, tracking=True)

    product_id = fields.Many2one('product.product', required=True, tracking=True, check_company=True,
                                 domain="[('detailed_type', '=', 'product')]")
    product_tracking = fields.Selection(related='product_id.tracking', readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Batch', tracking=True, check_company=True,
                             domain="[('product_id', '=', product_id)]")
    uom_id = fields.Many2one('uom.uom', string='UoM', related='product_id.uom_id', readonly=True)
    quantity = fields.Float(digits='Product Unit of Measure', tracking=True)
    location_id = fields.Many2one('stock.location', string='Source / Count Location',
                                  tracking=True, check_company=True)
    location_dest_id = fields.Many2one('stock.location', string='Destination Location',
                                       tracking=True, check_company=True)
    bond_classification = fields.Selection(
        [('bonded', 'Bonded'), ('non_bonded', 'Non-Bonded')],
        string='Bond Classification', required=True, default='bonded', tracking=True)
    reason = fields.Text(string='Reason')

    # References (kept as text until the shared contract fixes the LC / BoE / license relations)
    license_ref = fields.Char(string='Bond License Ref.', tracking=True)
    lc_ref = fields.Char(string='LC Ref.', tracking=True)
    boe_ref = fields.Char(string='Bill of Entry Ref.', tracking=True)

    # Approvals / audit
    prepared_by_id = fields.Many2one('res.users', string='Prepared By', readonly=True, copy=False,
                                     default=lambda self: self.env.user)
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    approval_date = fields.Datetime(readonly=True, copy=False)
    validation_date = fields.Datetime(readonly=True, copy=False)
    move_id = fields.Many2one('stock.move', string='Stock Move', readonly=True, copy=False, ondelete='restrict')

    # Transfer
    reclass_reason = fields.Text(string='Reclassification Justification',
                                 help="Mandatory when source and destination classifications differ.")

    # Issue
    operational_ref = fields.Char(string='Operational Reference')
    recipient_ref = fields.Char(string='Recipient / Department')
    support_approval_ref = fields.Char(string='Supporting Approval Ref.')
    return_ids = fields.One2many('bond.warehouse.movement', 'origin_issue_id', string='Returns')
    returned_qty = fields.Float(compute='_compute_return_stats', digits='Product Unit of Measure')
    outstanding_qty = fields.Float(compute='_compute_return_stats', digits='Product Unit of Measure')
    return_count = fields.Integer(compute='_compute_return_stats')

    # Return
    origin_issue_id = fields.Many2one(
        'bond.warehouse.movement', string='Original Issue', copy=False, tracking=True,
        domain="[('movement_type', '=', 'issue'), ('state', '=', 'done')]")
    return_condition = fields.Selection(
        [('good', 'Good / Reusable'), ('damaged', 'Damaged'), ('rejected', 'Rejected')],
        string='Condition')
    inspection_result = fields.Text()
    exception_note = fields.Text(string='Over-return Exception Justification')
    exception_approved = fields.Boolean(string='Exception Approved', readonly=True, copy=False)
    exception_approved_by_id = fields.Many2one('res.users', readonly=True, copy=False)

    # Adjustment
    count_ref = fields.Char(string='Physical Count Ref.')
    system_qty = fields.Float(string='System Quantity', digits='Product Unit of Measure', readonly=True, copy=False)
    counted_qty = fields.Float(string='Counted Quantity', digits='Product Unit of Measure')
    variance = fields.Float(compute='_compute_variance', store=True, digits='Product Unit of Measure')
    evidence_ids = fields.Many2many('ir.attachment', 'bond_movement_evidence_rel', 'movement_id',
                                    'attachment_id', string='Supporting Evidence', copy=False)

    # Reversal
    reversal_reason = fields.Text(readonly=True, copy=False)
    reversal_move_id = fields.Many2one('stock.move', string='Reversal Stock Move', readonly=True,
                                       copy=False, ondelete='restrict')
    reversed_by_id = fields.Many2one('res.users', readonly=True, copy=False)
    reversal_date = fields.Datetime(readonly=True, copy=False)

    # ------------------------------------------------------------------
    # Computes / constraints / onchange
    # ------------------------------------------------------------------
    @api.depends('counted_qty', 'system_qty')
    def _compute_variance(self):
        for rec in self:
            rec.variance = rec.counted_qty - rec.system_qty

    @api.depends('quantity', 'return_ids.state', 'return_ids.quantity')
    def _compute_return_stats(self):
        for rec in self:
            done = rec.return_ids.filtered(lambda r: r.state == 'done')
            rec.returned_qty = sum(done.mapped('quantity'))
            rec.outstanding_qty = rec.quantity - rec.returned_qty
            rec.return_count = len(rec.return_ids)

    @api.constrains('movement_type', 'quantity', 'counted_qty')
    def _check_non_negative(self):
        for rec in self:
            if rec.quantity < 0 or rec.counted_qty < 0:
                raise ValidationError(_("Quantities cannot be negative."))

    @api.constrains('lot_id', 'product_id')
    def _check_lot_product(self):
        for rec in self:
            if rec.lot_id and rec.lot_id.product_id != rec.product_id:
                raise ValidationError(_("The lot/batch does not belong to the selected product."))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.lot_id and self.lot_id.product_id != self.product_id:
            self.lot_id = False

    @api.onchange('product_id', 'lot_id', 'location_id', 'movement_type')
    def _onchange_system_qty(self):
        if self.movement_type == 'adjustment' and self.product_id and self.location_id:
            self.system_qty = self._get_onhand()

    @api.onchange('movement_type')
    def _onchange_movement_type(self):
        if self.movement_type == 'issue' and not self.location_dest_id:
            self.location_dest_id = self._consumption_location()

    @api.onchange('origin_issue_id')
    def _onchange_origin_issue_id(self):
        issue = self.origin_issue_id
        if issue:
            self.product_id = issue.product_id
            self.lot_id = issue.lot_id
            self.bond_classification = issue.bond_classification
            self.location_id = issue.location_dest_id
            self.location_dest_id = issue.location_id
            self.license_ref = issue.license_ref
            self.lc_ref = issue.lc_ref
            self.boe_ref = issue.boe_ref
            self.quantity = issue.outstanding_qty

    # ------------------------------------------------------------------
    # ORM overrides (audit protection)
    # ------------------------------------------------------------------
    @api.model
    def _consumption_location(self):
        return self.env.ref('nelsis_bond_movement.location_bond_consumption', raise_if_not_found=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            mtype = vals.get('movement_type') or self.env.context.get('default_movement_type')
            if vals.get('name', 'New') in (False, 'New') and mtype:
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'bond.warehouse.movement.%s' % mtype) or 'New'
            if mtype == 'issue' and not vals.get('location_dest_id'):
                loc = self._consumption_location()
                if loc:
                    vals['location_dest_id'] = loc.id
        return super().create(vals_list)

    def write(self, vals):
        locked_fields = set(vals) - WORKFLOW_FIELDS
        if locked_fields:
            for rec in self:
                if rec.state != 'draft':
                    raise UserError(_(
                        "%(name)s is %(state)s. Only draft documents can be edited; "
                        "reset to draft or reverse the document instead.",
                        name=rec.name, state=dict(STATES).get(rec.state)))
        if 'quantity' in vals or 'origin_issue_id' in vals:
            # Any change to a returned quantity invalidates a previous exception approval.
            vals = dict(vals, exception_approved=False, exception_approved_by_id=False)
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only draft documents can be deleted. %s keeps its audit history.", rec.name))
        return super().unlink()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _require_group(self, xmlid):
        if not self.env.su and not self.env.user.has_group(xmlid):
            raise AccessError(_("You do not have the required bond movement access rights for this action."))

    def _rounding(self):
        return self.uom_id.rounding or 0.01

    def _get_onhand(self):
        """On-hand quantity read from standard stock.quant (never stored separately)."""
        self.ensure_one()
        domain = [('product_id', '=', self.product_id.id),
                  ('location_id', 'child_of', self.location_id.id),
                  ('company_id', '=', self.company_id.id)]
        if self.lot_id:
            domain.append(('lot_id', '=', self.lot_id.id))
        return sum(self.env['stock.quant'].sudo().search(domain).mapped('quantity'))

    def _check_availability(self, location, qty):
        """Prevent negative eligible stock: reserved stock is not available."""
        self.ensure_one()
        if location.usage != 'internal':
            return
        available = self.env['stock.quant'].sudo()._get_available_quantity(
            self.product_id, location, lot_id=self.lot_id, strict=False)
        if float_compare(available, qty, precision_rounding=self._rounding()) < 0:
            raise UserError(_(
                "Insufficient eligible stock for %(product)s in %(loc)s: available %(avail)s, required %(qty)s.",
                product=self.product_id.display_name, loc=location.display_name,
                avail=available, qty=qty))

    def _check_location(self, loc, label, internal=True):
        if not loc:
            raise UserError(_("%s is required.", label))
        if loc.company_id and loc.company_id != self.company_id:
            raise UserError(_("%s belongs to another company.", label))
        if internal:
            if loc.usage != 'internal':
                raise UserError(_("%s must be an internal location.", label))
            if not loc.bond_movement_allowed:
                raise UserError(_("%(label)s (%(loc)s) is not authorized for bond movements.",
                                  label=label, loc=loc.display_name))
            if loc.bond_classification == 'unclassified':
                raise UserError(_("%(label)s (%(loc)s) has no bond classification.",
                                  label=label, loc=loc.display_name))

    def _is_reclassification(self):
        self.ensure_one()
        return (self.movement_type == 'transfer' and self.location_id and self.location_dest_id
                and self.location_id.bond_classification != self.location_dest_id.bond_classification)

    def _compliance_checks(self):
        """Extension hook: override in other Nelsis modules to evaluate configured
        compliance rules (entitlement, storage period, document validity...).
        Must raise UserError to block. No legal limits are hard-coded here."""
        self.ensure_one()
        param = self.env['ir.config_parameter'].sudo().get_param(
            'nelsis_bond_movement.require_customs_reference', 'True')
        if (self.bond_classification == 'bonded' and param.lower() in ('true', '1')
                and not (self.license_ref or self.lc_ref or self.boe_ref)):
            raise UserError(_("Bonded movements need at least one of: bond license, LC or Bill of Entry reference."))

    def _return_limit_check(self):
        self.ensure_one()
        issue = self.origin_issue_id
        already = sum(issue.return_ids.filtered(
            lambda r: r.state == 'done' and r.id != self.id).mapped('quantity'))
        outstanding = issue.quantity - already
        if float_compare(self.quantity, outstanding, precision_rounding=self._rounding()) > 0:
            if not (self.exception_approved and self.exception_note):
                raise UserError(_(
                    "Return quantity %(qty)s exceeds the outstanding quantity %(out)s of issue %(issue)s. "
                    "A documented exception approved by a Bond Classification Controller is required.",
                    qty=self.quantity, out=outstanding, issue=issue.name))

    def _check_rules(self):
        """Data and business validation, executed at submit and again at validation."""
        self.ensure_one()
        rounding = self._rounding()
        t = self.movement_type
        if not self.product_id:
            raise UserError(_("Product is required."))
        if self.product_tracking != 'none' and not self.lot_id:
            raise UserError(_("A lot/batch is required for tracked product %s.", self.product_id.display_name))
        if not self.reason:
            raise UserError(_("A reason is required."))
        if t != 'adjustment' and float_compare(self.quantity, 0.0, precision_rounding=rounding) <= 0:
            raise UserError(_("Quantity must be greater than zero."))

        if t == 'transfer':
            self._check_location(self.location_id, _("Source location"))
            self._check_location(self.location_dest_id, _("Destination location"))
            if self.location_id == self.location_dest_id:
                raise UserError(_("Source and destination must differ."))
            if self.location_id.bond_classification != self.bond_classification:
                raise UserError(_("The movement classification must match the source location classification."))
            if self._is_reclassification() and not self.reclass_reason:
                raise UserError(_("Bonded/non-bonded reclassification needs a written justification."))
        elif t == 'issue':
            self._check_location(self.location_id, _("Source location"))
            self._check_location(self.location_dest_id, _("Consumption location"), internal=False)
            if self.location_dest_id.usage == 'internal':
                raise UserError(_("An issue must leave internal stock; choose a consumption location."))
            if self.location_id.bond_classification != self.bond_classification:
                raise UserError(_("The movement classification must match the source location classification."))
            if not (self.operational_ref and self.recipient_ref and self.support_approval_ref):
                raise UserError(_("Operational reference, recipient/department and supporting approval are required."))
        elif t == 'return':
            issue = self.origin_issue_id
            if not issue or issue.state != 'done':
                raise UserError(_("A validated original issue is required."))
            if issue.product_id != self.product_id or issue.lot_id != self.lot_id:
                raise UserError(_("Product and lot/batch must match the original issue."))
            if issue.bond_classification != self.bond_classification:
                raise UserError(_("Returns cannot change the bond classification of the original issue."))
            self._check_location(self.location_id, _("Return-from location"), internal=False)
            self._check_location(self.location_dest_id, _("Return location"))
            if self.location_dest_id.bond_classification != self.bond_classification:
                raise UserError(_("The return location classification must match the movement classification."))
            if not (self.return_condition and self.inspection_result):
                raise UserError(_("Condition and inspection result are required for returns."))
            self._return_limit_check()
        elif t == 'adjustment':
            self._check_location(self.location_id, _("Count location"))
            if self.location_id.bond_classification != self.bond_classification:
                raise UserError(_("The movement classification must match the location classification."))
            if not self.count_ref:
                raise UserError(_("A physical count reference is required."))
            if not self.evidence_ids:
                raise UserError(_("Supporting evidence must be attached."))
        self._compliance_checks()

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_submit(self):
        self._require_group(GROUP_USER)
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only draft documents can be submitted."))
            if rec.movement_type == 'adjustment':
                rec.system_qty = rec._get_onhand()
                if float_is_zero(rec.counted_qty - rec.system_qty, precision_rounding=rec._rounding()):
                    raise UserError(_("Counted quantity equals the system quantity: no adjustment needed."))
            rec._check_rules()
            rec.write({'state': 'submitted', 'prepared_by_id': self.env.user.id})
            rec.message_post(body=_("Submitted for approval by %s.", self.env.user.name))
        return True

    def action_approve(self):
        self._require_group(GROUP_MANAGER)
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_("Only submitted documents can be approved."))
            if not self.env.su and rec.prepared_by_id == self.env.user:
                raise UserError(_("The preparer cannot approve their own document (maker-checker control)."))
            if rec._is_reclassification():
                rec._require_group(GROUP_CONTROLLER)
            rec.write({'state': 'approved', 'approved_by_id': self.env.user.id,
                       'approval_date': fields.Datetime.now()})
            rec.message_post(body=_("Approved by %s.", self.env.user.name))
        return True

    def action_grant_exception(self):
        self._require_group(GROUP_CONTROLLER)
        for rec in self:
            if rec.movement_type != 'return' or rec.state not in ('draft', 'submitted'):
                raise UserError(_("Exceptions apply only to draft or submitted returns."))
            if not rec.exception_note:
                raise UserError(_("Document the exception justification first."))
            rec.write({'exception_approved': True, 'exception_approved_by_id': self.env.user.id})
            rec.message_post(body=_("Over-return exception approved by %s.", self.env.user.name))
        return True

    def action_reset_draft(self):
        self._require_group(GROUP_MANAGER)
        for rec in self:
            if rec.state not in ('submitted', 'approved', 'cancel'):
                raise UserError(_("Only submitted, approved or cancelled documents can be reset."))
            rec.write({'state': 'draft', 'approved_by_id': False, 'approval_date': False})
            rec.message_post(body=_("Reset to draft by %s.", self.env.user.name))
        return True

    def action_cancel(self):
        self._require_group(GROUP_USER)
        for rec in self:
            if rec.state not in ('draft', 'submitted', 'approved'):
                raise UserError(_("Posted documents cannot be cancelled; reverse them instead."))
            rec.write({'state': 'cancel'})
            rec.message_post(body=_("Cancelled by %s.", self.env.user.name))
        return True

    def _lock_row(self):
        """Row-level lock to stop concurrent double posting."""
        self.ensure_one()
        self.flush_recordset(['state', 'move_id'])
        self.env.cr.execute("SELECT state FROM bond_warehouse_movement WHERE id = %s FOR UPDATE", (self.id,))
        self.invalidate_recordset(['state', 'move_id'])

    def action_validate(self):
        self._require_group(GROUP_MANAGER)
        for rec in self:
            rec._lock_row()
            if rec.move_id or rec.state == 'done':
                raise UserError(_("%s is already posted. Duplicate posting is blocked.", rec.name))
            if rec.state != 'approved':
                raise UserError(_("%s must be approved before validation.", rec.name))
            if rec._is_reclassification():
                rec._require_group(GROUP_CONTROLLER)
            rec._check_rules()
            move = rec._post_stock_move()
            rec.write({'state': 'done', 'move_id': move.id, 'validation_date': fields.Datetime.now()})
            rec.message_post(body=_("Validated by %(user)s; stock move %(move)s posted.",
                                    user=self.env.user.name, move=move.display_name))
        return True

    # ------------------------------------------------------------------
    # Stock posting (standard stock.move only; stock.quant is never written directly)
    # ------------------------------------------------------------------
    def _create_stock_move(self, src, dst, qty, label):
        self.ensure_one()
        company = self.company_id
        move = self.env['stock.move'].sudo().with_company(company).create({
            'name': label,
            'origin': self.name,
            'product_id': self.product_id.id,
            'product_uom': self.uom_id.id,
            'product_uom_qty': qty,
            'location_id': src.id,
            'location_dest_id': dst.id,
            'company_id': company.id,
            'is_inventory': self.movement_type == 'adjustment',
            'bond_movement_id': self.id,
        })
        move._action_confirm()
        move._do_unreserve()
        self.env['stock.move.line'].sudo().with_company(company).create({
            'move_id': move.id,
            'product_id': self.product_id.id,
            'product_uom_id': self.uom_id.id,
            'location_id': src.id,
            'location_dest_id': dst.id,
            'lot_id': self.lot_id.id or False,
            'quantity': qty,
            'company_id': company.id,
        })
        move.picked = True
        move._action_done()
        if move.state != 'done':
            raise UserError(_("The stock move for %s could not be completed.", self.name))
        return move

    def _post_stock_move(self):
        self.ensure_one()
        t = self.movement_type
        if t in ('transfer', 'issue', 'return'):
            src, dst, qty = self.location_id, self.location_dest_id, self.quantity
            self._check_availability(src, qty)
            return self._create_stock_move(src, dst, qty, self.name)
        # Adjustment
        current = self._get_onhand()
        if float_compare(current, self.system_qty, precision_rounding=self._rounding()) != 0:
            raise UserError(_(
                "Stock changed since submission (system %(old)s, now %(new)s). "
                "Reset to draft and resubmit with a fresh count.", old=self.system_qty, new=current))
        variance = self.counted_qty - current
        loss = self.product_id.with_company(self.company_id).property_stock_inventory
        if not loss:
            raise UserError(_("No inventory adjustment location is configured for the product."))
        if variance > 0:
            return self._create_stock_move(loss, self.location_id, variance, self.name)
        self._check_availability(self.location_id, -variance)
        return self._create_stock_move(self.location_id, loss, -variance, self.name)

    def action_reverse(self, reason=None):
        self._require_group(GROUP_MANAGER)
        if not reason or not reason.strip():
            raise UserError(_("A reversal reason is mandatory."))
        for rec in self:
            rec._lock_row()
            if rec.state != 'done' or not rec.move_id or rec.reversal_move_id:
                raise UserError(_("Only validated, not yet reversed documents can be reversed."))
            if rec.movement_type == 'issue' and rec.return_ids.filtered(lambda r: r.state == 'done'):
                raise UserError(_("Reverse the returns of %s first.", rec.name))
            orig = rec.move_id
            qty = orig.product_uom_qty
            rec._check_availability(orig.location_dest_id, qty)
            rev = rec._create_stock_move(orig.location_dest_id, orig.location_id, qty, "%s / REV" % rec.name)
            rec.write({'state': 'reversed', 'reversal_move_id': rev.id, 'reversal_reason': reason,
                       'reversed_by_id': self.env.user.id, 'reversal_date': fields.Datetime.now()})
            rec.message_post(body=_("Reversed by %(user)s. Reason: %(reason)s",
                                    user=self.env.user.name, reason=reason))
        return True

    # ------------------------------------------------------------------
    # Smart buttons
    # ------------------------------------------------------------------
    def action_view_stock_moves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Stock Moves'),
            'res_model': 'stock.move',
            'view_mode': 'tree,form',
            'domain': [('bond_movement_id', '=', self.id)],
        }

    def action_view_returns(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Returns'),
            'res_model': 'bond.warehouse.movement',
            'view_mode': 'tree,form',
            'domain': [('origin_issue_id', '=', self.id)],
            'context': {'default_movement_type': 'return', 'default_origin_issue_id': self.id},
        }
