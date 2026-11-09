# -*- coding: utf-8 -*-
import secrets
import string

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError


class RealEstateCreateUserWizard(models.TransientModel):
    """One-click 'give this customer / agent a user id and password'."""
    _name = 'real.estate.create.user.wizard'
    _description = 'Create Customer / Agent Login'

    partner_id = fields.Many2one('res.partner', string='Customer / Agent', required=True)
    role = fields.Selection([
        ('customer', 'Customer (sees only his own dashboard)'),
        ('agent', 'Agent (dashboard + CRM)'),
    ], string='Role', required=True, default='customer')
    login = fields.Char(string='User ID (Login)', required=True)
    password = fields.Char(string='Password', required=True, default=lambda self: self._generate_password())

    @api.model
    def _generate_password(self):
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _i in range(10))

    def action_create_user(self):
        self.ensure_one()
        if not (self.env.user.has_group('real_estate_project_management.group_real_estate_director')
                or self.env.user.has_group('real_estate_project_management.group_real_estate_sales_manager')):
            raise AccessError(_('Only Sales Managers / Directors can create customer or agent logins.'))
        Users = self.env['res.users'].sudo()
        if Users.search([('partner_id', '=', self.partner_id.id)]):
            raise UserError(_('This partner already has a login.'))
        if Users.with_context(active_test=False).search([('login', '=', self.login)]):
            raise UserError(_('The User ID "%s" is already taken.') % self.login)
        group_xmlid = ('real_estate_project_management.group_real_estate_agent' if self.role == 'agent'
                       else 'real_estate_project_management.group_real_estate_customer_portal')
        if self.role == 'agent' and not self.partner_id.is_agent:
            self.partner_id.sudo().is_agent = True
        user = Users.with_context(no_reset_password=True).create({
            'name': self.partner_id.name,
            'login': self.login,
            'password': self.password,
            'partner_id': self.partner_id.id,
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id, self.env.ref(group_xmlid).id])],
            'notification_type': 'inbox',
        })
        self.partner_id.message_post(body=_(
            'Login created: User ID "%(login)s" (%(role)s). Share the password securely with the user.',
            login=user.login, role=dict(self._fields['role'].selection)[self.role]))
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
            'title': _('Login created'),
            'message': _('User ID: %(login)s   Password: %(pwd)s',
                         login=user.login, pwd=self.password),
            'type': 'success', 'sticky': True,
            'next': {'type': 'ir.actions.act_window_close'},
        }}
