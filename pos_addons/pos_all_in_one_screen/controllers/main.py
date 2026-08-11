# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################
from odoo.http import request
from odoo import http
import pytz
import datetime
import logging
_logger = logging.getLogger(__name__)

class KitchenScreenBase(http.Controller):
    @http.route('/pos/kitchen/<int:id>/screen', type='http', auth='none')
    def display_kitchen_screen(self, **kw):
        try:
            config_id = kw.get('id')
            pos_kitchen_config = request.env['pos.screen.config'].sudo().browse(kw.get('id'))
            product_data = request.env['product.product'].sudo().search([
                ('available_in_pos', '=', True), 
                ('pos_categ_ids', 'in', pos_kitchen_config.pos_category_ids.ids)
            ])
            request.env['pos.session']._notify_changes_in_kitchen([], True)
            order_data = self.get_queue_orders_data(config_id)
            
            notifications =  request.env['pos.kitchen.order'].sudo().search([
                ('order_progress', 'in', ['new']), 
                ('date_order', '>=', datetime.date.today()), 
                ('config_id', 'in', pos_kitchen_config.pos_config_ids.ids),
                ('screen_session_id', '=', pos_kitchen_config.current_session_id.id),
            ])
            notifications = self.get_data_from_orders(True, pos_kitchen_config, pos_orders=[], orders=notifications);
            
            pending_orders = request.env['pos.kitchen.order'].sudo().search_count([
                ('order_progress', 'in', ['new', 'accepted','pending', 'partially_done']), 
                ('date_order', '>=', datetime.date.today()), 
                ('config_id', 'in', pos_kitchen_config.pos_config_ids.ids),
                ('screen_session_id', '=', pos_kitchen_config.current_session_id.id),
            ])
            
            datetime_now = datetime.datetime.now()
            datetime_last_15_min = datetime_now - datetime.timedelta(minutes=15)
            datetime_last_hour = datetime_now - datetime.timedelta(hours=1)

            orders_last_hour = request.env['pos.kitchen.order'].sudo().search_count([
                ('order_progress', 'in', ['pending', 'accepted', 'partially_done', 'new']), 
                ('date_order', '<=', datetime_now), 
                ('date_order', '>=', datetime_last_hour), 
                ('config_id', 'in', pos_kitchen_config.pos_config_ids.ids),
                ('screen_session_id', '=', pos_kitchen_config.current_session_id.id),
            ])

            orders_last_15_min = request.env['pos.kitchen.order'].sudo().search_count([
                ('order_progress', 'in', ['pending', 'accepted', 'partially_done', 'new']), 
                ('date_order', '<=', datetime_now), 
                ('date_order', '>=', datetime_last_15_min), 
                ('config_id', 'in', pos_kitchen_config.pos_config_ids.ids),
                ('screen_session_id', '=', pos_kitchen_config.current_session_id.id),
            ])
            
            result = request.render('pos_all_in_one_screen.pos_kitchen_screen_template', qcontext = {
                'data': order_data,
                'screen_config': pos_kitchen_config,
                'product_data': product_data,
                'notifications': notifications,
                'pending_orders' : pending_orders,
                'order_last_hour' : orders_last_hour,
                'orders_last_15_min' : orders_last_15_min,
            })
            return result
        except Exception as e:
            _logger.info("*************Exception************:%r", e)

    def get_data_from_orders(self, isUpdateTime, pos_screen_data, **kwargs):
        order_data = {
            'last_order_time': False,
            'order_data': [],
            'change_order_data': [],
            'product_data' : {},
        }
        if (kwargs.get('orders') and len(kwargs.get('orders')) or pos_screen_data.is_changed):
            orders_list = []
            product_data = {}

            if kwargs.get('orders'):
                for order in kwargs.get('orders'):
                    self.extract_order_data(order, orders_list, product_data, pos_screen_data)

            pos_screen_data = request.env['pos.screen.config'].sudo().browse(kwargs.get('id'))
            order_data.update({
                'order_data': orders_list,
                'product_data': product_data,
            })

            if pos_screen_data.is_changed:
                changed_restaurant_orders = request.env['pos.kitchen.order'].sudo().search([('order_progress', 'in', ['cancel', 'pending', 'partially_done']), (
                    'date_order', '>=', datetime.date.today()), ('config_id', 'in', pos_screen_data.pos_config_ids.ids), ('is_changed', '=', True)], order="id asc")
                for order in changed_restaurant_orders:
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
                                            'qty_added': line.qty_added,
                                            'state':line.state,
                                            'qty_removed':line.qty_removed,
                                            'order_id':[line.order_id.id, line.order_id.name],
                                            'screen_config':pos_screen_data.id,
                                            'product_id':[line.product_id.id, line.full_product_name or line.product_id.name],
                                            'qty':line.qty,
                                        }                 
                                        categ_id = categ.name+'-'+str(categ.id)
                                        if categ_id not in product_category_wise:
                                            product_category_wise[categ_id] = {line.id: line_vals}
                                        else:
                                            product_category_wise[categ_id].update({line.id: line_vals})
                        vals['product_category_wise'] = product_category_wise
                    order_data['change_order_data'].append(vals)
                    order.sudo().write({'is_changed': False})
                pos_screen_data.sudo().write({'is_changed': False})
        return order_data

    def extract_order_data(self, order, orders_list, product_data, pos_screen_data):
        config_id = order.config_id
        pos_screen_data = pos_screen_data
        is_allowed_order = True
        has_category_product = []

        if len(pos_screen_data.pos_category_ids.ids):
            for line in order['lines']:
                if not line.is_orderline_done:
                    for cat in line.product_id.pos_categ_ids:
                        if cat.id in pos_screen_data.pos_category_ids.ids:
                            id = line.product_id.id

                            qty = 0
                            if(line.qty_added): qty += line.qty_added
                            if(line.qty_removed): qty -= line.qty_removed
                            
                            if(id in product_data):
                                product_data[id]['qty'] += line.qty + qty
                            else:
                                product_data[id] = {
                                    'name' : line.product_id.display_name,
                                    'qty' : line.qty + qty,
                                    'pos_categ_ids': line.product_id.pos_categ_ids.ids,
                                }

                            has_category_product.append(line.product_id)

        order_date = order.date_order
        if request.env.context.get('tz'):
            user_tz = pytz.timezone(request.env.context.get('tz'))
            order_date = pytz.utc.localize(order.date_order).astimezone(user_tz)
        vals = {
            'lines':[],
            'name':order.name,
            'amount_total':order.amount_total,
            'pos_name':order.config_id.name,
            'pos_reference':order.pos_reference,
            'kitchen_order_name': order.kitchen_order_name,
            'order_date':order_date.strftime("%H:%M:%S"),
            'order_progress':order.order_progress,
            'order_type':order.order_type,
            'table' : order.table_id.name,
            'members' : order.table_id.seats,
        }

        if order.partner_id: vals['partner_id'] = [order.partner_id.id, order.partner_id.name]
        else: vals['partner_id'] = False
        
        vals['id'] = order.id

        product_category_wise = {}
        for line in order.lines:
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
                'done_line':"/pos/"+str(line.id)+"/done/orderline",
                'order_id': [line.order_id.id, line.order_id.name],
                'screen_config':pos_screen_data.id,
                'qty':line.qty,
            }
            if hasattr(config_id, 'order_action') and config_id.order_action == 'order_button' and line.qty_added:
                line_vals['qty_added'] = line.qty_added
            if hasattr(config_id, 'order_action') and config_id.order_action == 'order_button' and line.qty_removed:
                line_vals['qty_removed'] = line.qty_removed
            product = line.read(['product_id'])

            if len(product):
                line_vals['product_id'] = list(product[0].get('product_id'))
                line_vals['product_id'][1] = line.full_product_name or line_vals['product_id'][1]
                if len(line_vals['product_id'][1].split(']')) == 2:
                    line_vals['product_id'][1] = line.full_product_name or line_vals['product_id'][1].split(']')[1]
            else: line_vals['product_id'] = [line.product_id.id,line.full_product_name or line.product_id.name]
            
            if categ:
                categ_id = categ.name+'-'+str(categ.id)
                if categ_id not in product_category_wise:
                    product_category_wise[categ_id] = {line.id: line_vals}
                else:
                    product_category_wise[categ_id].update({line.id: line_vals})
            else:
                categ_id = "General"+'-'+str(0)
                if categ_id not in product_category_wise: product_category_wise[categ_id] = {line.id: line_vals}
                else: product_category_wise[categ_id].update({line.id: line_vals})
                    
            vals['lines'].append(line_vals)
            vals['product_category_wise'] = product_category_wise

    def get_queue_orders_data(self, config_id):
        pos_screen_data = request.env['pos.screen.config'].sudo().browse(config_id)
        orders = request.env['pos.kitchen.order'].sudo().search([
                ('order_progress', 'in', ['accepted' ,'done', 'pending', 'partially_done']), 
                ('date_order', '>=', datetime.date.today()), 
                ('config_id', 'in', pos_screen_data.pos_config_ids.ids)], 
        order="id asc")
        order_data = self.get_data_from_orders(True, pos_screen_data, orders=orders)
        return order_data
    
class ReviewScreenBase(http.Controller):
    @http.route('/pos/review/<int:id>/screen', type='http', auth='none')
    def display_review_screen(self, **kw):
        try:
            pos_review_config = request.env['pos.screen.config'].sudo().browse(kw.get('id'))
            result = request.render('pos_all_in_one_screen.pos_review_screen_template', qcontext = {
                'screen_data': pos_review_config,
            });
            return result
        except Exception as e:
            _logger.info("*************Exception************:%r", e)

class CartScreenBase(http.Controller):
    @http.route('/pos/cart/<int:id>/screen', type='http', auth='none')
    def display_cart_screen(self, **kw):
        try:
            pos_cart_config = request.env['pos.screen.config'].sudo().browse(kw.get('id'))
            result = request.render('pos_all_in_one_screen.pos_cart_screen_template', qcontext = { 'screen_data': pos_cart_config })
            return result
        except Exception as e:
            _logger.info("*************Exception************:%r", e)