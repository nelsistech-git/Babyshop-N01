from odoo import models, fields, _, api
from odoo.addons.helper import validator
from datetime import date
from odoo.tools import float_compare
from odoo.exceptions import AccessError, UserError


class StockBatchScrapWizard(models.TransientModel):
    _name = 'stock.batch.scrap.wizard'
    _description = 'Stock Batch Scrap Wizard'

    def _get_default_scrap_location_id(self):
        return self.env['stock.location'].search([('scrap_location', '=', True)], limit=1).id

    def _get_default_location_id(self):
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        if warehouse:
            return warehouse.lot_stock_id.id
        return None

    src_location_id = fields.Many2one(
        'stock.location', 'Source Location', domain="[('usage', '=', 'internal')]",
        required=True, default=_get_default_location_id)
    scrap_location_id = fields.Many2one(
        'stock.location', 'Scrap Location', default=_get_default_scrap_location_id,
        domain="[('scrap_location', '=', True)]", required=True)
    order_by_id = fields.Many2one('res.users', string='Order By', ondelete='cascade')
    approve_by_id = fields.Many2one('res.users', string='Approve By', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', 'Owner')
    source_document = fields.Char('Source Document')
    batch_scrap_ids = fields.One2many('stock.batch.scrap.line.wizard', 'head_id', string='Stock Move Line')

    def action_batch_scrap(self):
        self.ensure_one()
        for rec in self:
            if len(rec.batch_scrap_ids) < 1:
                raise UserError(
                    _("Warning! You have to add atleast one Product!.")
                )
        for rec in self.batch_scrap_ids:
            if rec.product_id.type != 'product':
                return self.do_scrap()
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            available_qty = sum(self.env['stock.quant']._gather(rec.product_id,
                                                                self.src_location_id,
                                                                self.scrap_location_id,
                                                                self.partner_id,
                                                                strict=True).mapped('quantity'))
            scrap_qty = rec.product_uom._compute_quantity(rec.scrap_qty, rec.product_id.uom_id)
            if float_compare(available_qty, scrap_qty, precision_digits=precision) >= 0:
                return self.do_scrap()
            else:
                ctx = dict(self.env.context)
                ctx.update({
                    'default_product_id': rec.product_id.id,
                    'default_location_id': self.src_location_id.id,
                    'default_scrap_id': self.id
                })
                return {
                    'name': _('Insufficient Quantity'),
                    'view_mode': 'form',
                    'res_model': 'stock.warn.insufficient.qty.scrap',
                    'view_id': self.env.ref('stock.stock_warn_insufficient_qty_scrap_form_view').id,
                    'type': 'ir.actions.act_window',
                    'context': ctx,
                    'target': 'new'
                }

    def do_scrap(self):
        for rec in self.batch_scrap_ids:
            available_qty = sum(self.env['stock.quant']._gather(rec.product_id,
                                                                self.src_location_id,
                                                                self.scrap_location_id,
                                                                self.partner_id,
                                                                strict=True).mapped('quantity'))
            quant_id = sum(self.env['stock.quant']._gather(rec.product_id,
                                                                self.src_location_id,
                                                                self.scrap_location_id,
                                                                self.partner_id,
                                                                strict=True).mapped('id'))

            scrap_qty = rec.product_uom._compute_quantity(rec.scrap_qty, rec.product_id.uom_id)
            qty_available = available_qty - scrap_qty
            query = """UPDATE stock_quant SET quantity = %s WHERE id = %s"""
            self.env.cr.execute(query, [qty_available, quant_id])

            self.env['stock.scrap'].create({
                'state': 'done',
                'name': self.env['ir.sequence'].next_by_code('stock.scrap') or _('New'),
                'product_id': rec.product_id.id,
                'product_uom_id': rec.product_uom.id,
                'location_id': self.src_location_id.id,
                'scrap_location_id': self.scrap_location_id.id,
                'owner_id': self.partner_id.id,
                # 'order_by_id': self.order_by_id.id,
                'origin': self.source_document,
                'scrap_qty': rec.scrap_qty,
                'date_done': fields.Datetime.now(),
            })
        return True


class StockBatchScrapLineWizard(models.TransientModel):
    _name = 'stock.batch.scrap.line.wizard'
    _description = 'Stock Batch Scrap Line Wizard'

    head_id = fields.Many2one('stock.batch.scrap.wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    scrap_qty = fields.Float(string='Scrap Quantity', default=0, required=True)
    product_uom = fields.Many2one('uom.uom', string='UoM', related='product_id.uom_id', readonly=True,
                        domain="[('category_id', '=', product_uom_category_id)]")
    product_available_qty = fields.Float(string='Stock Qty', related='product_id.qty_available', readonly=True)
    product_cost_price = fields.Float(string='Cost Price', related='product_id.standard_price', readonly=True)
    product_other_cost = fields.Float(string='Other Cost', related='product_id.other_cost', readonly=True)

    @api.constrains('head_id', 'product_id')
    def _check_unique_constraint_product(self):
        for rec in self:
            msg = 'Product "%s"' % rec.product_id.name
            envobj = self.env['stock.batch.scrap.line.wizard']
            conditionlist = [('head_id', '=', rec.head_id.id), ('product_id', '=', rec.product_id.id)]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)