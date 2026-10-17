# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from .constants import G_OFFICER, LIVE_STATES, SHIPMENT_STATES


class NelsisLcShipment(models.Model):
    _name = 'nelsis.lc.shipment'
    _description = 'LC Shipment'
    _inherit = ['nelsis.lc.guard.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'lc_id, sequence_no, id'

    name = fields.Char('Shipment Ref.', readonly=True, copy=False, default='New', index=True)
    sequence_no = fields.Integer(readonly=True, copy=False)
    lc_id = fields.Many2one('nelsis.lc', string='Letter of Credit', required=True, index=True,
                            ondelete='cascade', tracking=True)
    company_id = fields.Many2one(related='lc_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(related='lc_id.currency_id', store=True)
    partner_id = fields.Many2one(related='lc_id.partner_id', store=True, string='Supplier')
    bl_awb_no = fields.Char('B/L or AWB No.', tracking=True)
    vessel = fields.Char('Vessel / Flight')
    invoice_no = fields.Char('Commercial Invoice No.', tracking=True)
    invoice_date = fields.Date('Invoice Date')
    invoice_value = fields.Monetary('Invoice Value', currency_field='currency_id', tracking=True)
    shipment_date = fields.Date('Shipment Date', tracking=True)
    eta_date = fields.Date('ETA')
    doc_received_date = fields.Date('Documents Received')
    customs_cleared_date = fields.Date('Customs Cleared')
    received_date = fields.Date('Received in Warehouse')
    state = fields.Selection(SHIPMENT_STATES, default='planned', required=True, readonly=True,
                             copy=False, tracking=True, index=True)
    cancel_reason = fields.Text(readonly=True, copy=False)
    note = fields.Text()

    boe_ids = fields.One2many('nelsis.lc.boe', 'shipment_id', string='Bills of Entry')
    document_ids = fields.One2many('nelsis.lc.document', 'shipment_id', string='Documents')
    picking_ids = fields.One2many('stock.picking', 'lc_shipment_id', string='Warehouse Receipts')
    boe_count = fields.Integer(compute='_compute_counts')
    picking_count = fields.Integer(compute='_compute_counts')

    @api.depends('boe_ids', 'picking_ids')
    def _compute_counts(self):
        for sh in self:
            sh.boe_count = len(sh.boe_ids)
            sh.picking_count = len(sh.sudo().picking_ids)

    # ------------------------------------------------------------ constraints
    @api.constrains('invoice_value')
    def _check_value(self):
        for sh in self:
            if sh.invoice_value < 0:
                raise ValidationError(_('The invoice value cannot be negative.'))

    @api.constrains('invoice_value', 'state', 'lc_id')
    def _check_utilization(self):
        for lc in self.mapped('lc_id'):
            limit = lc.current_amount * (1 + lc.tolerance_percent / 100.0)
            if lc.currency_id.compare_amounts(lc.utilized_amount, limit) > 0:
                raise ValidationError(_(
                    'Utilization (%(used)s) would exceed the approved LC amount (%(cur)s) '
                    'plus tolerance for %(lc)s. Raise an approved amendment first.',
                    used=lc.utilized_amount, cur=lc.current_amount, lc=lc.name))

    @api.onchange('shipment_date', 'lc_id')
    def _onchange_shipment_date(self):
        if self.shipment_date and self.lc_id.shipment_deadline \
                and self.shipment_date > self.lc_id.shipment_deadline:
            return {'warning': {
                'title': _('Late shipment'),
                'message': _('The shipment date is after the LC latest shipment date (%s). '
                             'An approved amendment may be required.', self.lc_id.shipment_deadline),
            }}

    # ------------------------------------------------------------ ORM
    @api.model_create_multi
    def create(self, vals_list):
        next_no = {}
        for vals in vals_list:
            lc = self.env['nelsis.lc'].browse(vals.get('lc_id')).exists()
            if not lc:
                raise ValidationError(_('Select a Letter of Credit.'))
            if not self.env.su:
                if lc.state not in LIVE_STATES:
                    raise UserError(_('Shipments can only be added to an opened LC (current status: %s).',
                                      dict(lc._fields['state'].selection)[lc.state]))
                vals['state'] = 'planned'
            if lc.id not in next_no:
                last = self.search([('lc_id', '=', lc.id)], order='sequence_no desc', limit=1)
                next_no[lc.id] = last.sequence_no or 0
            next_no[lc.id] += 1
            vals['sequence_no'] = next_no[lc.id]
            vals['name'] = self.env['ir.sequence'].next_by_code('nelsis.lc.shipment') or 'New'
        records = super().create(vals_list)
        for sh in records:
            sh.lc_id._log(_('Shipment %s created', sh.name))
        records.mapped('lc_id')._sync_state()
        return records

    def write(self, vals):
        if not self.env.su:
            business = self._business_vals(vals)
            if business:
                if 'state' in business:
                    raise UserError(_('The status can only be changed through the workflow buttons.'))
                if business & {'lc_id', 'name', 'sequence_no'}:
                    raise UserError(_('The LC and numbering of a shipment cannot be changed.'))
                for sh in self:
                    if sh.state in ('received', 'cancelled'):
                        raise UserError(_('Shipment %s is %s and cannot be edited.', sh.name,
                                          dict(SHIPMENT_STATES)[sh.state]))
                    if sh.lc_id.state not in LIVE_STATES:
                        raise UserError(_('LC %s is not active; shipments are locked.', sh.lc_id.name))
        res = super().write(vals)
        if 'invoice_value' in vals:
            self.mapped('lc_id')._sync_state()
        return res

    def unlink(self):
        lcs = self.mapped('lc_id')
        for sh in self:
            if sh.state != 'planned' or sh.boe_ids or sh.sudo().picking_ids:
                raise UserError(_('Only planned shipments without Bills of Entry or receipts can be deleted. '
                                  'Cancel %s instead.', sh.name))
            if sh.lc_id.state not in LIVE_STATES:
                raise UserError(_('LC %s is not active; shipments are locked.', sh.lc_id.name))
        res = super().unlink()
        lcs._sync_state()
        return res

    # ------------------------------------------------------------ workflow
    def _move(self, from_state, new_state, event, extra=None):
        for sh in self:
            if sh.state != from_state:
                raise UserError(_('Shipment %s must be in status "%s".', sh.name,
                                  dict(SHIPMENT_STATES)[from_state]))
            if sh.lc_id.state not in LIVE_STATES:
                raise UserError(_('LC %s is not active.', sh.lc_id.name))
        for sh in self:
            sh.sudo().write(dict({'state': new_state}, **(extra(sh) if extra else {})))
            sh.lc_id._log('%s: %s' % (sh.name, event))
        self.mapped('lc_id')._sync_state()
        return True

    def action_ship(self):
        self._assert_group(G_OFFICER)
        for sh in self:
            missing = [sh._fields[f].string for f in ('bl_awb_no', 'invoice_no', 'shipment_date')
                       if not sh[f]]
            if not sh.invoice_value or sh.invoice_value <= 0:
                missing.append(sh._fields['invoice_value'].string)
            if missing:
                raise UserError(_('Please complete before marking as shipped: %s', ', '.join(missing)))
        return self._move('planned', 'shipped', _('Shipped'))

    def action_docs_received(self):
        self._assert_group(G_OFFICER)
        today = fields.Date.context_today(self)
        return self._move('shipped', 'docs_received', _('Shipping documents received'),
                          lambda sh: {'doc_received_date': sh.doc_received_date or today})

    def action_clear(self):
        self._assert_group(G_OFFICER)
        today = fields.Date.context_today(self)
        for sh in self:
            cleared = sh.boe_ids.filtered(lambda b: b.state == 'cleared')
            if sh.lc_id._setting().require_boe_for_clearance and not cleared:
                raise UserError(_('Shipment %s needs a cleared Bill of Entry before customs clearance.', sh.name))
        return self._move(
            'docs_received', 'customs_cleared', _('Customs cleared'),
            lambda sh: {'customs_cleared_date': max(
                sh.boe_ids.filtered(lambda b: b.state == 'cleared' and b.clearance_date).mapped('clearance_date'),
                default=today)})

    def action_receive(self):
        self._assert_group(G_OFFICER)
        today = fields.Date.context_today(self)
        for sh in self:
            done = sh.sudo().picking_ids.filtered(lambda p: p.state == 'done')
            if sh.lc_id._setting().require_receipt_for_received and not done:
                raise UserError(_('Shipment %s needs at least one validated warehouse receipt linked to it.', sh.name))
        return self._move('customs_cleared', 'received', _('Received in warehouse'),
                          lambda sh: {'received_date': today})

    def action_cancel(self):
        self._assert_group(G_OFFICER)
        self.ensure_one()
        return self._open_reason_wizard('shipment_cancel', _('Cancel Shipment'))

    def _do_cancel(self, reason):
        self._assert_group(G_OFFICER)
        for sh in self:
            if sh.state in ('received', 'cancelled'):
                raise UserError(_('Shipment %s cannot be cancelled in its current status.', sh.name))
            if sh.sudo().picking_ids.filtered(lambda p: p.state == 'done'):
                raise UserError(_('Shipment %s has validated receipts and cannot be cancelled.', sh.name))
            sh.sudo().write({'state': 'cancelled', 'cancel_reason': reason})
            sh.lc_id._log('%s: %s' % (sh.name, _('Cancelled')), note=reason)
        self.mapped('lc_id')._sync_state()

    def action_load_required_documents(self):
        self._assert_group(G_OFFICER)
        types = self.env['nelsis.lc.document.type'].search(
            [('required_default', '=', True), ('scope', '=', 'shipment')])
        vals = []
        for sh in self:
            existing = sh.document_ids.mapped('type_id')
            for dtype in types:
                if dtype in existing or (dtype.lc_type and dtype.lc_type != sh.lc_id.lc_type):
                    continue
                vals.append({'lc_id': sh.lc_id.id, 'shipment_id': sh.id, 'type_id': dtype.id,
                             'is_required': True})
        if vals:
            self.env['nelsis.lc.document'].create(vals)
        return True

    def action_view_boes(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('Bills of Entry'), 'res_model': 'nelsis.lc.boe',
                'view_mode': 'tree,form', 'domain': [('shipment_id', '=', self.id)],
                'context': {'default_lc_id': self.lc_id.id, 'default_shipment_id': self.id}}

    def action_view_receipts(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('Warehouse Receipts'), 'res_model': 'stock.picking',
                'view_mode': 'tree,form', 'domain': [('lc_shipment_id', '=', self.id)],
                'context': {'create': False}}
