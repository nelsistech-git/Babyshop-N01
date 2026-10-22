# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentBomSupplier(models.Model):
    """Supplier Mapping (SRS section 21) — garment.bom.supplier. Tracks
    approved/alternative/emergency suppliers per material, with a Supplier
    Ranking score and a full Price History trail (SRS section 22)."""
    _name = 'garment.bom.supplier'
    _description = 'Garment BOM Supplier Mapping'
    _order = 'sequence'

    bom_id = fields.Many2one('garment.bom', string='BOM', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    material_reference = fields.Char(string='Material Reference', required=True)
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True)
    supplier_code = fields.Char(string='Supplier Code')
    supplier_type = fields.Selection([
        ('buyer_approved', 'Buyer Approved'), ('factory_approved', 'Factory Approved'),
        ('alternative', 'Alternative'), ('emergency', 'Emergency'),
    ], string='Supplier Type', default='factory_approved', required=True)
    country_id = fields.Many2one('res.country', string='Country')
    contact_person = fields.Char(string='Contact Person')
    lead_time_days = fields.Integer(string='Lead Time (days)')
    moq = fields.Float(string='MOQ')
    currency_id = fields.Many2one('res.currency', related='bom_id.currency_id', store=True)
    previous_price = fields.Monetary(string='Previous Price', currency_field='currency_id')
    current_price = fields.Monetary(string='Current Price', currency_field='currency_id')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    approved_status = fields.Selection([
        ('draft', 'Draft'), ('approved', 'Approved'), ('suspended', 'Suspended'),
    ], string='Approved Status', default='draft')

    # Supplier Ranking (SRS section 21)
    quality_rating = fields.Float(string='Quality Rating (0-5)')
    delivery_rating = fields.Float(string='Delivery Performance (0-5)')
    compliance_score = fields.Float(string='Compliance Score (0-100)')
    previous_issues_count = fields.Integer(string='Previous Issues')
    rank_score = fields.Float(string='Ranking Score', compute='_compute_rank_score', store=True,
                               help='Weighted score from Quality, Delivery Performance and Compliance, '
                                    'penalized by Previous Issues and Price — higher is better.')

    price_history_ids = fields.One2many('garment.bom.price.history', 'bom_supplier_id', string='Price History')

    def action_view_price_history(self):
        self.ensure_one()
        return {'name': _('Price History'), 'type': 'ir.actions.act_window',
                'res_model': 'garment.bom.price.history', 'view_mode': 'tree',
                'domain': [('bom_supplier_id', '=', self.id)]}

    @api.depends('quality_rating', 'delivery_rating', 'compliance_score', 'previous_issues_count')
    def _compute_rank_score(self):
        for rec in self:
            score = (rec.quality_rating or 0.0) * 20 + (rec.delivery_rating or 0.0) * 20 \
                + (rec.compliance_score or 0.0) * 0.6
            score -= (rec.previous_issues_count or 0) * 5
            rec.rank_score = max(score, 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.current_price:
                rec.env['garment.bom.price.history'].create({
                    'bom_supplier_id': rec.id,
                    'previous_price': rec.previous_price,
                    'current_price': rec.current_price,
                    'effective_date': fields.Date.context_today(rec),
                    'changed_by_id': rec.env.user.id,
                    'reason': _('Initial price on Supplier Mapping creation.'),
                })
        return records

    def write(self, vals):
        price_changes = {}
        if 'current_price' in vals:
            for rec in self:
                if rec.current_price != vals['current_price']:
                    price_changes[rec.id] = rec.current_price
        supplier_changes = {rec.id: rec.supplier_id for rec in self} if 'supplier_id' in vals else {}
        res = super().write(vals)
        for rec in self:
            if rec.id in price_changes:
                rec.env['garment.bom.price.history'].create({
                    'bom_supplier_id': rec.id,
                    'previous_price': price_changes[rec.id],
                    'current_price': rec.current_price,
                    'effective_date': fields.Date.context_today(rec),
                    'changed_by_id': rec.env.user.id,
                    'reason': _('Price updated.'),
                })
                rec.previous_price = price_changes[rec.id]
                rec.bom_id.message_post(body=_('Supplier "%s" price for "%s" changed: %.2f → %.2f') % (
                    rec.supplier_id.name, rec.material_reference, price_changes[rec.id], rec.current_price))
            if rec.id in supplier_changes and supplier_changes[rec.id] != rec.supplier_id:
                rec.bom_id.message_post(body=_('Supplier for "%s" changed: %s → %s') % (
                    rec.material_reference, supplier_changes[rec.id].name or '-', rec.supplier_id.name))
        return res
