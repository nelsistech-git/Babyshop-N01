# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartnerAgentLink(models.Model):
    """Agent / referral network on res.partner (no duplicate tables).

    * ``is_agent``       - this partner works as a sales agent.
    * ``referred_by_id`` - who brought this partner in. This single link is
      what builds the 2-level commission chain:

        Agent A  --brings-->  Customer B  --sells to-->  Customer C

      Sale to C  ->  Level 1 commission = B (the seller / referrer)
                     Level 2 commission = A (the one who referred B)
    """
    _inherit = 'res.partner'

    is_agent = fields.Boolean(string='Is Agent', tracking=False)
    agent_code = fields.Char(string='Agent Code', copy=False)
    referred_by_id = fields.Many2one(
        'res.partner', string='Referred / Brought By', index=True, ondelete='set null',
        help='The agent (or customer) who introduced this partner. They become the '
             'Level 2 commission beneficiary when this partner sells to somebody else.')
    referral_ids = fields.One2many('res.partner', 'referred_by_id', string='Referred Customers')
    referral_count = fields.Integer(compute='_compute_agent_counts')

    agent_sale_ids = fields.One2many('real.estate.sale.agreement', 'agent_id',
                                      string='Sales Made (as Agent / Referrer)')
    agent_sale_count = fields.Integer(compute='_compute_agent_counts')
    commission_ids = fields.One2many('real.estate.commission', 'beneficiary_id',
                                      string='Commissions')
    commission_count = fields.Integer(compute='_compute_agent_counts')
    commission_total = fields.Monetary(string='Total Commission', compute='_compute_agent_counts')
    commission_paid = fields.Monetary(string='Commission Paid', compute='_compute_agent_counts')
    commission_pending = fields.Monetary(string='Commission Pending', compute='_compute_agent_counts')

    @api.depends('referral_ids', 'agent_sale_ids', 'commission_ids.amount', 'commission_ids.state')
    def _compute_agent_counts(self):
        for rec in self:
            rec.referral_count = len(rec.referral_ids)
            rec.agent_sale_count = len(rec.agent_sale_ids)
            valid = rec.commission_ids.filtered(lambda c: c.state != 'cancelled')
            rec.commission_count = len(valid)
            rec.commission_total = sum(valid.mapped('amount'))
            rec.commission_paid = sum(valid.filtered(lambda c: c.state == 'paid').mapped('amount'))
            rec.commission_pending = rec.commission_total - rec.commission_paid

    @api.constrains('referred_by_id')
    def _check_referral_cycle(self):
        if self._has_cycle('referred_by_id'):
            raise ValidationError(_('A partner cannot be (directly or indirectly) referred by themselves.'))

    # ---- navigation -------------------------------------------------
    def action_view_referrals(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Referred Customers'),
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [('referred_by_id', '=', self.id)],
            'context': {'default_referred_by_id': self.id},
        }

    def action_view_commissions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Commissions'),
            'res_model': 'real.estate.commission',
            'view_mode': 'tree,form',
            'domain': [('beneficiary_id', '=', self.id)],
        }

    def action_view_agent_sales(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Made'),
            'res_model': 'real.estate.sale.agreement',
            'view_mode': 'tree,form',
            'domain': [('agent_id', '=', self.id)],
        }

    # ---- staff helpers: preview a dashboard / create a login ---------
    def action_open_customer_dashboard(self):
        self.ensure_one()
        return self.env['real.estate.portal.dashboard'].action_open_dashboard('customer', partner=self)

    def action_open_agent_dashboard(self):
        self.ensure_one()
        return self.env['real.estate.portal.dashboard'].action_open_dashboard('agent', partner=self)

    def action_create_portal_login(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Login (User ID & Password)'),
            'res_model': 'real.estate.create.user.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_role': 'agent' if self.is_agent else 'customer',
                'default_login': self.email or '',
            },
        }
