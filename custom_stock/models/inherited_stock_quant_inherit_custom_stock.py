from odoo import models, fields, api
from odoo.addons.helper import validator
from psycopg2 import OperationalError


class InheritedStockQuantCustomStock(models.Model):
    _inherit = 'stock.quant'

    other_cost_rate = fields.Float(default=0, store=True, digits=(16, 3), string='Other Cost Rate')
    total_cost_rate = fields.Float(string='Total Other Cost', default=0)
    reserved_quantity = fields.Float(default=0)
    net_value = fields.Float(string='Net Value', default=0, compute='_compute_net_value', store=True)

    @api.depends('quantity', 'other_cost_rate', 'total_cost_rate')
    def _compute_net_value(self):
        for rec in self:
            rec.net_value = rec.value + rec.total_cost_rate


    # @api.model
    # def _update_available_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None,
    #                                in_date=None):
    #     self = self.sudo()
    #     quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id,
    #                           strict=True)
    #     if lot_id and quantity > 0:
    #         quants = quants.filtered(lambda q: q.lot_id)
    #
    #     incoming_dates = [d for d in quants.mapped('in_date') if d]
    #     incoming_dates = [fields.Datetime.from_string(incoming_date) for incoming_date in incoming_dates]
    #     if in_date:
    #         incoming_dates += [in_date]
    #     if incoming_dates:
    #         in_date = fields.Datetime.to_string(min(incoming_dates))
    #     else:
    #         in_date = fields.Datetime.now()
    #
    #     for quant in quants:
    #         try:
    #             with self._cr.savepoint(flush=False):
    #                 self._cr.execute("SELECT 1 FROM stock_quant WHERE id = %s FOR UPDATE NOWAIT", [quant.id],
    #                                  log_exceptions=False)
    #                 quant.write({
    #                     'quantity': quant.quantity + quantity,
    #                     'in_date': in_date,
    #                 })
    #                 break
    #         except OperationalError as e:
    #             if e.pgcode == '55P03':  # could not obtain the lock
    #                 continue
    #             else:
    #                 self.clear_caches()
    #                 raise
    #     else:
    #         self.create({
    #             'product_id': product_id.id,
    #             'location_id': location_id.id,
    #             'quantity': quantity,
    #             'lot_id': lot_id and lot_id.id,
    #             'package_id': package_id and package_id.id,
    #             'owner_id': owner_id and owner_id.id,
    #             'in_date': in_date,
    #         })
    #     #stock_rows = self.env['stock.quant'].search([('product_id', '=', product_id.id), ('quantity', '>', 0)])
    #     stock_rows = self.env['stock.quant'].search([('product_id', '=', product_id.id), ('quantity', '>=', 0)])
    #     for data in stock_rows:
    #         total_value = data.quantity * data.other_cost_rate
    #         data.total_cost_rate = total_value
    #
    #     return self._get_available_quantity(product_id, location_id, lot_id=lot_id, package_id=package_id,
    #                                         owner_id=owner_id, strict=False,
    #                                         allow_negative=True), fields.Datetime.from_string(in_date)

