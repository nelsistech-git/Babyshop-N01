# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .bond_sql import VERIFICATION_STATES

BOND_REF_FIELDS = ('bond_license_ref', 'bond_lc_ref', 'bond_boe_ref', 'bond_entitlement_ref')
MANAGER_GROUP = 'nelsis_bond_reconciliation.group_bond_recon_manager'


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    bond_license_ref = fields.Char(string='Bond License', tracking=True, copy=False, index=True)
    bond_lc_ref = fields.Char(string='LC Reference', tracking=True, copy=False, index=True)
    bond_boe_ref = fields.Char(string='Bill of Entry', tracking=True, copy=False, index=True)
    bond_entitlement_ref = fields.Char(string='Entitlement Reference', tracking=True, copy=False)
    bond_verification_state = fields.Selection(
        VERIFICATION_STATES, string='Bond Verification', default='draft',
        copy=False, tracking=True, index=True)
    bond_verified_by = fields.Many2one('res.users', string='Verified By', copy=False, readonly=True)
    bond_verified_on = fields.Datetime(string='Verified On', copy=False, readonly=True)
    bond_document_count = fields.Integer(compute='_compute_bond_document_count')

    # ------------------------------------------------------------------
    def _compute_bond_document_count(self):
        counts = {}
        if self.ids:
            attachments = self.env['ir.attachment'].sudo().search_read(
                [('res_model', '=', 'stock.picking'), ('res_id', 'in', self.ids)], ['res_id'])
            for att in attachments:
                counts[att['res_id']] = counts.get(att['res_id'], 0) + 1
        for rec in self:
            rec.bond_document_count = counts.get(rec.id, 0)

    def write(self, vals):
        if any(f in vals for f in BOND_REF_FIELDS):
            if not self.env.su and not self.env.user.has_group(MANAGER_GROUP):
                done = self.filtered(lambda p: p.state == 'done')
                if done:
                    raise UserError(_(
                        "Bond references of validated transfers can only be changed by a "
                        "Bond Reconciliation Manager (%s).", ', '.join(done.mapped('name'))))
        return super().write(vals)

    def _action_done(self):
        res = super()._action_done()
        for picking in self:
            picking._bond_propagate_refs_to_lots()
        return res

    def _bond_propagate_refs_to_lots(self):
        """Copy LC / BoE / license references to lots that do not carry them yet."""
        self.ensure_one()
        if not (self.bond_lc_ref or self.bond_boe_ref or self.bond_license_ref):
            return
        for lot in self.move_line_ids.mapped('lot_id'):
            vals = {}
            if self.bond_lc_ref and not lot.bond_lc_ref:
                vals['bond_lc_ref'] = self.bond_lc_ref
            if self.bond_boe_ref and not lot.bond_boe_ref:
                vals['bond_boe_ref'] = self.bond_boe_ref
            if self.bond_license_ref and not lot.bond_license_ref:
                vals['bond_license_ref'] = self.bond_license_ref
            if vals:
                lot.sudo().write(vals)

    # ------------------------------------------------------------------
    # Verification workflow
    # ------------------------------------------------------------------
    def _bond_check_manager(self):
        if not self.env.user.has_group(MANAGER_GROUP):
            raise UserError(_("Only a Bond Reconciliation Manager can verify or reject bond transactions."))

    def action_bond_submit(self):
        for rec in self:
            if rec.bond_verification_state not in ('draft', 'rejected'):
                continue
            rec.bond_verification_state = 'pending'
            rec.message_post(body=_("Submitted for bond verification."))
        return True

    def action_bond_verify(self):
        self._bond_check_manager()
        for rec in self:
            if rec.state != 'done':
                raise UserError(_("%s is not validated yet; only validated transfers can be verified.", rec.name))
            rec.write({
                'bond_verification_state': 'verified',
                'bond_verified_by': self.env.user.id,
                'bond_verified_on': fields.Datetime.now(),
            })
            rec.message_post(body=_("Bond verification completed."))
        return True

    def action_bond_reject(self):
        self._bond_check_manager()
        for rec in self:
            rec.write({
                'bond_verification_state': 'rejected',
                'bond_verified_by': self.env.user.id,
                'bond_verified_on': fields.Datetime.now(),
            })
            rec.message_post(body=_("Bond verification rejected."))
        return True

    def action_bond_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Supporting Documents'),
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,tree,form',
            'domain': [('res_model', '=', 'stock.picking'), ('res_id', '=', self.id)],
            'context': {'default_res_model': 'stock.picking', 'default_res_id': self.id},
        }
