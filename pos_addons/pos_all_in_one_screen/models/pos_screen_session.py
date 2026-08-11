# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class PosScreenSession(models.Model):
    _name = 'pos.screen.session'
    _order = 'id desc'
    _description = 'Handles Pos Screen Sessions'

    SCREEN_SESSION_STATE = [
        ('opening_control', 'Opening Control'),  # method action_pos_session_open
        ('opened', 'In Progress'),               # method action_pos_session_closing_control
        ('closing_control', 'Closing Control'),  # method action_pos_session_close
        ('closed', 'Closed & Posted'),
    ]
    screen_id = fields.Many2one('pos.screen.config', string="Screen", readonly=True)
    name = fields.Char(string='Session ID', required=True, readonly=True, default='/')
    user_id = fields.Many2one('res.users', string='Opened By', required=True, index=True, readonly=True, default=lambda self: self.env.uid, ondelete='restrict')
    start_at = fields.Datetime(string='Opening Date', readonly=True)
    stop_at = fields.Datetime(string='Closing Date', readonly=True, copy=False)
    state = fields.Selection(SCREEN_SESSION_STATE, string='Status', required=True, readonly=True, index=True, copy=False, default='opening_control')
    order_ids = fields.One2many('pos.kitchen.order', 'screen_session_id',  string='Orders')
    review_ids = fields.One2many('pos.review.record', 'screen_session_id',  string='Reviews')
    order_count = fields.Integer(compute='_compute_order_count')
    review_count = fields.Integer(compute='_compute_review_count')
    user_id = fields.Many2one('res.users', string='Opened By', required=True, index=True, readonly=True, default=lambda self: self.env.uid, ondelete='restrict')

    def _compute_order_count(self):
        for session in self: session.order_count = len(session.order_ids)

    def _compute_review_count(self):
        for session in self: session.review_count = len(session.review_ids)

    @api.constrains('screen_id')
    def _check_pos_config(self):
        if self.search_count([('state', '!=', 'closed'), ('screen_id', '=', self.screen_id.id)]) > 1:
            raise ValidationError(_("Another session is already opened for this point of sale."))
    
    def action_view_order(self):
        return {
            'name': _('Kitchen Orders'),
            'res_model': 'pos.kitchen.order',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('pos_all_in_one_screen.view_pos_kitchen_order_tree').id, 'tree'),
                (self.env.ref('pos_all_in_one_screen.view_pos_pos_kitchen_order_form').id, 'form'),
                ],
            'type': 'ir.actions.act_window',
            'domain': [('screen_session_id', 'in', self.ids)],
        }

    def open_frontend_cb(self):
        if not self.ids: return {}
        return self.screen_id.open_ui()
    
    def action_pos_screen_session_closing_control(self):
        records = self.env['pos.kitchen.order'].search([('screen_session_id', '=', self.id), ('order_progress', 'not in', ['done', 'cancel', 'picked_up'])])
        if(records):
            return {
                'name':'Pending Kitchen Orders',
                'view_mode': 'form',
                'view_id': False,
                'res_model': 'pos.close.screen.session.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'domain': '[]',
                'context': {'session_id': self.id}
            }
        else:
            for session in self:
                if session.state == 'closed': raise UserError(_('This session is already closed.'))
                return session._validate_session()
        
    def _validate_session(self):
        self.ensure_one()
        self.write({'state': 'closing_control', 'stop_at': fields.Datetime.now()})
        self.write({'state': 'closed'})
        self.env['pos.session']._notify_changes_in_kitchen([], True, 'pos.screen.session')
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            screen_id = vals.get('screen_id') or self.env.context.get('default_screen_id')
            if not screen_id: raise UserError(_("You should assign a POS Screen to your session."))

            ctx = dict(self.env.context)

            pos_name = self.env['ir.sequence'].with_context(ctx).next_by_code('pos.session')
            if vals.get('name'): pos_name += ' ' + vals['name']

            vals.update({
                'name': pos_name,
                'screen_id': screen_id,
            })

        if self.user_has_groups('point_of_sale.group_pos_user'):
            sessions = super(PosScreenSession, self).create(vals_list)
        else:
            sessions = super(PosScreenSession, self).create(vals_list)
        sessions.action_pos_session_open()
        return sessions
    
    def action_pos_session_open(self):
        for session in self.filtered(lambda session: session.state == 'opening_control'):
            values = {}
            if not session.start_at: values['start_at'] = fields.Datetime.now()
            values['state'] = 'opened'
            session.write(values)
        return True
