# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from psycopg2 import OperationalError

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

from .reference_mixin import GROUP_APPROVER, GROUP_INSPECTOR, GROUP_USER

HEADER_DRAFT_ONLY = {'bond_status', 'partner_id', 'location_dest_id', 'picking_type_id', 'consignment_id'}
HEADER_REFERENCES = {'lc_ref', 'lc_number', 'boe_number', 'boe_date', 'customs_ref'}
LINE_DRAFT_ONLY = {'product_id', 'product_uom_id', 'declared_qty', 'consignment_line_id'}
LINE_VERIFICATION = {'hs_code'}
LINE_INSPECTION = {'received_qty', 'damaged_qty', 'rejected_qty', 'lot_name', 'expiry_date', 'inspected',
                   'measure_qty', 'measure_uom_id', 'disposition_note'}


class BondReceipt(models.Model):
    _name = 'bond.inventory.receipt'
    _inherit = ['bond.inventory.reference.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Bonded Goods Receipt'
    _order = 'id desc'

    @api.model
    def _default_picking_type(self):
        return self.env['stock.picking.type'].search(
            [('code', '=', 'incoming'), ('company_id', '=', self.env.company.id)], limit=1)

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    company_id = fields.Many2one('res.company', required=True, readonly=True, index=True,
                                 default=lambda self: self.env.company)
    bond_status = fields.Selection(
        [('bonded', 'Bonded'), ('non_bonded', 'Non-Bonded')], string='Receipt Type',
        default='bonded', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Supplier', required=True, tracking=True)
    consignment_id = fields.Many2one(
        'bond.inventory.consignment', string='Consignment', tracking=True, index=True,
        domain="[('state', '=', 'open'), ('company_id', '=', company_id)]")
    lc_ref = fields.Reference(selection='_selection_lc_models', string='LC Record')
    lc_number = fields.Char(string='LC Number', tracking=True)
    boe_number = fields.Char(string='Bill of Entry No.', tracking=True, index=True)
    boe_date = fields.Date(string='Bill of Entry Date')
    customs_ref = fields.Reference(selection='_selection_customs_models', string='Customs Document Record')
    lc_label = fields.Char(string='LC', compute='_compute_lc_label')
    picking_type_id = fields.Many2one(
        'stock.picking.type', string='Operation Type', required=True, default=_default_picking_type,
        domain="[('code', '=', 'incoming'), ('company_id', '=', company_id)]")
    location_dest_id = fields.Many2one(
        'stock.location', string='Receiving Location', required=True, tracking=True,
        domain="[('usage', '=', 'internal'), ('bond_status', '=', bond_status)]")
    receipt_date = fields.Date(default=fields.Date.context_today)
    state = fields.Selection(
        [('draft', 'Draft'), ('doc_verification', 'Document Verification'), ('inspection', 'Inspection'),
         ('approval', 'Approval'), ('ready', 'Ready for Validation'), ('done', 'Done'),
         ('rejected', 'Rejected'), ('cancelled', 'Cancelled')],
        default='draft', required=True, copy=False, readonly=True, tracking=True, index=True)
    line_ids = fields.One2many('bond.inventory.receipt.line', 'receipt_id', string='Lines', copy=True)
    document_ids = fields.One2many('bond.inventory.receipt.document', 'receipt_id', string='Documents', copy=False)
    picking_id = fields.Many2one('stock.picking', string='Stock Transfer', readonly=True, copy=False, index=True)
    picking_count = fields.Integer(compute='_compute_picking_count')
    return_count = fields.Integer(compute='_compute_picking_count')
    approval_required = fields.Boolean(compute='_compute_approval_required')
    reject_reason = fields.Text(copy=False)
    note = fields.Text()
    doc_verified_by = fields.Many2one('res.users', readonly=True, copy=False)
    doc_verified_on = fields.Datetime(readonly=True, copy=False)
    inspected_by = fields.Many2one('res.users', readonly=True, copy=False)
    inspected_on = fields.Datetime(readonly=True, copy=False)
    approved_by = fields.Many2one('res.users', readonly=True, copy=False)
    approved_on = fields.Datetime(readonly=True, copy=False)
    validated_by = fields.Many2one('res.users', readonly=True, copy=False)
    validated_on = fields.Datetime(readonly=True, copy=False)

    # -- computes ------------------------------------------------------------
    @api.depends('lc_ref', 'lc_number')
    def _compute_lc_label(self):
        for rec in self:
            rec.lc_label = rec.lc_ref.sudo().display_name if rec.lc_ref else (rec.lc_number or False)

    def _returns(self):
        self.ensure_one()
        if not self.picking_id:
            return self.env['stock.picking']
        return self.env['stock.picking'].search(
            [('move_ids.origin_returned_move_id.picking_id', '=', self.picking_id.id)])

    @api.depends('picking_id')
    def _compute_picking_count(self):
        for rec in self:
            rec.picking_count = 1 if rec.picking_id else 0
            rec.return_count = len(rec._returns()) if rec.id else 0

    @api.depends('company_id.bond_always_require_approval', 'company_id.bond_variance_tolerance_pct',
                 'line_ids.declared_qty', 'line_ids.shortage_qty', 'line_ids.excess_qty',
                 'line_ids.damaged_qty', 'line_ids.rejected_qty', 'line_ids.received_qty',
                 'line_ids.consignment_line_id')
    def _compute_approval_required(self):
        for rec in self:
            required = rec.company_id.bond_always_require_approval
            tolerance = rec.company_id.bond_variance_tolerance_pct / 100.0
            for line in rec.line_ids:
                rounding = line.product_uom_id.rounding or 0.01
                allowed = line.declared_qty * tolerance
                if (float_compare(line.shortage_qty, allowed, precision_rounding=rounding) > 0
                        or float_compare(line.excess_qty, allowed, precision_rounding=rounding) > 0
                        or not float_is_zero(line.damaged_qty, precision_rounding=rounding)
                        or not float_is_zero(line.rejected_qty, precision_rounding=rounding)
                        or line.over_consignment):
                    required = True
                    break
            rec.approval_required = required

    # -- onchange / ORM ------------------------------------------------------
    @api.onchange('consignment_id')
    def _onchange_consignment_id(self):
        cons = self.consignment_id
        if cons:
            self.partner_id = cons.partner_id
            self.lc_ref = cons.lc_ref
            self.lc_number = cons.lc_number
            self.boe_number = cons.boe_number
            self.boe_date = cons.boe_date
            self.customs_ref = cons.customs_ref

    @api.onchange('bond_status')
    def _onchange_bond_status(self):
        if self.location_dest_id and self.location_dest_id.bond_status != self.bond_status:
            self.location_dest_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('bond.inventory.receipt') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        keys = set(vals)
        for rec in self:
            if keys & HEADER_DRAFT_ONLY and rec.state != 'draft':
                raise UserError(_('These fields can only be changed while the receipt is in Draft.'))
            if keys & HEADER_REFERENCES and rec.state not in ('draft', 'doc_verification'):
                raise UserError(_('LC / Bill of Entry references can only be changed in Draft or '
                                  'Document Verification.'))
        return super().write(vals)

    def unlink(self):
        if any(rec.state not in ('draft', 'cancelled') for rec in self):
            raise UserError(_('Only draft or cancelled receipts can be deleted. Receipt history is retained.'))
        return super().unlink()

    # -- constraints ---------------------------------------------------------
    @api.constrains('bond_status', 'location_dest_id')
    def _check_location_status(self):
        for rec in self:
            if rec.location_dest_id.bond_status != rec.bond_status:
                raise ValidationError(_(
                    'Location "%(loc)s" is %(have)s but the receipt is %(want)s.',
                    loc=rec.location_dest_id.display_name,
                    have=dict(rec.location_dest_id._fields['bond_status'].selection)[rec.location_dest_id.bond_status],
                    want=dict(rec._fields['bond_status'].selection)[rec.bond_status]))

    @api.constrains('picking_type_id')
    def _check_picking_type(self):
        for rec in self:
            if rec.picking_type_id.code != 'incoming':
                raise ValidationError(_('The operation type must be a receipt (incoming).'))

    # -- helpers -------------------------------------------------------------
    def _assert_state(self, *states):
        for rec in self:
            if rec.state not in states:
                raise UserError(_('Receipt %(name)s is in state "%(state)s"; expected: %(exp)s.',
                                  name=rec.name, state=dict(rec._fields['state'].selection)[rec.state],
                                  exp=', '.join(dict(rec._fields['state'].selection)[s] for s in states)))

    def _lock_for_update(self):
        """Serialise concurrent validations of the same receipt."""
        try:
            with self.env.cr.savepoint(flush=False):
                self.env.cr.execute(
                    'SELECT id FROM bond_inventory_receipt WHERE id IN %s FOR UPDATE NOWAIT', (tuple(self.ids),))
        except OperationalError:
            raise UserError(_('Receipt is being processed by another user. Please retry.'))
        self.invalidate_recordset(['state', 'picking_id'])

    def _check_maker_checker(self):
        if self.env.su or self._bond_is_manager():
            return
        for rec in self:
            if rec.create_uid == self.env.user:
                raise UserError(_('The creator of a receipt cannot approve it (segregation of duties).'))

    def _fill_from_consignment(self):
        for rec in self:
            cons = rec.consignment_id
            if not cons:
                continue
            if cons.state != 'open':
                raise UserError(_('Consignment %s is not open.', cons.name))
            vals = {}
            for fname in ('lc_ref', 'lc_number', 'boe_number', 'boe_date', 'customs_ref'):
                if not rec[fname] and cons[fname]:
                    vals[fname] = cons[fname]
            if vals:
                rec.write(vals)

    def _check_header(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('Add at least one receipt line.'))
        if self.bond_status == 'bonded':
            if not (self.lc_ref or self.lc_number):
                raise UserError(_('An LC reference or number is required for a bonded receipt.'))
            if not self.boe_number:
                raise UserError(_('The Bill of Entry number is required for a bonded receipt.'))
            if not self.location_dest_id._bond_is_authorized():
                raise UserError(_('Location "%s" is not bond-authorized today (license missing, not yet '
                                  'valid or expired).', self.location_dest_id.display_name))
        elif self.location_dest_id.bond_status != 'non_bonded':
            raise UserError(_('A non-bonded receipt cannot use a bonded location.'))
        for line in self.line_ids:
            line._check_for_status()

    def _check_ready(self):
        """Final checks right before posting stock."""
        self.ensure_one()
        self._check_header()
        seen = set()
        for line in self.line_ids:
            rounding = line.product_uom_id.rounding or 0.01
            if float_compare(line.accepted_qty, 0.0, precision_rounding=rounding) <= 0:
                continue
            tracked = line.product_id.tracking != 'none'
            if tracked:
                if not line.lot_name:
                    raise UserError(_('Lot / batch number is required for "%s".', line.product_id.display_name))
                key = (line.product_id.id, line.lot_name)
                if key in seen:
                    raise UserError(_('Lot "%(lot)s" of "%(product)s" appears twice in this receipt.',
                                      lot=line.lot_name, product=line.product_id.display_name))
                seen.add(key)
            if line.product_id.product_tmpl_id.bond_requires_expiry and not line.expiry_date:
                raise UserError(_('Expiry date is required for "%s".', line.product_id.display_name))

    # -- workflow ------------------------------------------------------------
    def action_submit_verification(self):
        self._bond_check_group(GROUP_USER)
        for rec in self:
            rec._assert_state('draft')
            rec._fill_from_consignment()
            rec._check_header()
            rec.state = 'doc_verification'
            rec.message_post(body=_('Submitted for document verification.'))
        return True

    def action_verify_documents(self):
        self._bond_check_group(GROUP_INSPECTOR)
        for rec in self:
            rec._assert_state('doc_verification')
            rec._check_header()
            if rec.bond_status == 'bonded':
                if not rec.document_ids:
                    raise UserError(_('Attach and verify the customs documents first.'))
                if rec.document_ids.filtered(lambda d: not d.verified):
                    raise UserError(_('All listed documents must be verified.'))
                required = self.env['bond.inventory.document.type'].search([('required_for_bonded', '=', True)])
                missing = required - rec.document_ids.mapped('type_id')
                if missing:
                    raise UserError(_('Missing required document type(s): %s.',
                                      ', '.join(missing.mapped('name'))))
            rec.write({'state': 'inspection', 'doc_verified_by': self.env.user.id,
                       'doc_verified_on': fields.Datetime.now()})
            rec.message_post(body=_('Documents verified.'))
        return True

    def action_mark_all_inspected(self):
        self._bond_check_group(GROUP_INSPECTOR)
        for rec in self:
            rec._assert_state('inspection')
            rec.line_ids.write({'inspected': True})
        return True

    def action_complete_inspection(self):
        self._bond_check_group(GROUP_INSPECTOR)
        for rec in self:
            rec._assert_state('inspection')
            if rec.line_ids.filtered(lambda l: not l.inspected):
                raise UserError(_('Every line must be inspected.'))
            rec._check_ready()
            if all(float_compare(l.accepted_qty, 0.0, precision_rounding=l.product_uom_id.rounding or 0.01) <= 0
                   for l in rec.line_ids):
                raise UserError(_('No accepted quantity: use Reject to refuse the whole receipt.'))
            vals = {'inspected_by': self.env.user.id, 'inspected_on': fields.Datetime.now()}
            if rec.approval_required:
                vals['state'] = 'approval'
                rec.write(vals)
                rec.message_post(body=_('Inspection completed. Approval is required (variance, damaged or '
                                        'rejected goods, or policy).'))
            else:
                vals['state'] = 'ready'
                rec.write(vals)
                rec.message_post(body=_('Inspection completed. Ready for validation.'))
        return True

    def action_approve(self):
        self._bond_check_group(GROUP_APPROVER)
        self._check_maker_checker()
        for rec in self:
            rec._assert_state('approval')
            rec.write({'state': 'ready', 'approved_by': self.env.user.id,
                       'approved_on': fields.Datetime.now()})
            rec.message_post(body=_('Receipt approved.'))
        return True

    def action_reject(self):
        self._bond_check_group(GROUP_INSPECTOR)
        for rec in self:
            rec._assert_state('doc_verification', 'inspection', 'approval')
            if not rec.reject_reason:
                raise UserError(_('Enter the rejection reason first.'))
            rec.state = 'rejected'
            rec.message_post(body=_('Receipt rejected: %s', rec.reject_reason))
        return True

    def action_cancel(self):
        self._bond_check_group(GROUP_USER)
        for rec in self:
            rec._assert_state('draft', 'doc_verification', 'inspection', 'approval', 'ready')
            if rec.picking_id and rec.picking_id.state not in ('cancel',):
                rec.picking_id.with_context(bond_receipt_cancel=True).action_cancel()
            rec.state = 'cancelled'
        return True

    def action_reset_draft(self):
        self._bond_check_group(GROUP_USER)
        for rec in self:
            rec._assert_state('rejected', 'cancelled')
            rec.write({'state': 'draft', 'reject_reason': False})
        return True

    def action_validate(self):
        self._bond_check_group(GROUP_USER)
        for rec in self:
            rec._lock_for_update()
            if rec.state == 'done' or rec.picking_id:
                raise UserError(_('Receipt %s has already been validated; stock is not posted twice.', rec.name))
            rec._assert_state('ready')
            rec._check_ready()
            rec._post_stock()
        return True

    # -- stock posting -------------------------------------------------------
    def _accepted_lines(self):
        return self.line_ids.filtered(
            lambda l: float_compare(l.accepted_qty, 0.0, precision_rounding=l.product_uom_id.rounding or 0.01) > 0)

    def _prepare_lots(self, lines):
        self.ensure_one()
        Lot = self.env['stock.lot'].with_context(bond_classification_apply=True)
        for line in lines:
            if line.product_id.tracking == 'none':
                continue
            lot = Lot.search([('name', '=', line.lot_name), ('product_id', '=', line.product_id.id),
                              ('company_id', '=', self.company_id.id)], limit=1)
            if lot:
                if lot.bond_status != self.bond_status:
                    raise UserError(_('Lot "%(lot)s" already exists as %(have)s stock; it cannot be received '
                                      'as %(want)s.', lot=lot.name,
                                      have=dict(lot._fields['bond_status'].selection)[lot.bond_status],
                                      want=dict(self._fields['bond_status'].selection)[self.bond_status]))
                if self.bond_status == 'bonded' and lot.bond_boe_number != self.boe_number:
                    raise UserError(_('Lot "%(lot)s" is already linked to Bill of Entry "%(boe)s".',
                                      lot=lot.name, boe=lot.bond_boe_number or '-'))
                if line.expiry_date:
                    if lot.bond_expiry_date and lot.bond_expiry_date != line.expiry_date:
                        raise UserError(_('Lot "%s" already has a different expiry date.', lot.name))
                    lot.bond_expiry_date = line.expiry_date
            else:
                lot = Lot.create({
                    'name': line.lot_name,
                    'product_id': line.product_id.id,
                    'company_id': self.company_id.id,
                    'bond_status': self.bond_status,
                    'bond_receipt_id': self.id,
                    'bond_consignment_id': self.consignment_id.id,
                    'bond_lc_label': self.lc_label,
                    'bond_boe_number': self.boe_number,
                    'bond_hs_code': line.hs_code,
                    'bond_expiry_date': line.expiry_date,
                })
            line.lot_id = lot

    def _source_location(self):
        self.ensure_one()
        src = self.picking_type_id.default_location_src_id or self.partner_id.property_stock_supplier
        if not src:
            raise UserError(_('No source (vendor) location is configured for the operation type or supplier.'))
        return src

    def _post_stock(self):
        """Create, confirm and validate the standard receipt picking. Called once per receipt."""
        self.ensure_one()
        lines = self._accepted_lines()
        self._prepare_lots(lines)
        src = self._source_location()
        groups = {}
        for line in lines:
            groups.setdefault((line.product_id, line.product_uom_id), self.env['bond.inventory.receipt.line'])
            groups[(line.product_id, line.product_uom_id)] |= line
        move_vals = [(0, 0, {
            'name': product.display_name,
            'product_id': product.id,
            'product_uom': uom.id,
            'product_uom_qty': sum(group.mapped('accepted_qty')),
            'location_id': src.id,
            'location_dest_id': self.location_dest_id.id,
            'company_id': self.company_id.id,
            'origin': self.name,
        }) for (product, uom), group in groups.items()]
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'location_id': src.id,
            'location_dest_id': self.location_dest_id.id,
            'company_id': self.company_id.id,
            'bond_receipt_id': self.id,
            'move_ids': move_vals,
        })
        picking.action_confirm()
        picking.move_line_ids.unlink()
        moves = {(m.product_id.id, m.product_uom.id): m for m in picking.move_ids}
        MoveLine = self.env['stock.move.line']
        for line in lines:
            move = moves[(line.product_id.id, line.product_uom_id.id)]
            MoveLine.create({
                'move_id': move.id,
                'picking_id': picking.id,
                'product_id': line.product_id.id,
                'product_uom_id': line.product_uom_id.id,
                'quantity': line.accepted_qty,
                'lot_id': line.lot_id.id or False,
                'location_id': src.id,
                'location_dest_id': self.location_dest_id.id,
                'company_id': self.company_id.id,
                'picked': True,
            })
            line.move_id = move
        picking.with_context(bond_receipt_validate=True, skip_backorder=True).button_validate()
        if picking.state != 'done':
            raise UserError(_('The stock transfer %s could not be validated.', picking.name))
        self.write({'state': 'done', 'picking_id': picking.id, 'validated_by': self.env.user.id,
                    'validated_on': fields.Datetime.now()})
        self.message_post(body=_('Receipt validated. Stock transfer %s done.', picking.name))

    # -- navigation ----------------------------------------------------------
    def action_view_picking(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'stock.picking', 'view_mode': 'form',
                'res_id': self.picking_id.id}

    def action_view_returns(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'stock.picking', 'name': _('Returns'),
                'view_mode': 'tree,form', 'domain': [('id', 'in', self._returns().ids)]}

    def action_return(self):
        """Open the standard return wizard on the validated transfer (no custom stock logic)."""
        self.ensure_one()
        self._assert_state('done')
        return {'type': 'ir.actions.act_window', 'res_model': 'stock.return.picking', 'view_mode': 'form',
                'target': 'new', 'context': {'active_id': self.picking_id.id, 'active_model': 'stock.picking'}}


class BondReceiptLine(models.Model):
    _name = 'bond.inventory.receipt.line'
    _description = 'Bonded Goods Receipt Line'
    _order = 'receipt_id, sequence, id'

    receipt_id = fields.Many2one('bond.inventory.receipt', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(related='receipt_id.company_id', store=True, index=True)
    state = fields.Selection(related='receipt_id.state', store=True)
    consignment_line_id = fields.Many2one(
        'bond.inventory.consignment.line', string='Consignment Line', index=True)
    product_id = fields.Many2one('product.product', required=True, index=True,
                                 domain=[('detailed_type', '=', 'product')])
    product_tracking = fields.Selection(related='product_id.tracking')
    requires_expiry = fields.Boolean(related='product_id.product_tmpl_id.bond_requires_expiry')
    hs_code = fields.Char(string='HS Code', compute='_compute_hs_code', store=True, readonly=False,
                          precompute=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True,
                                     compute='_compute_product_uom_id', store=True, readonly=False,
                                     precompute=True)
    declared_qty = fields.Float(string='Declared Qty', digits='Product Unit of Measure')
    received_qty = fields.Float(string='Received Qty', digits='Product Unit of Measure')
    damaged_qty = fields.Float(string='Damaged Qty', digits='Product Unit of Measure')
    rejected_qty = fields.Float(string='Rejected Qty', digits='Product Unit of Measure')
    accepted_qty = fields.Float(string='Accepted Qty', digits='Product Unit of Measure',
                                compute='_compute_quantities', store=True)
    shortage_qty = fields.Float(string='Shortage', digits='Product Unit of Measure',
                                compute='_compute_quantities', store=True)
    excess_qty = fields.Float(string='Excess', digits='Product Unit of Measure',
                              compute='_compute_quantities', store=True)
    over_consignment = fields.Boolean(compute='_compute_over_consignment')
    lot_name = fields.Char(string='Lot / Batch No.')
    lot_id = fields.Many2one('stock.lot', string='Lot / Batch', readonly=True, copy=False)
    expiry_date = fields.Date()
    inspected = fields.Boolean(copy=False)
    inspection_result = fields.Selection(
        [('pending', 'Pending'), ('passed', 'Passed'), ('partial', 'Partially Accepted'), ('failed', 'Failed')],
        compute='_compute_inspection_result', store=True)
    measure_qty = fields.Float(string='Measured Qty', digits='Product Unit of Measure',
                               help='Informational measurement (e.g. area of hides received in pieces). '
                                    'It is never converted to the stock quantity.')
    measure_uom_id = fields.Many2one('uom.uom', string='Measured Unit')
    disposition_note = fields.Char(string='Damaged / Rejected Disposition')
    move_id = fields.Many2one('stock.move', string='Stock Move', readonly=True, copy=False)

    @api.depends('product_id')
    def _compute_hs_code(self):
        for line in self:
            line.hs_code = line.product_id.bond_hs_code or line.hs_code

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        for line in self:
            line.product_uom_id = line.product_id.uom_id

    @api.depends('declared_qty', 'received_qty', 'damaged_qty', 'rejected_qty', 'product_uom_id')
    def _compute_quantities(self):
        for line in self:
            rounding = line.product_uom_id.rounding or 0.01
            accepted = line.received_qty - line.damaged_qty - line.rejected_qty
            line.accepted_qty = accepted if float_compare(accepted, 0.0, precision_rounding=rounding) > 0 else 0.0
            diff = line.declared_qty - line.received_qty
            line.shortage_qty = diff if float_compare(diff, 0.0, precision_rounding=rounding) > 0 else 0.0
            line.excess_qty = -diff if float_compare(diff, 0.0, precision_rounding=rounding) < 0 else 0.0

    @api.depends('received_qty', 'consignment_line_id.remaining_qty', 'receipt_id.state')
    def _compute_over_consignment(self):
        for line in self:
            cl = line.consignment_line_id
            line.over_consignment = bool(
                cl and line.receipt_id.state != 'done'
                and float_compare(line.received_qty, cl.remaining_qty,
                                  precision_rounding=line.product_uom_id.rounding or 0.01) > 0)

    @api.depends('inspected', 'received_qty', 'declared_qty', 'accepted_qty', 'damaged_qty', 'rejected_qty')
    def _compute_inspection_result(self):
        for line in self:
            rounding = line.product_uom_id.rounding or 0.01
            if not line.inspected:
                line.inspection_result = 'pending'
            elif float_is_zero(line.accepted_qty, precision_rounding=rounding):
                line.inspection_result = 'failed'
            elif (float_compare(line.accepted_qty, line.declared_qty, precision_rounding=rounding) == 0
                  and float_is_zero(line.damaged_qty, precision_rounding=rounding)
                  and float_is_zero(line.rejected_qty, precision_rounding=rounding)):
                line.inspection_result = 'passed'
            else:
                line.inspection_result = 'partial'

    @api.onchange('consignment_line_id')
    def _onchange_consignment_line_id(self):
        cl = self.consignment_line_id
        if cl:
            self.product_id = cl.product_id
            self.product_uom_id = cl.product_uom_id
            self.hs_code = cl.hs_code
            self.declared_qty = cl.remaining_qty

    # -- ORM guards ----------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            receipt = self.env['bond.inventory.receipt'].browse(vals.get('receipt_id'))
            if receipt and receipt.state != 'draft':
                raise UserError(_('Lines can only be added while the receipt is in Draft.'))
        return super().create(vals_list)

    def write(self, vals):
        keys = set(vals)
        for line in self:
            state = line.receipt_id.state
            if keys & LINE_DRAFT_ONLY and state != 'draft':
                raise UserError(_('Product, unit, declared quantity and consignment line can only be '
                                  'changed in Draft.'))
            if keys & LINE_VERIFICATION and state not in ('draft', 'doc_verification'):
                raise UserError(_('The HS code can only be changed in Draft or Document Verification.'))
            if keys & LINE_INSPECTION and state != 'inspection':
                raise UserError(_('Inspection results can only be recorded in the Inspection stage.'))
        return super().write(vals)

    def unlink(self):
        if any(line.receipt_id.state != 'draft' for line in self):
            raise UserError(_('Lines can only be deleted while the receipt is in Draft.'))
        return super().unlink()

    # -- constraints ---------------------------------------------------------
    @api.constrains('declared_qty', 'received_qty', 'damaged_qty', 'rejected_qty')
    def _check_quantities(self):
        for line in self:
            rounding = line.product_uom_id.rounding or 0.01
            for label, qty in ((_('Declared'), line.declared_qty), (_('Received'), line.received_qty),
                               (_('Damaged'), line.damaged_qty), (_('Rejected'), line.rejected_qty)):
                if float_compare(qty, 0.0, precision_rounding=rounding) < 0:
                    raise ValidationError(_('%s quantity cannot be negative.', label))
            if float_compare(line.damaged_qty + line.rejected_qty, line.received_qty,
                             precision_rounding=rounding) > 0:
                raise ValidationError(_('Damaged plus rejected quantity cannot exceed the received quantity '
                                        'of "%s".', line.product_id.display_name))

    @api.constrains('product_id', 'product_uom_id', 'measure_qty', 'measure_uom_id')
    def _check_uom(self):
        for line in self:
            if line.product_uom_id.category_id != line.product_id.uom_id.category_id:
                raise ValidationError(_(
                    'The unit of "%s" must be in the same category as the product unit. Pieces are never '
                    'converted to area or weight without a configured conversion.',
                    line.product_id.display_name))
            if line.measure_qty and not line.measure_uom_id:
                raise ValidationError(_('Select the unit of the measured quantity.'))
            if line.measure_qty < 0:
                raise ValidationError(_('The measured quantity cannot be negative.'))

    @api.constrains('consignment_line_id', 'product_id', 'product_uom_id', 'receipt_id')
    def _check_consignment_line(self):
        for line in self:
            cl = line.consignment_line_id
            if not cl:
                continue
            if cl.consignment_id != line.receipt_id.consignment_id:
                raise ValidationError(_('The consignment line belongs to another consignment.'))
            if cl.product_id != line.product_id or cl.product_uom_id != line.product_uom_id:
                raise ValidationError(_('Product and unit must match the consignment line.'))

    def _check_for_status(self):
        """Eligibility rules depending on the receipt type."""
        self.ensure_one()
        receipt = self.receipt_id
        if receipt.bond_status == 'bonded':
            tmpl = self.product_id.product_tmpl_id
            if not tmpl.bond_eligible:
                raise UserError(_('Product "%s" is not bond-eligible. Imported goods are not bonded '
                                  'automatically; use a Bond Classification Request.',
                                  self.product_id.display_name))
            if self.product_id.tracking not in ('lot', 'serial'):
                raise UserError(_('Product "%s" must be lot/serial tracked.', self.product_id.display_name))
            if not self.hs_code:
                raise UserError(_('HS code is required for "%s".', self.product_id.display_name))


class BondReceiptDocument(models.Model):
    _name = 'bond.inventory.receipt.document'
    _inherit = ['bond.inventory.reference.mixin']
    _description = 'Bond Receipt Supporting Document'
    _order = 'receipt_id, id'

    receipt_id = fields.Many2one('bond.inventory.receipt', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='receipt_id.company_id', store=True, index=True)
    type_id = fields.Many2one('bond.inventory.document.type', string='Document Type', required=True)
    reference = fields.Char(string='Document No.', required=True)
    document_date = fields.Date()
    customs_ref = fields.Reference(selection='_selection_customs_models', string='Customs Document Record')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'bond_inv_receipt_doc_attachment_rel', 'document_id', 'attachment_id',
        string='Attachments')
    verified = fields.Boolean(readonly=True, copy=False)
    verified_by = fields.Many2one('res.users', readonly=True, copy=False)
    verified_on = fields.Datetime(readonly=True, copy=False)
    note = fields.Char()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            receipt = self.env['bond.inventory.receipt'].browse(vals.get('receipt_id'))
            if receipt and receipt.state in ('ready', 'done', 'rejected', 'cancelled'):
                raise UserError(_('Documents cannot be added at this stage of the receipt.'))
        return super().create(vals_list)

    def write(self, vals):
        content = {'type_id', 'reference', 'document_date', 'attachment_ids', 'customs_ref'}
        for doc in self:
            if doc.receipt_id.state in ('ready', 'done', 'rejected', 'cancelled'):
                raise UserError(_('Documents are locked at this stage of the receipt.'))
            if doc.verified and content & set(vals) and not self.env.context.get('bond_doc_reverify'):
                raise UserError(_('A verified document cannot be edited. Reset its verification first.'))
        return super().write(vals)

    def unlink(self):
        if any(doc.receipt_id.state in ('ready', 'done', 'rejected', 'cancelled') or doc.verified for doc in self):
            raise UserError(_('Verified or locked documents cannot be deleted.'))
        return super().unlink()

    def action_verify(self):
        self._bond_check_group(GROUP_INSPECTOR)
        for doc in self:
            if doc.receipt_id.state != 'doc_verification':
                raise UserError(_('Documents are verified during the Document Verification stage.'))
            if not doc.attachment_ids:
                raise UserError(_('Attach the document copy before verifying it.'))
            doc.write({'verified': True, 'verified_by': self.env.user.id, 'verified_on': fields.Datetime.now()})
        return True

    def action_reset_verification(self):
        self._bond_check_group(GROUP_INSPECTOR)
        for doc in self:
            if doc.receipt_id.state != 'doc_verification':
                raise UserError(_('Verification can only be reset during Document Verification.'))
            doc.write({'verified': False, 'verified_by': False, 'verified_on': False})
        return True
