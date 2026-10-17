# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
from .constants import (TRANSACTION_TYPES, FILE_STATES, G_USER, G_OFFICER, G_MANAGER, require_group)

MANAGER_STATES = ('docs_complete', 'receipt_pending', 'done', 'returned', 'rejected')
USER_STATES = ('draft', 'submitted')


class NelsisCommercialFile(models.Model):
    _name = 'nelsis.commercial.file'
    _description = 'Commercial File'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Reference', readonly=True, copy=False, default=lambda self: _('New'), tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    transaction_type = fields.Selection(TRANSACTION_TYPES, required=True, default='import_lc', tracking=True)
    lc_ref = fields.Reference(selection='_lc_selection', string='LC Reference')
    lc_display = fields.Char(string='LC', compute='_compute_lc_display')
    partner_id = fields.Many2one('res.partner', string='Supplier / Exporter', tracking=True)
    importer_id = fields.Many2one('res.partner', string='Importer / Applicant',
                                  default=lambda self: self.env.company.partner_id)
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user, tracking=True)
    state = fields.Selection(FILE_STATES, default='draft', required=True, tracking=True, copy=False)
    previous_state = fields.Char(copy=False)
    notes = fields.Html()

    shipment_ids = fields.One2many('nelsis.commercial.shipment', 'file_id')
    document_ids = fields.One2many('nelsis.commercial.document', 'file_id')
    boe_ids = fields.One2many('nelsis.commercial.boe', 'file_id')
    line_ids = fields.One2many('nelsis.commercial.line', 'file_id')
    discrepancy_ids = fields.One2many('nelsis.commercial.discrepancy', 'file_id')
    picking_ids = fields.Many2many('stock.picking', 'nelsis_commercial_file_picking_rel',
                                   'file_id', 'picking_id', string='Warehouse Receipts')

    shipment_count = fields.Integer(compute='_compute_counts')
    document_count = fields.Integer(compute='_compute_counts')
    boe_count = fields.Integer(compute='_compute_counts')
    picking_count = fields.Integer(compute='_compute_counts')
    discrepancy_count = fields.Integer(compute='_compute_counts')
    open_discrepancy_count = fields.Integer(compute='_compute_counts')

    missing_type_ids = fields.Many2many('nelsis.commercial.document.type', compute='_compute_missing',
                                        string='Missing Required Documents')
    missing_count = fields.Integer(compute='_compute_missing')
    conditional_type_ids = fields.Many2many('nelsis.commercial.document.type', compute='_compute_missing',
                                            string='Conditional Documents (manual check)')

    # ------------------------------------------------------------------ helpers
    @api.model
    def _lc_selection(self):
        setting = self.env['nelsis.commercial.setting'].sudo().search(
            [('company_id', '=', self.env.company.id)], limit=1)
        model = setting.lc_model_id.model
        if model and model in self.env:
            return [(model, setting.lc_model_id.name)]
        return []

    @api.depends('lc_ref')
    def _compute_lc_display(self):
        for rec in self:
            try:
                rec.lc_display = rec.lc_ref.display_name if rec.lc_ref else False
            except Exception:
                rec.lc_display = _('Restricted / unavailable')

    @api.depends('shipment_ids', 'document_ids', 'boe_ids', 'picking_ids', 'discrepancy_ids.state')
    def _compute_counts(self):
        for rec in self:
            rec.shipment_count = len(rec.shipment_ids)
            rec.document_count = len(rec.document_ids.filtered(lambda d: d.state != 'superseded'))
            rec.boe_count = len(rec.boe_ids)
            rec.picking_count = len(rec.picking_ids)
            rec.discrepancy_count = len(rec.discrepancy_ids)
            rec.open_discrepancy_count = len(
                rec.discrepancy_ids.filtered(lambda d: d.state in ('mismatch', 'uom_review')))

    def _applicable_rules(self, requirement):
        self.ensure_one()
        today = fields.Date.context_today(self)
        return self.env['nelsis.commercial.rule'].search([
            ('active', '=', True),
            ('requirement', '=', requirement),
            '|', ('effective_date', '=', False), ('effective_date', '<=', today),
            '|', ('transaction_type', '=', False), ('transaction_type', '=', self.transaction_type),
            '|', ('company_id', '=', False), ('company_id', '=', self.company_id.id),
        ])

    @api.depends('transaction_type', 'company_id', 'document_ids.state',
                 'document_ids.document_type_id', 'document_ids.expiry_date')
    def _compute_missing(self):
        for rec in self:
            if not rec.id:
                rec.missing_type_ids = False
                rec.missing_count = 0
                rec.conditional_type_ids = False
                continue
            valid = rec.document_ids.filtered(lambda d: d.state == 'verified' and not d.is_expired)
            required = rec._applicable_rules('required').document_type_id
            missing = required - valid.document_type_id
            rec.missing_type_ids = missing
            rec.missing_count = len(missing)
            rec.conditional_type_ids = rec._applicable_rules('conditional').document_type_id - valid.document_type_id

    # ------------------------------------------------------------------ ORM
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.pop('state', None)
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('nelsis.commercial.file') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        if 'state' in vals:
            target = vals['state']
            if target in MANAGER_STATES:
                require_group(self.env, G_MANAGER)
            elif target in USER_STATES:
                require_group(self.env, G_USER)
            else:
                require_group(self.env, G_OFFICER)
        return super().write(vals)

    def unlink(self):
        if any(rec.state != 'draft' for rec in self):
            raise UserError(_("Only draft commercial files can be deleted. Cancel the file instead to keep its audit history."))
        return super().unlink()

    @api.constrains('state')
    def _check_state_rules(self):
        for rec in self:
            if rec.state in ('docs_complete', 'customs', 'receipt_pending', 'done') and rec.missing_count:
                names = ', '.join(rec.missing_type_ids.mapped('name'))
                raise ValidationError(_("Required verified documents are outstanding: %s", names))
            if rec.state in ('receipt_pending', 'done') and rec.transaction_type in ('import_lc', 'import_non_lc'):
                boes = rec.boe_ids.filtered(lambda b: b.state != 'cancel')
                if not boes or any(b.state != 'cleared' for b in boes):
                    raise ValidationError(_("Every Bill of Entry must be verified and cleared before this step."))
            if rec.state == 'done':
                if not rec.picking_ids:
                    raise ValidationError(_("Link at least one warehouse receipt before completing the file."))
                if rec.open_discrepancy_count:
                    raise ValidationError(_("Unresolved quantity/unit discrepancies must be approved or corrected first."))

    # ------------------------------------------------------------------ workflow
    def _do_transition(self, allowed, target, group):
        require_group(self.env, group)
        labels = dict(self._fields['state'].selection)
        for rec in self:
            if rec.state not in allowed:
                raise UserError(_("Action not allowed from status '%s'.", labels[rec.state]))
        self.write({'state': target})
        return True

    def action_submit(self):
        return self._do_transition(('draft', 'returned'), 'submitted', G_USER)

    def action_start_verification(self):
        return self._do_transition(('submitted',), 'verification', G_OFFICER)

    def action_docs_complete(self):
        return self._do_transition(('verification',), 'docs_complete', G_MANAGER)

    def action_start_customs(self):
        return self._do_transition(('docs_complete',), 'customs', G_OFFICER)

    def action_cleared(self):
        return self._do_transition(('customs',), 'receipt_pending', G_MANAGER)

    def action_done(self):
        return self._do_transition(('receipt_pending',), 'done', G_MANAGER)

    def action_return(self):
        return self._do_transition(('submitted', 'verification', 'docs_complete'), 'returned', G_MANAGER)

    def action_reject(self):
        return self._do_transition(('submitted', 'verification', 'docs_complete'), 'rejected', G_MANAGER)

    def action_cancel(self):
        return self._do_transition(('draft', 'submitted', 'returned', 'hold'), 'cancel', G_OFFICER)

    def action_reset_draft(self):
        return self._do_transition(('returned', 'rejected', 'cancel'), 'draft', G_MANAGER)

    def action_hold(self):
        require_group(self.env, G_OFFICER)
        for rec in self:
            if rec.state in ('done', 'cancel', 'rejected', 'hold'):
                raise UserError(_("This file cannot be put on hold."))
            rec.previous_state = rec.state
            rec.write({'state': 'hold'})
        return True

    def action_resume(self):
        require_group(self.env, G_OFFICER)
        for rec in self:
            if rec.state != 'hold':
                raise UserError(_("Only files on hold can be resumed."))
            rec.write({'state': rec.previous_state or 'draft'})
        return True

    # ------------------------------------------------------------------ discrepancies
    def _prepare_discrepancy_vals(self, line, setting):
        self.ensure_one()
        pickings = line.shipment_id.picking_ids or self.picking_ids
        done = pickings.sudo().filtered(lambda p: p.state == 'done')  # read-only: commercial roles have no stock rights
        moves = done.move_ids.filtered(lambda m: m.state == 'done' and m.product_id == line.product_id)
        basis = _("Documented: %(kind)s line %(qty)s %(uom)s. Received: validated stock moves of %(picks)s (standard Odoo Inventory).",
                  kind=dict(line._fields['source_kind'].selection).get(line.source_kind, ''),
                  qty=line.qty, uom=line.uom_id.name,
                  picks=', '.join(done.mapped('name')) or _('no validated receipt'))
        vals = {'received_uom_id': line.uom_id.id, 'received_qty': 0.0, 'basis': basis}
        if not done:
            vals['state'] = 'pending'
            return vals
        if moves.filtered(lambda m: m.product_uom.category_id != line.uom_id.category_id):
            vals['state'] = 'uom_review'
            vals['basis'] += ' ' + _("Units belong to different categories: conversion/manual review required.")
            return vals
        received = sum(m.product_uom._compute_quantity(m.quantity, line.uom_id) for m in moves)
        tolerance = line.qty * (setting.quantity_tolerance or 0.0) / 100.0
        diff = received - line.qty
        vals['received_qty'] = received
        vals['state'] = 'ok' if float_compare(abs(diff), tolerance, precision_rounding=line.uom_id.rounding) <= 0 else 'mismatch'
        return vals

    def action_compute_discrepancies(self):
        require_group(self.env, G_OFFICER)
        setting = self.env['nelsis.commercial.setting'].get_setting()
        for rec in self:
            for line in rec.line_ids:
                vals = rec._prepare_discrepancy_vals(line, setting)
                disc = rec.discrepancy_ids.filtered(lambda d: d.line_id == line)[:1]
                if disc:
                    if disc.state != 'approved':
                        disc.write(vals)
                else:
                    self.env['nelsis.commercial.discrepancy'].create(dict(vals, line_id=line.id, file_id=rec.id))
        return True

    # ------------------------------------------------------------------ smart buttons
    def _open_records(self, model, domain, title, ctx=None):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': title, 'res_model': model,
            'view_mode': 'tree,form', 'domain': domain,
            'context': dict(ctx or {}, default_file_id=self.id),
        }

    def action_view_documents(self):
        return self._open_records('nelsis.commercial.document', [('file_id', '=', self.id)], _('Documents'))

    def action_view_shipments(self):
        return self._open_records('nelsis.commercial.shipment', [('file_id', '=', self.id)], _('Shipments'))

    def action_view_boes(self):
        return self._open_records('nelsis.commercial.boe', [('file_id', '=', self.id)], _('Bills of Entry'))

    def action_view_discrepancies(self):
        return self._open_records('nelsis.commercial.discrepancy', [('file_id', '=', self.id)], _('Discrepancies'))

    def action_view_pickings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Warehouse Receipts'), 'res_model': 'stock.picking',
            'view_mode': 'tree,form', 'domain': [('id', 'in', self.picking_ids.ids)],
        }
