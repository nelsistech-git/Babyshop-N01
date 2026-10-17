# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero

from .reference_mixin import GROUP_APPROVER, GROUP_USER


class BondClassificationRequest(models.Model):
    """Approved workflow for every bonded / non-bonded classification change."""
    _name = 'bond.inventory.classification.request'
    _inherit = ['bond.inventory.reference.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Bond Classification Request'
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    company_id = fields.Many2one('res.company', required=True, readonly=True, index=True,
                                 default=lambda self: self.env.company)
    target_type = fields.Selection(
        [('location', 'Location'), ('product', 'Product'), ('lot', 'Lot / Batch')],
        required=True, default='location', tracking=True)
    location_id = fields.Many2one('stock.location', domain=[('usage', '=', 'internal')])
    product_tmpl_id = fields.Many2one('product.template', string='Product')
    lot_id = fields.Many2one('stock.lot', string='Lot / Batch')
    new_status = fields.Selection(
        [('bonded', 'Bonded / Bond Eligible'), ('non_bonded', 'Non-Bonded / Not Eligible')],
        string='New Classification', required=True, tracking=True)
    current_status = fields.Char(compute='_compute_current_status')
    license_ref = fields.Char(string='Bond License Reference')
    authorized_from = fields.Date(string='Authorized From')
    authorized_to = fields.Date(string='Authorized Until')
    reason = fields.Text(string='Justification', required=True)
    attachment_ids = fields.Many2many(
        'ir.attachment', 'bond_inv_class_request_attachment_rel', 'request_id', 'attachment_id',
        string='Supporting Evidence')
    state = fields.Selection(
        [('draft', 'Draft'), ('submitted', 'Submitted'), ('applied', 'Approved & Applied'),
         ('rejected', 'Rejected')],
        default='draft', required=True, copy=False, readonly=True, tracking=True, index=True)
    requested_by = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True, copy=False)
    decided_by = fields.Many2one('res.users', readonly=True, copy=False)
    decided_on = fields.Datetime(readonly=True, copy=False)
    rejection_reason = fields.Text(copy=False)

    @api.depends('target_type', 'location_id', 'product_tmpl_id', 'lot_id')
    def _compute_current_status(self):
        for rec in self:
            if rec.target_type == 'location' and rec.location_id:
                rec.current_status = dict(rec.location_id._fields['bond_status'].selection)[rec.location_id.bond_status]
            elif rec.target_type == 'product' and rec.product_tmpl_id:
                rec.current_status = _('Bond eligible') if rec.product_tmpl_id.bond_eligible else _('Not eligible')
            elif rec.target_type == 'lot' and rec.lot_id:
                rec.current_status = dict(rec.lot_id._fields['bond_status'].selection)[rec.lot_id.bond_status]
            else:
                rec.current_status = False

    @api.constrains('target_type', 'location_id', 'product_tmpl_id', 'lot_id')
    def _check_target(self):
        for rec in self:
            targets = {'location': rec.location_id, 'product': rec.product_tmpl_id, 'lot': rec.lot_id}
            if not targets[rec.target_type]:
                raise ValidationError(_('Select the %s to classify.', rec.target_type))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'bond.inventory.classification.request') or _('New')
        return super().create(vals_list)

    def unlink(self):
        if any(rec.state not in ('draft',) for rec in self):
            raise UserError(_('Only draft requests can be deleted; decided requests are kept as audit trail.'))
        return super().unlink()

    def action_submit(self):
        self._bond_check_group(GROUP_USER)
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft requests can be submitted.'))
            if not rec.attachment_ids:
                raise UserError(_('Supporting evidence (attachment) is mandatory.'))
            if rec.target_type == 'location' and rec.new_status == 'bonded' and not rec.license_ref:
                raise UserError(_('The bond license reference is required to bond a location.'))
            rec.state = 'submitted'

    def action_approve(self):
        self._bond_check_group(GROUP_APPROVER)
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Only submitted requests can be approved.'))
            if not self.env.su and rec.create_uid == self.env.user and not self._bond_is_manager():
                raise UserError(_('The requester cannot approve their own request.'))
            rec._apply_classification()
            rec.write({'state': 'applied', 'decided_by': self.env.user.id,
                       'decided_on': fields.Datetime.now()})
            rec.message_post(body=_('Classification applied: %s.', dict(
                rec._fields['new_status'].selection)[rec.new_status]))

    def action_reject(self):
        self._bond_check_group(GROUP_APPROVER)
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Only submitted requests can be rejected.'))
            if not rec.rejection_reason:
                raise UserError(_('Enter the rejection reason first.'))
            rec.write({'state': 'rejected', 'decided_by': self.env.user.id,
                       'decided_on': fields.Datetime.now()})

    def action_reset_draft(self):
        for rec in self:
            if rec.state != 'rejected':
                raise UserError(_('Only rejected requests can be reset to draft.'))
            rec.state = 'draft'

    # -- application ---------------------------------------------------------
    def _apply_classification(self):
        self.ensure_one()
        getattr(self, '_apply_%s' % self.target_type)()

    def _stock_quants(self, domain):
        return self.env['stock.quant'].sudo().search(
            domain + [('location_id.usage', '=', 'internal'), ('quantity', '!=', 0)])

    def _apply_location(self):
        location = self.location_id.with_context(active_test=False)
        if location.usage != 'internal':
            raise UserError(_('Only internal locations can be classified.'))
        if self._stock_quants([('location_id', 'child_of', location.id)]):
            raise UserError(_('Location %s (or a sub-location) still holds stock. Reclassifying it would '
                              'misstate bonded quantities; move the stock out first.', location.display_name))
        tree = self.env['stock.location'].with_context(active_test=False).search(
            [('id', 'child_of', location.id), ('usage', '=', 'internal')])
        if self.new_status == 'bonded':
            vals = {'bond_status': 'bonded', 'bond_license_ref': self.license_ref,
                    'bond_authorized_from': self.authorized_from, 'bond_authorized_to': self.authorized_to}
        else:
            vals = {'bond_status': 'non_bonded', 'bond_license_ref': False,
                    'bond_authorized_from': False, 'bond_authorized_to': False}
        tree.with_context(bond_classification_apply=True).write(vals)

    def _apply_product(self):
        product = self.product_tmpl_id
        new_value = self.new_status == 'bonded'
        if not new_value:
            bonded = self._stock_quants([('product_id', 'in', product.product_variant_ids.ids),
                                         ('location_id.bond_status', '=', 'bonded')])
            if bonded:
                raise UserError(_('Product "%s" still has stock in bonded locations.', product.display_name))
        product.with_context(bond_classification_apply=True).write({'bond_eligible': new_value})

    def _apply_lot(self):
        lot = self.lot_id
        if self._stock_quants([('lot_id', '=', lot.id)]):
            raise UserError(_('Lot %s is on hand. Move it out before changing its classification.', lot.name))
        lot.with_context(bond_classification_apply=True).write({'bond_status': self.new_status})
