# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################
from odoo import api, fields, models, _
from odoo.http import request
from functools import partial
import datetime
import pytz

class PosKitchenOrder(models.Model):
    _name = 'pos.kitchen.order'
    _order = 'id desc'
    _rec_name = 'pos_reference'
    _description = 'POS Kitchen Order'

    name = fields.Char(string="Name",readonly=True)
    is_changed = fields.Boolean(default=False, string="Is Changed",readonly=True)
    order_progress = fields.Selection([
        ('new', 'New'), ('accepted', 'New'),('pending', 'Pending'),('partially_done', 'Partially Done'), 
        ('done', 'Done'),('cancel', "Cancel"), ('picked_up', 'Picked Up')], 
        string="Order Progress",readonly=True)
    config_id = fields.Many2one('pos.config', string="POS Config",readonly=True)
    session_id = fields.Many2one('pos.session', string="POS Session",readonly=True)
    is_state_updated = fields.Boolean(string="Is state Updated",readonly=True)
    kitchen_order_name = fields.Char(string="Token NO.",readonly=True)
    user_id = fields.Many2one('res.users', string="Users",readonly=True)
    amount_total = fields.Float(string="Amount Total",readonly=True)
    out_of_stock_products = fields.One2many('product.product', 'related_kitchen_order', string="Out Of Stock Products",readonly=True)
    cancellation_reason = fields.Char(string="Cancellation Reason",readonly=True)
    pos_reference = fields.Char(string="Pos Reference",readonly=True)
    partner_id = fields.Many2one('res.partner', string="Partner",readonly=True)
    date_order = fields.Datetime(string="DateTime",readonly=True)
    lines = fields.One2many('pos.kitchen.orderline','order_id', string="kitchen Orderlines" ,readonly=True)
    screen_progress = fields.Text(string="Screen Progress",readonly=True)
    order_type = fields.Selection([('takeaway', 'Takeaway'), ('dining', 'Dining')], string="Order Type",readonly=True)
    floor_id = fields.Many2one("restaurant.floor",string="Floor",readonly=True)
    table_id = fields.Many2one("restaurant.table",string="Table No",readonly=True)
    screen_session_id = fields.Many2one('pos.screen.session', string='Session', required=True, domain="[('state', '=', 'opened')]", states={'draft': [('readonly', False)]}, readonly=True)
    
    def done_screen_pending_order(self, session_id):
        records = self.search([('screen_session_id', '=', session_id), ('order_progress', 'not in', ['done', 'cancel', 'picked_up'])])
        if(records):
            for rec in records:
                rec.sudo().write({
                    'order_progress': 'cancel',
                    'is_state_updated': True,
                })
        session = self.env['pos.screen.session'].browse(session_id)
        session.action_pos_screen_session_closing_control()

    @api.model
    def done_pos_pending_order(self, session_id):
        records = self.search([('session_id', '=', session_id), ('order_progress', 'not in', ['done', 'cancel', 'picked_up'])])
        if(records):
            for rec in records:
                rec.sudo().write({
                    'order_progress': 'cancel',
                    'is_state_updated': True,
                })

    @api.model_create_multi
    def create(self, vals_list):
        data = {}
        res = super(PosKitchenOrder, self).create(vals_list)
        data = self.fetch_kitchen_order_data(res.screen_session_id.screen_id.id, res.id)
        self.env['pos.session']._notify_changes_in_kitchen(data, True, res._name)
        return res
    
    def write(self, vals):
        data = {}
        res = super(PosKitchenOrder, self).write(vals)
        data = self.fetch_kitchen_order_data(self.screen_session_id.screen_id.id, self.id)
        self.env['pos.session']._notify_changes_in_kitchen(data, False, self._name)
        return res

    def fetch_kitchen_order_data(self, config_id, order_id):
        pos_screen_data = self.env['pos.screen.config'].sudo().browse(config_id)
        order = self.env['pos.kitchen.order'].sudo().search([
            ('order_progress', 'in', ['accepted', 'new','pending', 'partially_done']), 
            ('date_order', '>=', datetime.date.today()), 
            ('config_id', 'in', pos_screen_data.pos_config_ids.ids),
            ('id', '=', order_id)
        ])
        orders = [order]
        order_data = self.get_data_from_orders(pos_screen_data, orders=orders)
        order_data['screen_id'] = config_id
        return order_data

    def get_data_from_orders(self, pos_screen_data, **kw):
        lines = self.env['pos.kitchen.orderline'].sudo().search_read([('order_id', '!=', False)])
        order_data = {
            'change_order_data': [],
            'lines': lines,
        }
        if kw.get('orders') and len(kw.get('orders')):
            orders_list = []
            product_data = {}
            for order in kw.get('orders'):
                self.extract_order_data('restaurant', order, orders_list, product_data, pos_screen_data)
            
            order_data.update({
                'orders': orders_list,
                'products': product_data,
            })

        if pos_screen_data.is_changed:
            order = self.env['pos.kitchen.order'].sudo().search([
                ('order_progress', 'in', ['cancel', 'pending', 'partially_done']), 
                ('date_order', '>=', datetime.date.today()), 
                ('config_id', 'in', pos_screen_data.pos_config_ids.ids), 
                ('is_changed', '=', True),
                ('id', '=', order['id'])
            ])
            vals = {'id': order.id, 'state': order.order_progress}
            product_category_wise = {}
            if order.order_progress in ['pending', 'partially_done']:
                for line in order.lines:
                    if not line.is_orderline_done:
                        count = 0
                        for categ in line.product_id.pos_categ_ids:
                            if categ in pos_screen_data.pos_category_ids and not count:
                                count += 1
                                line_vals = {
                                    'note':hasattr(line, 'note') and line.note or '',
                                    'display_name':line.display_name,
                                    'id':line.id,
                                    'qty_added':line.qty_added,
                                    'state':line.state,
                                    'qty_removed':line.qty_removed,
                                    'order_id':[line.order_id.id, line.order_id.name],
                                    'screen_config':pos_screen_data.id,
                                    'product_id':[line.product_id.id, line.full_product_name or line.product_id.name],
                                    'qty':line.qty,
                                    'discount':line.discount,
                                }
                                categ_id = categ.name+'-'+str(categ.id)
                                if categ_id not in product_category_wise:
                                    product_category_wise[categ_id] = {line.id: line_vals}
                                else:
                                    product_category_wise[categ_id].update({line.id: line_vals})                
                vals['product_category_wise'] = product_category_wise
            order_data['change_order_data'].append(vals)
            # order.sudo().write({'is_changed': False})
            pos_screen_data.sudo().write({'is_changed': False})
        return order_data

    def extract_order_data(self, order_type, order, orders_list, product_data, pos_screen_data):
        session = self.env['pos.session'].sudo().browse(order.session_id.id)
        config_id = order.config_id
        is_allowed_order = True
        has_category_product = []

        if len(pos_screen_data.pos_category_ids.ids):
            for line in order.lines:
                if not line.is_orderline_done:
                    for cat in line.product_id.pos_categ_ids:
                        if cat.id in pos_screen_data.pos_category_ids.ids:
                            id = line.product_id.id

                            if(id in product_data): product_data[id]['qty'] += line.qty
                            else:
                                product_data[id] = {
                                    'name' : line.product_id.display_name,
                                    'qty' : line.qty,
                                    'pos_categ_ids': line.product_id.pos_categ_ids.ids,
                                    'order_id':order.id,
                                    'product_id': id,
                                }

                            has_category_product.append(line.product_id)

        if order:
            order_date = order.date_order
            if request.env.context.get('tz'):
                user_tz = pytz.timezone(request.env.context.get('tz'))
                order_date = pytz.utc.localize(order.date_order).astimezone(user_tz)
            order_progress = 'pending' if session.config_id.auto_accept else 'new'
            if order.order_progress: order_progress = order.order_progress
            vals = {
                'id':order.id,
                'lines':[],
                'name':order.name,
                'amount_total':order.amount_total,
                'pos_name':order.config_id.name,
                'pos_reference':order.pos_reference,
                'kitchen_order_name':order.kitchen_order_name,
                'order_date':order_date.strftime("%H:%M:%S"),
                'order_progress':order_progress,
                'order_type':order.order_type,
                'table' : order.table_id.name,
                'members' : order.table_id.seats,
                'screen_config':pos_screen_data.id,
            }
            if order.partner_id:
                vals['partner_id'] = [order.partner_id.id, order.partner_id.name]
            else:
                vals['partner_id'] = False
            product_category_wise = {}
            for line in order.lines:
                # if not line.is_orderline_done:
                count = 0
                for categ in line.product_id.pos_categ_ids:
                    self.accumulate_line_data(line,vals,pos_screen_data,count,config_id,product_category_wise,categ)
            vals['total_items'] = len(vals['lines'])
            orders_list.append(vals)

    def accumulate_line_data(self, line, vals, pos_screen_data, count, config_id, product_category_wise, categ):
        if categ and categ in pos_screen_data.pos_category_ids and not count:
            count += 1
            line_vals = {
                'note':hasattr(line, 'note') and line.note or '',
                'display_name':line.display_name,
                'id':line.id,
                'state':line.state,
                'order_id':[line.order_id.id, line.order_id.name],
                'screen_config':pos_screen_data.id,
                'discount':line.discount,
                'qty':line.qty,
                'pos_categ_ids':[categ.id],
            }
            if hasattr(config_id, 'order_action') and config_id.order_action == 'order_button' and line and line.qty_added:
                line_vals['qty_added'] = line.qty_added
            if hasattr(config_id, 'order_action') and config_id.order_action == 'order_button' and line.qty_removed:
                line_vals['qty_removed'] = line.qty_removed

            product = line.read(['product_id'])

            if len(product):
                line_vals['product_id'] = list(product[0].get('product_id'))
                line_vals['product_id'][1] = line.full_product_name or line_vals['product_id'][1]
                if len(line_vals['product_id'][1].split(']')) == 2:
                    line_vals['product_id'][1] = line.full_product_name or line_vals['product_id'][1].split(']')[1]
            else:
                line_vals['product_id'] = [line.product_id.id,line.full_product_name or line.product_id.name]

            if categ:
                categ_id = categ.name+'-'+str(categ.id)
                if categ_id not in product_category_wise:
                    product_category_wise[categ_id] = {line.id: line_vals}
                else:
                    product_category_wise[categ_id].update({line.id: line_vals})
            else:
                categ_id = "General"+'-'+str(0)
                if categ_id not in product_category_wise:
                    product_category_wise[categ_id] = {line.id: line_vals}
                else:
                    product_category_wise[categ_id].update({line.id: line_vals})
                    
            vals['lines'].append(line_vals)
            vals['product_category_wise'] = product_category_wise

    def get_queue_orders_data(self, config_id):
        datetime_now = datetime.datetime.now()
        datetime_last_15_min = datetime_now - datetime.timedelta(minutes=15)
        datetime_last_hour = datetime_now - datetime.timedelta(hours=1)
        pos_screen_data = self.env['pos.screen.config'].sudo().browse(config_id)
        domain = ['pending', 'accepted', 'partially_done', 'new']
        orders = self.env['pos.kitchen.order'].sudo().search([
            ('order_progress', 'in', ['new', 'accepted','pending', 'partially_done', 'done']), 
            ('date_order', '>=', datetime.date.today()), 
            ('config_id', 'in', pos_screen_data.pos_config_ids.ids),
        ])
        data = self.get_data_from_orders(pos_screen_data, orders=orders)
        data['pending_orders'] = self.sudo().search_count([
            ('order_progress', 'in', domain), 
            ('date_order', '>=', datetime.date.today()), 
            ('config_id', 'in', pos_screen_data.pos_config_ids.ids),
        ])
        data['orders_last_hour'] = self.sudo().search_count([
            ('order_progress', 'in', domain), 
            ('date_order', '<=', datetime_now), 
            ('date_order', '>=', datetime_last_hour), 
            ('config_id', 'in', pos_screen_data.pos_config_ids.ids),
        ])
        data['orders_last_15_min'] = self.sudo().search_count([
            ('order_progress', 'in', domain), 
            ('date_order', '<=', datetime_now), 
            ('date_order', '>=', datetime_last_15_min), 
            ('config_id', 'in', pos_screen_data.pos_config_ids.ids),
        ])
        pos_screen_data = self.env['pos.screen.config'].sudo().search_read([('id', '=', config_id)])
        data['config'] = pos_screen_data[0]
        return data

    @api.model
    def process_order(self, config_id, order_id, status, reason):
        pos_screen_data = request.env['pos.screen.config'].sudo().search([('id', '=', config_id)])

        order = self.env['pos.kitchen.order'].sudo().browse(order_id)
        
        if(pos_screen_data and order):
            if(status in ['picked_up']):
                order.sudo().write({
                    'order_progress': status,
                    'is_state_updated': True,
                })
            else:
                is_orderline_done = False
                cancellation_reason = ''
                line_state = status

                if(status == 'accept'): line_state = 'in_queue'
                if(status == 'pending'): line_state = 'in_process'
                elif(status == 'done'):  
                    is_orderline_done = True
                    line_state = 'done'
                elif(status == 'cancel'): 
                    cancellation_reason = reason
                    line_state = 'cancel'

                for line in order.lines:
                    for cat in line.product_id.pos_categ_ids:
                        if cat.id in pos_screen_data.pos_category_ids.ids:
                            line.sudo().write({'state': line_state, 'is_orderline_done': is_orderline_done})

                if(status == 'done'):
                    order.sudo().write({
                        'order_progress': status,
                        'is_state_updated': True,
                    })
                    return
                order_progress = status

                for line in order.lines: 
                    if line.state == 'in_process': order_progress = 'pending'
                    if line.is_orderline_done:  order_progress = 'partially_done'

                if(status == 'accept'): order_progress = 'accepted'
                order.sudo().write({
                    'order_progress': order_progress,
                    'cancellation_reason' : cancellation_reason,
                    'is_state_updated': True,
                })

    @api.model
    def fetch_pos_kitchen_order(self, args):
        result = self.env['pos.kitchen.order'].search_read(args.get('pos_kitchen_order_domain'))
        return result

    @api.model
    def update_kitchen_order_progress(self,data):
        order_progresses = []
        orderline_qtys = []
        if len(data):
            int_list = [int(i) for i in data]
            orders = self.browse(int_list)
            order_progresses = orders.read(['order_progress'])
            orderlines = []
            for order in orders:
                orderlines += order.lines.ids
            orderline_qtys = self.env['pos.kitchen.orderline'].browse(orderlines).read(['total_qtys'])
        res =  {'progress':order_progresses,'qtys':orderline_qtys}
        return res

    @api.model
    def fetch_same_product_orderlines(self,order,product_id,curr_line_qty):
        kitchen_order = self.search([('pos_reference','=',order.get('name'))])
        lines = []
        for line in kitchen_order.lines:
            line_qty = line.qty + line.qty_added - line.qty_removed
            if line.product_id.id == product_id:
                lines.append(line.read())
        return lines

    @api.model
    def get_kitchen_order_data(self, data, is_order_validate, changes):
        order = self.search([('pos_reference','=',data['name'])])
        process_line = partial(self._kitchen_order_line_fields, session_id=data['pos_session_id'])
        pos_config_id = self.env['pos.session'].browse(data['pos_session_id']).config_id
        pos_config_id_val = pos_config_id.id if pos_config_id.id else None
        pos_screen_data = self.env['pos.screen.config'].search([("pos_config_ids",'=ilike', pos_config_id.id)])
        floor_id = False

        if data.get('table_id'):
            table_obj = self.env['restaurant.table'].browse([data.get('table_id')])
            if table_obj and table_obj.floor_id : floor_id = table_obj.floor_id.id
        
        order_id = {
            'orders' : [],
            'orderlines' : [],
        }

        if(not order):
            lines = data.get('lines')
            orderline_data = {}
            screen_dict = {}

            for pos_screen in pos_screen_data: screen_dict[pos_screen.id] = pos_screen.pos_category_ids.ids
            test=[]
            
            for config in pos_screen_data:
                for line in lines:
                    if line[2]['product_id'] not in test:
                        product = self.env['product.product'].search([('id', '=', line[2]['product_id'])])
                        if(list(set(product.pos_categ_ids.ids).intersection(set(config.pos_category_ids.ids)))):
                            if (config.id not in orderline_data) : orderline_data[config.id] = []
                            orderline_data[config.id].append(line)
                            test.append(line[2]['product_id'])
            
            order_list = []
            order_line_list = [] 

            for i in orderline_data:
                pos_screen_config = self.env['pos.screen.config'].search([('id', '=', i)])
                order = None
                res = {
                    'user_id':      data.get('user_id') or False,
                    'config_id':   pos_config_id_val,
                    'session_id':   data.get('pos_session_id'),
                    'screen_session_id': pos_screen_config.current_session_id.id,
                    'lines':        [process_line(l) for l in orderline_data.get(i)] if orderline_data.get(i) else False,
                    'pos_reference': data.get('name'),
                    'partner_id':   data.get('partner_id') or False,
                    'date_order':   data.get('date_order').replace('T', ' ')[:19],
                    'amount_total':  data.get('amount_total'),
                    'table_id':  data.get('table_id'),
                    'floor_id':  floor_id,
                    'order_type':data.get('order_type'),
                }
                
                if data.get('is_kitchen_order') and not order and not is_order_validate and pos_config_id.order_action == 'order_button':
                    sequence_date_wise = self.env['token.perday'].search([],limit=1)
                    if sequence_date_wise:
                        res.update({
                            'kitchen_order_name':sequence_date_wise.sequence_id._next(),
                            'order_progress':'pending' if pos_config_id.auto_accept else 'new'
                        })
                    else:
                        self.env['token.perday'].search([]).unlink()
                        sequence_date_wise = self.env['token.perday'].create({
                            'name':"token"+datetime.date.today().strftime("%Y-%m-%d")
                        })
                        res.update({
                            'kitchen_order_name':sequence_date_wise.sequence_id._next(),
                            'order_progress':'pending' if pos_config_id.auto_accept else 'new'
                        })
                else:
                    res.update({'kitchen_order_name':data.get('token_no'),
                        'order_progress':'pending' if pos_config_id.auto_accept else 'new'
                    })

                if not order and ((is_order_validate and pos_config_id.order_action == 'validation') or (pos_config_id.order_action == 'order_button' and not is_order_validate)):
                    order = self.create(res)
                    if pos_config_id.auto_accept: order.lines.write({'state':'in_process'})
                    if order:
                        has_category_product = []
                        pos_config_id = order.config_id
                        is_allowed_order = True
                        if hasattr(pos_config_id,'order_action'):
                            if len(pos_screen_data.pos_category_ids.ids):
                                for line in order.lines:
                                    if not line.is_orderline_done:
                                        for cat in line.product_id.pos_categ_ids:
                                            if cat.id in pos_screen_data.pos_category_ids.ids:
                                                has_category_product.append(line.product_id)

                                if len(has_category_product) == 0: is_allowed_order = False

                    if is_allowed_order :
                        vals = {
                            'lines'				:[],
                            'name'				:order.name,
                            'amount_total'		:order.amount_total,
                            'pos_reference'		:order.pos_reference,
                            'order_progress'	:order.order_progress,
                            'date_order'		:order.date_order,
                            'kitchen_order_name':order.kitchen_order_name,
                        }
                        if order.table_id: vals['table_id'] = [order.table_id.id,order.table_id.name]
                        if order.floor_id: vals['floor_id'] = [order.floor_id.id,order.floor_id.name]
                        if order.partner_id: vals['partner_id'] = [order.partner_id.id, order.partner_id.name]
                        else: vals['partner_id'] = False
                        vals['id'] = order.id
                        for line in order.lines:
                            if not line.is_orderline_done:
                                count = 0
                                for categ in line.product_id.pos_categ_ids:
                                    if categ in pos_screen_data.pos_category_ids and not count:
                                        count += 1
                                        vals['lines'].append(line.id)
                                        rec = self.env
                                        line_vals = {
                                            'display_name'	: line.full_product_name,
                                            'id'			: line.id,
                                            'order_id'		: [line.order_id.id, line.order_id.name],
                                            'product_id'	: [line.product_id.id, line.product_id.name],
                                            'qty'			: line.qty,
                                            'total_qtys'	: line.qty,
                                            'type_of_update': 'new',
                                            'wk_cid'        : line.wk_cid,
                                            'discount'      : line.discount,
                                            'note'          : line.note,
                                        }
                                        order_line_list.append(line_vals)
                        vals['total_items'] = len(vals['lines'])
                        order_list.append(vals)
                        order_id['orders'] = order_list
                        order_id['orderlines'] = order_line_list

            return order_id['orders']
        else:
            if not is_order_validate and pos_config_id.order_action == 'order_button':
                orders = self.search([('pos_reference','=',data['name'])])
                order_list = []
                order_line_list = [] 
                
                for order in orders:
                    kitchen_screen_config = self.env['pos.screen.config'].search([('current_session_id', '=', order.screen_session_id.id)])
                    if kitchen_screen_config: kitchen_screen_config.write({'is_changed':True})
                    
                    if changes:
                        order_id['updated_orderlines'] = {}
                        lines_by_product_id = {line.product_id.id:line for line in order.lines}
                        lines_by_product_cid = {line.wk_cid:line for line in order.lines}
                        new_lines = []

                        if changes.get('new'):
                            for line in changes.get('new'):
                                if line.get('product_id') in lines_by_product_id:
                                    if (order.order_progress == 'done' or lines_by_product_id[line.get('product_id')].is_orderline_done or line.get('discount') >0) or (line.get('wk_cid') not in lines_by_product_cid):
                                        previous_quantity = lines_by_product_id[line.get('product_id')].total_qtys + lines_by_product_id[line.get('product_id')].qty_added - lines_by_product_id[line.get('product_id')].qty_removed
                                        previous_first_quantity = lines_by_product_id[line.get('product_id')].qty
                                        if order.order_progress == 'done':
                                            order.order_progress = 'pending' if pos_config_id.auto_accept else 'new'
                                        
                                        if (line.get('wk_cid') not in lines_by_product_cid):
                                            new_lines.append((0,0,{
                                                'product_id':line.get('product_id'),
                                                'qty':line.get('quantity'),
                                                'state':'in_process',
                                                'full_product_name'	:line.get('name'),
                                                'previous_quantity':previous_quantity,
                                                'previous_first_quantity':previous_first_quantity,
                                                'qty_added':0,
                                                'qty_removed':0,
                                                'total_qtys':line.get('quantity'),
                                                'is_orderline_done':False,
                                                'wk_cid':line.get('wk_cid'),
                                                'discount': line.get('discount')
                                            }))					
                                    
                                    else:
                                        lines_by_product_cid[line.get('wk_cid')].total_qtys += line.get('quantity')
                                        if lines_by_product_cid[line.get('wk_cid')].qty_added:
                                            lines_by_product_cid[line.get('wk_cid')].qty_added += line.get("quantity")
                                        else:
                                            lines_by_product_cid[line.get('wk_cid')].qty_added = line.get("quantity")
                                        if lines_by_product_cid[line.get('wk_cid')].previous_quantity:
                                            lines_by_product_cid[line.get('wk_cid')].qty_added = line.get("quantity")	
                                else:
                                    prod = self.env['product.product'].search([('id', '=', line.get('product_id'))])

                                    if(list(set(prod.pos_categ_ids.ids).intersection(set(kitchen_screen_config.pos_category_ids.ids)))):
                                        if order.order_progress == 'done': 
                                            order.order_progress = 'pending' if pos_config_id.auto_accept else 'new'
                                        new_lines.append((0,0,{
                                            'product_id':line.get('product_id'),
                                            'qty':line.get('quantity'),
                                            'state':'in_process',
                                            'full_product_name' :line.get('name'),
                                            'wk_cid':line.get('wk_cid'),
                                            'discount': line.get('discount')
                                        }))
                            order.write({'lines':new_lines})
                        
                        if changes.get('cancelled'):
                            for line in changes.get('cancelled'):
                                if line.get('product_id') in lines_by_product_id:
                                    lines_by_product_id[line.get('product_id')].total_qtys -= line.get('quantity')
                                    if lines_by_product_id[line.get('product_id')].qty_removed >0:
                                        lines_by_product_id[line.get('product_id')].qty_removed += line.get("quantity")
                                    else:
                                        lines_by_product_id[line.get('product_id')].qty_removed = line.get("quantity")
                    
    def _kitchen_order_line_fields(self, line, session_id=None):
        line = [line[0], line[1], {k: v for k, v in line[2].items() if k in ['display_name','product_id','qty','price_unit','note','discount','full_product_name','total_qtys','wk_cid']}]
        return line

    def get_kitchen_orders(self, config_id):
        if(config_id):
            res = self.search_read([('config_id', '=', config_id), ('date_order', '>=', datetime.date.today())])
            return res

class PosKitchenOrderLines(models.Model):
    _name = 'pos.kitchen.orderline'
    _description = "POS Kitchen Orderline"

    order_id = fields.Many2one('pos.kitchen.order', string="Related Pos Order")
    display_name = fields.Char(string="Display Name")
    is_orderline_done = fields.Boolean(string="Is Orderline Done", default=False)
    product_id = fields.Many2one('product.product', string="Product")
    state = fields.Selection([('cancel', "Cancel"), ('in_process', 'In Process'), ('done', 'Done'), ('in_queue', 'In Queue'), ('new', 'New')], string="State", default="new")
    qty = fields.Integer(string="Quantity" ,readonly=True)
    note = fields.Char(string="Note")
    previous_quantity = fields.Integer(string="Previous Quantity",default=0)
    previous_first_quantity = fields.Integer(string="Previous First Quantity",default=0)
    qty_added = fields.Integer(string="Quantities Added",default=0)
    qty_removed = fields.Integer(string="Quantities Removed",default=0)
    total_qtys = fields.Integer(string="Total Quantities",default=0)
    price_unit = fields.Float(string="Price")
    full_product_name = fields.Char(string="Full Product Name")
    wk_cid = fields.Char()
    discount = fields.Float(string='Discount (%)', digits=0, default=0.0)
    full_product_name = fields.Char()

    @api.model
    def fetch_pos_kitchen_orderline(self, args):
        result = self.env['pos.kitchen.orderline'].search_read(args.get('pos_kitchen_orderline_domain'))
        return result
