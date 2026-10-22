# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import _, fields, models


class ResPartner(models.Model):
    """Buyer Portal identity fields on res.partner (SRS sections 6-7, 24).

    A Buyer Portal login is an ordinary Odoo portal user whose res.partner
    is either the Buyer's own `garment.buyer.partner_id` (single-user buyers)
    or a child contact of it (multi-user buyers - SRS section 7 "a buyer can
    have multiple users"). `garment_buyer_id` is stamped on both cases so
    every controller/record-rule in this module can resolve "which buyer is
    this portal user" with a single field instead of walking the commercial
    partner hierarchy.
    """
    _inherit = 'res.partner'

    garment_buyer_id = fields.Many2one(
        'garment.buyer', string='Buyer (Portal)', copy=False, tracking=True,
        help='Set when this contact is a Buyer Portal login. Scopes every /my page in the '
             'Buyer Portal module to this buyer only (SRS section 25 - Data Visibility Rules).')
    garment_portal_role = fields.Selection([
        ('buyer_admin', 'Buyer Admin - Full Buyer Access'),
        ('buyer_merchandiser', 'Buyer Merchandiser - Order & Sample'),
        ('buyer_qa', 'Buyer QA - Quality Data'),
        ('buyer_logistics', 'Buyer Logistics - Shipment Data'),
    ], string='Buyer Portal Role', tracking=True,
        help='External buyer-side access-control role (SRS section 24 - Buyer Access Control).')
    garment_portal_department = fields.Char(
        string='Buyer Portal Department',
        help='e.g. Merchandising, QA, Logistics - used to route portal messages/comments to the '
             'right factory team (SRS section 13).')
    garment_portal_activity_count = fields.Integer(
        string='Portal Activity Count', compute='_compute_garment_portal_activity_count')

    def _compute_garment_portal_activity_count(self):
        Log = self.env['garment.portal.activity.log']
        for rec in self:
            rec.garment_portal_activity_count = Log.search_count([('partner_id', '=', rec.id)])

    def action_view_garment_portal_activity(self):
        self.ensure_one()
        return {
            'name': _('Buyer Portal Activity'),
            'type': 'ir.actions.act_window',
            'res_model': 'garment.portal.activity.log',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
        }
