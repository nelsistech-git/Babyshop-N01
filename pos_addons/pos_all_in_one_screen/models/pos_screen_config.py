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
from odoo.exceptions import UserError
import base64
import os
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class PosScreenConfig(models.Model):
    _name = 'pos.screen.config'
    _description = "POS Screen Configuration"

    name = fields.Char(string="Name")
    type = fields.Selection([('review', 'Review Screen'), ('cart', 'Cart Screen'),('kitchen', 'Kitchen Screen')], string="Screen Type", default="kitchen")
    url = fields.Char(string="Display Url", compute="compute_url")
    ip_address = fields.Char(string="IP Address")
    is_changed = fields.Boolean(default=False, string="Is Changed")
    
    # kitchen screen fields
    pos_config_ids = fields.Many2many('pos.config', string="Allowed POS")
    pos_category_ids = fields.Many2many('pos.category', string="Allowed POS Categories")
    orders_on_grid = fields.Selection([('2', 2), ('3', 3), ('4', 4), ('6', 6)], string="Orders On Grid Screen", default="3",)
    queue_order = fields.Selection([('new2old', "Newer To Older"), ('old2new', "Older To Newer")], default="new2old",)
    threshold_time = fields.Float(string='Max Order Duration')
    accepted_order_color = fields.Char(string="Accepted Order Colors")
    pending_order_color = fields.Char(string="Pending Order Colors")
    threshold_order_color = fields.Char(string="Threshold Order Colors")
    
    # review screen fields 
    show_rating_on_page = fields.Boolean(string="Show Rating On Page")
    welcome_screen_content = fields.Text(string="Welcome Screen")
    welcome_screen_heading = fields.Char(string="Welcome Screen Title",default="WELCOME",size=40)
    welcome_screen_subheading = fields.Char(string="Welcome Screen SubHeading",size=100)
    related_id = fields.Many2one('pos.config',string="Pos Config")
    welcome_screen_banner = fields.Binary(string="Welcome Screen Image")
    banner = fields.Binary(string="Banner Image")
    auto_review_screen_validate = fields.Boolean(string="Auto Show Review Screen On Validate",default=True)
    show_review_button = fields.Boolean(string="Show Review Button On Receipt Screen",default=True)
    title = fields.Text(string="Review Screen Title")
    welcome_screen_content = fields.Text(string="Welcome Screen")
    review_screen_content = fields.Text(string="Review Screen Content")
    welcome_screen_heading = fields.Char(string="Welcome Screen Title",default="WELCOME")
    welcome_screen_subheading = fields.Char(string="Welcome Screen SubHeading")
    is_show_content_box = fields.Boolean(string="Show Comment Box",default=True)
    screen_reset_timeout = fields.Integer(string="Review Screen Reset Time(in Seconds)")
    icons_smiley = fields.Binary(string="Icons Smiley",compute="compute_base64")
    type_of_icons = fields.Selection([('star','Star Rating'),('smiley','Smiley Icons')],default="smiley",string="Type Of Review Icons")
    blank_gif = fields.Binary(string="Blank Gif",compute="compute_base64")

    # session related fields
    current_session_id = fields.Many2one('pos.screen.session', compute='_compute_current_session', string="Current Session", store=True)
    session_ids = fields.One2many('pos.screen.session', 'screen_id', string='Sessions')
    has_active_session = fields.Boolean(compute='_compute_current_session')
    current_session_state = fields.Char(compute='_compute_current_session')
    number_of_opened_session = fields.Integer(string="Number of Opened Session", compute='_compute_current_session')
    current_user_id = fields.Many2one('res.users', string='Current Session Responsible', compute='_compute_current_session_user')
    pending_order_count = fields.Integer(compute='_compute_order_count')
    proceed_order_count = fields.Integer(compute='_compute_order_count')
    category_names = fields.Char(compute='_compute_order_count')

    # Cart Fields
    show_cart_type = fields.Selection([('auto','Automatically On Adding Product'),('button','On Button Click')], string="Show Cart Products",help="User can choose whether he wants to add the product automatically on addition of product or on the click of a button",default="auto")
    show_product_image = fields.Boolean(string="Show Product Image",default=True)

    def compute_base64(self):
        for self_obj in self:
            try:
                path1 = os.path.join(os.path.dirname(__file__), "../static/description/icons-smileys.png")
                with open(path1, "rb") as img_file:
                    icons_string = base64.b64encode(img_file.read())
                self_obj.icons_smiley = icons_string
            except Exception as e:
                _logger.info("***************Exception**************:%r",e)
            try:
                path2 = os.path.join(os.path.dirname(__file__), "../static/description/blank.gif")
                with open(path2, "rb") as img_file:
                    blank_string = base64.b64encode(img_file.read())
                self_obj.blank_gif = blank_string
            except Exception as e:
                _logger.info("***************Exception**************:%r",e)

    def _compute_order_count(self):
        for rec in self:
            if(rec.type == 'kitchen'):
                pending_orders = rec.env['pos.kitchen.order'].search_count([('screen_session_id','=', rec.current_session_id.id), ('order_progress', 'not in', ['done', 'cancel', 'picked_up'])])
                proceed_orders = rec.env['pos.kitchen.order'].search_count([('screen_session_id','=', rec.current_session_id.id), ('order_progress', 'in', ['done', 'picked_up'])])
                rec.pending_order_count = pending_orders
                rec.proceed_order_count = proceed_orders
                categories = []
                for categ in rec.pos_category_ids:
                    categories.append(categ.name)
                rec.category_names = ', '.join(categories)
            else:
                rec.pending_order_count = 0
                rec.proceed_order_count = 0
                rec.category_names = ''

    @api.depends('session_ids')
    def _compute_current_session_user(self):
        for pos_screen in self:
            session = pos_screen.session_ids.filtered(lambda s: s.state in ['opening_control', 'opened', 'closing_control'])
            if session:
                pos_screen.current_session_state = session[0].state
                pos_screen.current_user_id = session[0].user_id
            else:
                pos_screen.current_session_state = False
                pos_screen.current_user_id = False

    @api.model
    def update_review_screen_status(self, reload, name):
        if(not reload): self.env['pos.session']._notify_changes_in_kitchen([], False, 'pos.order')
        else: 
            order = self.env['pos.order'].search_read([('pos_reference', '=', name)])
            if(order) : 
                order[0]['reload'] = True
                self.env['pos.session']._notify_changes_in_kitchen(order, True, 'pos.order')

    @api.model
    def getConfigData(self, config_id):
        data = self.search_read([('id', '=', config_id)]);
        status = self.search([('id', '=', config_id)]).related_id.has_active_session;
        return {
            'data' : data,
            'status' : status,
        }

    @api.model
    def review_screen(self, rating, feedback, order_id, partner_id, screen_session_id):
        order = self.env["pos.order"].sudo().search([('pos_reference', '=', str(order_id))])
        if order:
            vals = {
                'customer': partner_id or False,
                'review_rating': rating,
                'review_content': feedback,
                'name': order.id,
                'salesperson': order.user_id and order.user_id.id,
                'screen_session_id' : screen_session_id,
            }	
            try:
                related_record = self.env['pos.review.record'].sudo().search([('name','=',order.id)])
                if not related_record:
                    record = self.env['pos.review.record'].sudo().create(vals)
                    order.write({'review_record_id': record and record.id})
                else:
                    related_record.write({
                        'customer':vals.get('customer'),
                        'review_rating':vals.get('review_rating'),
                        'review_content':vals.get('review_content'),
                        'name':vals.get('name'),
                        'salesperson':vals.get('salesperson'),
                        'screen_session_id': vals.get('screen_session_id'),
                    })
                    order.write({'review_record_id':related_record and related_record.id})
            except Exception as e:
                _logger.info("*****************Exception review_screen*************:%r",e)

    def open_screen_config(self):
        return {
            "type":"ir.actions.act_window",
            'name':self.name,
            'res_model':'pos.screen.config',
            'view_mode':'form',
            'target':'current',
            'res_id': self.id,
        }
    
    def open_pos_config(self):
        return {
            "type":"ir.actions.act_window",
            'name':self.name,
            'res_model':'pos.config',
            'view_mode':'tree',
            'domain':['|', ('id','in',self.pos_config_ids.ids), ('id','=', self.related_id.id)],
            'target':'current',
        }
    
    def open_screen_sessions(self):
        return {
            "type":"ir.actions.act_window",
            'name':self.name,
            'res_model':'pos.screen.session',
            'view_mode':'tree,form',
            'domain':[('screen_id','=', self.id)],
            'target':'current',
        }
    
    def open_screen_orders(self):
        return {
            "type":"ir.actions.act_window",
            'name':self.name,
            'res_model':'pos.kitchen.order',
            'view_mode':'tree,form',
            'domain':[('screen_session_id','=', self.current_session_id.id)],
            'target':'current',
        }

    def open_screen_reviews(self):
        return {
            "type":"ir.actions.act_window",
            'name':self.name,
            'res_model':'pos.review.record',
            'view_mode':'tree,form',
            'domain':[('screen_session_id','=', self.current_session_id.id)],
            'target':'current',
        }
    
    @api.depends('pos_config_ids', 'type')
    def compute_url(self):
        for self_obj in self:
            if(self_obj.ip_address):
                self_obj.url = 'http://{}/pos/{}/{}/screen'.format(self_obj.ip_address, self_obj.type ,self_obj.id)
            else:
                self_obj.url = '{}pos/{}/{}/screen'.format(request.httprequest.host_url, self_obj.type ,self_obj.id)

    def open_ui(self):
        self.ensure_one()
        self._validate_fields(self._fields)
        return self._action_to_open_ui()
    
    # Methods to open the POS
    def _action_to_open_ui(self):
        if not self.current_session_id:
            self.env['pos.screen.session'].create({'user_id': self.env.uid, 'screen_id': self.id})
        if self.url: url = self.url
        else:
            base_url = request.httprequest.host_url
            url = '{}pos/{}/{}/screen'.format(base_url, self.type, self.id)
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "self",
        }

    def open_existing_session_cb(self):
        self.ensure_one()
        return self._open_session()

    def _open_session(self):
        return {
            'name': _('Session'),
            'view_mode': 'form,tree',
            'res_model': 'pos.screen.session',
            'res_id': self.current_session_id.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
        }

    @api.depends('session_ids', 'session_ids.state')
    def _compute_current_session(self):
        """If there is an open session, store it to current_session_id / current_session_State.
        """
        for screen_config in self:
            opened_sessions = screen_config.session_ids.filtered(lambda s: not s.state == 'closed')
            session = screen_config.session_ids.filtered(lambda s: not s.state == 'closed')
            # sessions ordered by id desc
            screen_config.number_of_opened_session = len(opened_sessions)
            screen_config.has_active_session = opened_sessions and True or False
            screen_config.current_session_id = session and session[0].id or False
            screen_config.current_session_state = session and session[0].state or False

    def open_opened_session_list(self):
        return {
            'name': _('Opened Sessions'),
            'res_model': 'pos.session',
            'view_mode': 'tree,kanban,form',
            'type': 'ir.actions.act_window',
            'domain': [('state', '!=', 'closed'), ('screen_id', '=', self.id)]
        }

    @api.model
    def update_cart_screen(self, data):
        self.env['pos.session']._notify_changes_in_kitchen(data, True,'cart_screen')
    
    @api.model
    def get_cart_screen_data(self, screen_id):
        screen = self.search([('id', '=', screen_id)])
        config = self.env['pos.config'].sudo().search([('id', '=', screen.related_id.id)])
        return {
            'screen' : screen,
            'pos_status' : config.has_active_session,
        }

class PosConfig(models.Model):
    _inherit = 'pos.config'

    pos_kitchen_screen = fields.Many2many('pos.screen.config', string="Pos Kitchen Screen")
    auto_accept = fields.Boolean('Auto Accept kitchen order', default=False)
    pos_review_screen = fields.One2many('pos.screen.config','related_id', string="Pos Review Screen")
    order_action = fields.Selection([('validation','On Order Validation'),('order_button','Clicking On Order Button')],default="order_button")
    is_done_orderline_restricted = fields.Boolean(default=False) 
    is_done_order_restricted = fields.Boolean(default=False)
        
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_pos_kitchen_screen = fields.Many2many(related='pos_config_id.pos_kitchen_screen', readonly=False)
    pos_auto_accept = fields.Boolean(related='pos_config_id.auto_accept', readonly=False)
    wk_pos_review_screen = fields.One2many(related='pos_config_id.pos_review_screen', readonly=False)
    pos_order_action = fields.Selection(related='pos_config_id.order_action', readonly=False)
    pos_is_done_orderline_restricted = fields.Boolean(related='pos_config_id.is_done_orderline_restricted', readonly=False)
    pos_is_done_order_restricted = fields.Boolean(related='pos_config_id.is_done_order_restricted', readonly=False)
    
    def open_screen_configuration(self):
        view_id_tree = self.env.ref('pos_all_in_one_screen.pos_screen_conf_form').id

        if self.pos_config_id.pos_review_screen and self.pos_config_id.pos_review_screen.id and self.pos_config_id.pos_review_screen.type == 'review':
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'pos.screen.config',
                'view_mode': 'form',
                'res_id':self.pos_config_id.pos_review_screen.id,
                'view_id':view_id_tree,
                'target': 'current'
            }
        else:
            raise UserError("No Customer Screen Settings available for this POS.")
     
class ProductProduct(models.Model):
    _inherit = "product.product"

    related_order = fields.Many2one('pos.order', string="related order")
    related_kitchen_order = fields.Many2one('pos.kitchen.order', string="Related Kitchen order")