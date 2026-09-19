# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models
from odoo.exceptions import UserError


class FwBuyerOrder(models.Model):
    _inherit = 'fw.buyer.order'

    invoice_count = fields.Integer(string='Invoices', compute='_compute_invoice_count')

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = self.env['account.move'].search_count([
                ('fw_buyer_order_id', '=', rec.id),
            ])

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('fw_buyer_order_id', '=', self.id)],
        }

    def action_create_invoice(self):
        self.ensure_one()
        partner = self.buyer_id.partner_id
        if not partner:
            raise UserError(
                "Buyer '%s' has no linked Contact. Please set one on the Buyer master "
                "before creating an invoice." % self.buyer_id.name)

        invoice_line_vals = []
        missing_product_styles = []
        for line in self.line_ids:
            product = line.style_id.product_tmpl_id.product_variant_id \
                if line.style_id.product_tmpl_id else False
            if not product:
                missing_product_styles.append(line.style_id.name or line.style_id.style_no)
                continue
            invoice_line_vals.append((0, 0, {
                'product_id': product.id,
                'quantity': line.total_qty,
                'price_unit': line.unit_price,
                'name': "%s - %s" % (line.style_id.style_no or '', line.style_id.name or ''),
            }))

        if missing_product_styles:
            raise UserError(
                "These styles have no linked Product and cannot be invoiced: %s. "
                "Please set a Product on the Style master first (FW Core Master > "
                "Styles)." % ', '.join(missing_product_styles))
        if not invoice_line_vals:
            raise UserError("This order has no invoiceable lines.")

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': fields.Date.context_today(self),
            'currency_id': self.currency_id.id,
            'invoice_origin': self.name,
            'fw_buyer_order_id': self.id,
            'invoice_line_ids': invoice_line_vals,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Invoice',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
        }
