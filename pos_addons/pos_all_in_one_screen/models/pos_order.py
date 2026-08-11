# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################
from odoo import api, fields, models, _
from itertools import groupby
import datetime

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    is_orderline_done = fields.Boolean(string="Is Orderline Done", default=False)
    state = fields.Selection([('cancel', "Cancel"), ('in_process', 'In Process'), ('done', 'Done'), ('in_queue', 'In Queue'), ('new', 'New')], string="State", default="new")
    qty_added = fields.Integer(string="Quantities Added",default=0)
    qty_removed = fields.Integer(string="Quantities Removed",default=0)
    kitchen_sent_qty = fields.Float("Sent Qty")
    is_kitchen_sent = fields.Boolean(default="False")
    wk_cid = fields.Char()
    mp_dirty = fields.Boolean(default="False")
    
class PosOrder(models.Model):
    _inherit = 'pos.order'

    order_progress = fields.Selection([('cancel', "Cancel"), ('pending', 'Pending'), ('done', 'Done'), ('partially_done', 'Partially Done'), ('new', 'New')], string="Order Progress",readonly=True)
    screen_progress = fields.Text(string="Screen Progress",readonly=True)
    kitchen_order_name = fields.Char(string="Kitchen Order",readonly=True)
    cancellation_reason = fields.Char(string="Cancellation Reason",readonly=True)
    is_state_updated = fields.Boolean(string="Is state Updated")
    out_of_stock_products = fields.One2many('product.product', 'related_order', string="Out Of Stock Products")
    kitchen_screen_id = fields.Many2one('pos.screen.config', string="Pos Kitchen Screen",readonly=True)
    order_type = fields.Selection([('takeaway', 'Takeaway'), ('dining', 'Dining')], string="Order Type",readonly=True)
    review_record_id = fields.Many2one('pos.review.record',string="PoS Order Review")
    is_kitchen_order = fields.Boolean(string="Is Kitchen Order")
    order_changes = fields.Text()
    removed_line = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        res = super(PosOrder, self).create(vals_list)
        data = self.search_read([('id', '=', res.id)])
        screen = self.env['pos.screen.config'].search([('related_id', '=', res.config_id.id)])
        if(screen): self.env['pos.session']._notify_changes_in_kitchen(data, True, 'pos.order')
        return res

    @api.model
    def get_token_number(self):
        token = ''
        sequence_date_wise = self.env['token.perday'].search([], limit=1)
        if len(sequence_date_wise) == 0:
            self.env['token.perday'].search([]).unlink()
            sequence_date_wise = self.env['token.perday'].create({'name': "token"+datetime.date.today().strftime("%Y-%m-%d")})
        token = sequence_date_wise.sequence_id._next()
        return token

    @api.model
    def update_order_progress(self, data):
        order_progresses = []
        if len(data):
            int_list = [int(i) for i in data]
            orders = self.browse(int_list)
            order_progresses = orders.read(['order_progress'])
        return order_progresses

    def _get_fields_for_draft_order(self):
        fields = super(PosOrder, self)._get_fields_for_draft_order()
        fields.extend([ 'order_changes','order_progress','removed_line'])
        return fields

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        session = self.env['pos.session'].sudo().browse(ui_order.get('pos_session_id'))
        if(hasattr(session.config_id, 'order_action') and session.config_id.order_action != 'order_button') or not hasattr(session.config_id, 'order_action'):
            pos_screen_data = self.env['pos.screen.config'].search([("pos_config_ids", 'in', session.config_id.id)])
            for data in pos_screen_data.ids:
                order_fields.update({
                    'kitchen_order_name': ui_order.get('token_no'),
                    'order_progress': 'pending' if session.config_id.auto_accept else 'new',
                    'kitchen_screen_id': data,
                    'order_type' : ui_order.get('order_type'),
                })
            if(hasattr(session.config_id, 'order_action')):
                order_fields.update({'is_kitchen_order': ui_order.get('is_kitchen_order')})
        order_fields['order_changes'] = ui_order.get('order_changes')
        order_fields['order_progress'] = ui_order.get('order_progress')
        order_fields['removed_line'] = ui_order.get('removed_line')
        return order_fields

    def _get_fields_for_order_line(self):
        fields = super(PosOrder, self)._get_fields_for_order_line()
        fields.extend(['kitchen_sent_qty','is_kitchen_sent','state','wk_cid','mp_dirty'])
        return fields

    def _get_order_lines(self, orders):
        order_lines = self.env['pos.order.line'].search_read(
                domain = [('order_id', 'in', [to['id'] for to in orders])],
                fields = self._get_fields_for_order_line())
        if order_lines != []:
            self._get_pack_lot_lines(order_lines)
        extended_order_lines = []
        for order_line in order_lines:
            order_line['product_id'] = order_line['product_id'][0]
            order_line['server_id'] = order_line['id']
            order_line['kitchen_sent_qty'] = order_line['kitchen_sent_qty']
            order_line['is_kitchen_sent'] = order_line['is_kitchen_sent']
            order_line['state'] = order_line['state']
            order_line['wk_cid'] = order_line['wk_cid']
            order_line['mp_dirty'] = order_line['mp_dirty']
            del order_line['id']
            if not 'pack_lot_ids' in order_line:
                order_line['pack_lot_ids'] = []
            extended_order_lines.append([0, 0, order_line])
        for order_id, order_lines in groupby(extended_order_lines, key=lambda x:x[2]['order_id']):
            next(order for order in orders if order['id'] == order_id[0])['lines'] = list(order_lines)
