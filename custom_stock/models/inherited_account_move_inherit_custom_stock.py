from odoo import models, fields, api,_
from odoo.addons.helper import validator
from datetime import date
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError


class InheritedAccountMoveInheritCustomStock(models.Model):
    _inherit = 'account.move'

    picking_id = fields.Many2one('stock.picking', string='Origin Reference')
    order_id = fields.Many2one('sale.order')
    po_id = fields.Many2one('purchase.order')
    challan_no = fields.Char(string="Challan No.")
    credit_tenor_date = fields.Date(string='Credit Tenor')

    # def action_post(self):
    #     po_val = self.env['custom.common.settings'].search([('key', '=', 'allow_create_po_from_bill')], limit=1)
    #     so_val = self.env['custom.common.settings'].search([('key', '=', 'allow_create_so_from_invoice')], limit=1)
    #     if po_val.value:
    #         if self.type == 'in_invoice':
    #             if not self.invoice_line_ids:
    #                 raise ValidationError(_('Required Minimum one Product.'))
    #             po_no = self.env['ir.sequence'].get('purchase.order')
    #             POData = self.env['purchase.order'].create({
    #                 'name': po_no,
    #                 'state': 'draft',
    #                 'partner_id': self.partner_id.id,
    #                 'po_type': self.partner_id.vendor_type,
    #                 'is_created_from_bill': True,
    #             })
    #             parentId = POData['id']
    #             create_date = POData['create_date']
    #             for data in self.invoice_line_ids:
    #                 self.env['purchase.order.line'].create({
    #                     'order_id': parentId,
    #                     'product_id': data.product_id.id,
    #                     'name': data.product_id.display_name,
    #                     'partner_id': self.partner_id.id,
    #                     'product_uom': data.product_id.uom_id.id,
    #                     'date_planned': create_date,
    #                     'product_qty': data.quantity,
    #                     'price_unit': data.price_unit
    #                 })
    #             POData.button_confirm()
    #             for x in POData.picking_ids:
    #                 x.action_transfer_release()
    #                 x.button_validate()
    #             inv_list = []
    #             inv_list.append(self.id)
    #             POData.invoice_ids = [(6, 0, inv_list)]
    #             POData.invoice_count = len(inv_list)
    #             self.po_id = parentId
    #
    #     if so_val.value:
    #         if self.type == 'out_invoice':
    #             if not self.invoice_line_ids:
    #                 raise ValidationError(_('Required Minimum one Product.'))
    #             so_no = self.env['ir.sequence'].get('sale.order')
    #             SOData = self.env['sale.order'].create({
    #                 'name': so_no,
    #                 'state': 'draft',
    #                 'partner_id': self.partner_id.id,
    #                 'shop_id': self.location_id.id,
    #                 'is_created_from_invoice': True,
    #             })
    #             parentId = SOData['id']
    #             create_date = SOData['create_date']
    #             for data in self.invoice_line_ids:
    #                 line_id = self.env['sale.order.line'].create({
    #                     'order_id': parentId,
    #                     'product_id': data.product_id.id,
    #                     'name': data.product_id.display_name,
    #                     'product_uom': data.product_id.uom_id.id,
    #                     'product_uom_qty': data.quantity,
    #                     'price_unit': data.price_unit,
    #                 })
    #                 data.sale_line_ids = line_id.id,
    #
    #             pr_err_msg = ''
    #             pro_ids = []
    #             check_availability_warning = self.env['custom.common.settings'].search([('key', '=', 'hide_check_availability_warning'), ('value', '=', True)])
    #             for rec in SOData.order_line:
    #                 if rec.product_id.type != 'service':
    #                     available_qty = rec.product_id.with_context({'location': self.location_id.id}).qty_available
    #                     if rec.product_uom_qty > available_qty and not check_availability_warning:
    #                         pr_err_msg += rec.product_id.display_name if not pr_err_msg else '\n' + rec.product_id.display_name
    #                         pro_ids.append(rec.product_id.id)
    #                         # raise ValidationError(_('Given quantity is more than available quantity.'))
    #             if pr_err_msg:
    #                 action_vals = {
    #                     'name': _('Product Stock Update'),
    #                     'domain': [],
    #                     'res_model': 'sale.product.adjustment.wizard',
    #                     'view_mode': 'form',
    #                     'view_id': False,
    #                     'type': 'ir.actions.act_window',
    #                     'target': 'new',
    #                     'context': {'pr_err_msg': pr_err_msg, 'location_id': self.location_id.id, 'pro_ids': pro_ids},
    #                 }
    #                 return action_vals
    #
    #             SOData.action_check_availability()
    #             SOData.action_confirm()
    #
    #             for x in SOData.picking_ids:
    #                 x.action_transfer_release()
    #                 for y in x.move_ids_without_package:
    #                     y.quantity_done = y.product_uom_qty
    #                 x.button_validate()
    #
    #             inv_list1 = []
    #             inv_list1.append(self.id)
    #             SOData.invoice_ids = [(6, 0, inv_list1)]
    #             SOData.invoice_status = 'invoiced'
    #             SOData.invoice_count = len(inv_list1)
    #             self.order_id = parentId
    #
    #     res = super(InheritedAccountMoveDynamicCheque, self).action_post()
    #     return res