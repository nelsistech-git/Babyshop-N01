# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class BondConsignment(models.Model):
    _inherit = 'bond.inventory.consignment'

    purchase_order_id = fields.Many2one(
        'purchase.order', string='Purchase Order', copy=False, tracking=True, index=True, ondelete='restrict',
        domain="[('state', 'in', ['purchase', 'done']), ('company_id', '=', company_id), "
               "('bond_purchase_type', '=', 'import_bonded')]")
    lc_id = fields.Many2one('nelsis.lc', string='LC (linked)', compute='_compute_lc_id')
    lc_shipment_id = fields.Many2one('nelsis.lc.shipment', string='LC Shipment', copy=False, tracking=True,
                                     domain="[('lc_id', '=', lc_id)]")

    @api.depends('lc_ref')
    def _compute_lc_id(self):
        for rec in self:
            lc = rec.sudo().lc_ref
            rec.lc_id = lc if lc and lc._name == 'nelsis.lc' else False

    @api.onchange('purchase_order_id')
    def _onchange_purchase_order_id(self):
        po = self.purchase_order_id
        if not po:
            return
        self.partner_id = po.partner_id.commercial_partner_id
        lc = po.lc_id.sudo()
        if lc:
            self.lc_number = lc.lc_number
            if 'nelsis.lc' in dict(self._selection_lc_models()):
                self.lc_ref = 'nelsis.lc,%d' % lc.id

    @api.constrains('purchase_order_id', 'partner_id', 'lc_ref', 'lc_number', 'lc_shipment_id', 'company_id')
    def _check_purchase_order(self):
        for rec in self:
            po = rec.purchase_order_id.sudo()
            if po:
                if po.bond_purchase_type != 'import_bonded':
                    raise ValidationError(_('Purchase order %s is not a bonded import order.', po.name))
                if po.company_id != rec.company_id:
                    raise ValidationError(_('Purchase order %s belongs to another company.', po.name))
                if po.partner_id.commercial_partner_id != rec.partner_id.commercial_partner_id:
                    raise ValidationError(_('The supplier of %(c)s differs from the supplier of order %(po)s.',
                                            c=rec.name, po=po.name))
                lc = po.lc_id
                if lc:
                    if rec.lc_id and rec.lc_id != lc:
                        raise ValidationError(_('%(c)s is on LC %(a)s but order %(po)s is on LC %(b)s.',
                                                c=rec.name, a=rec.lc_id.display_name, po=po.name,
                                                b=lc.display_name))
                    if not rec.lc_id and rec.lc_number and rec.lc_number != lc.lc_number:
                        raise ValidationError(_('LC number %(a)s on %(c)s differs from LC %(b)s of order %(po)s.',
                                                a=rec.lc_number, c=rec.name, b=lc.lc_number, po=po.name))
            ship = rec.lc_shipment_id.sudo()
            if ship and rec.lc_id and ship.lc_id != rec.lc_id:
                raise ValidationError(_('Shipment %s belongs to another LC.', ship.display_name))

    def action_open(self):
        for rec in self:
            po = rec.purchase_order_id.sudo()
            if po and po.state not in ('purchase', 'done'):
                raise UserError(_('Purchase order %s is not confirmed.', po.name))
        return super().action_open()

    def action_view_purchase_order(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'purchase.order', 'view_mode': 'form',
                'res_id': self.purchase_order_id.id}


class BondConsignmentLine(models.Model):
    _inherit = 'bond.inventory.consignment.line'

    purchase_order_id = fields.Many2one(related='consignment_id.purchase_order_id', store=True, index=True)
    purchase_line_id = fields.Many2one(
        'purchase.order.line', string='Purchase Line', copy=False, index=True, ondelete='restrict',
        domain="[('order_id', '=', purchase_order_id)]")

    @api.constrains('purchase_line_id', 'declared_qty', 'product_id', 'product_uom_id', 'consignment_id')
    def _check_purchase_line(self):
        for line in self:
            pol = line.purchase_line_id.sudo()
            if not pol:
                continue
            if pol.order_id != line.consignment_id.purchase_order_id.sudo():
                raise ValidationError(_('Purchase line %s is not on the consignment purchase order.',
                                        pol.display_name))
            if pol.product_id != line.product_id:
                raise ValidationError(_('Consignment line %(p)s does not match purchase line %(q)s.',
                                        p=line.product_id.display_name, q=pol.product_id.display_name))
        for pol in self.mapped('purchase_line_id').sudo():
            lc = pol.order_id.lc_id
            tol = lc.tolerance_percent if lc else 0.0
            allowed = pol.product_qty * (1 + tol / 100.0)
            declared = 0.0
            for cl in pol.bond_consignment_line_ids.filtered(lambda c: c.consignment_id.state != 'cancelled'):
                declared += cl.product_uom_id._compute_quantity(cl.declared_qty, pol.product_uom)
            if float_compare(declared, allowed, precision_rounding=pol.product_uom.rounding) > 0:
                raise ValidationError(_('Consignments declare %(d).2f of %(p)s, above the ordered %(o).2f '
                                        '(tolerance included: %(a).2f).', d=declared, p=pol.product_id.display_name,
                                        o=pol.product_qty, a=allowed))
