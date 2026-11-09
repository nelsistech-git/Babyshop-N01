# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RealEstateSaleAgreementCommissionLink(models.Model):
    """Adds the seller (agent / referring customer) to the Sale Agreement and
    generates the 2-layer commission when the agreement is activated."""
    _inherit = 'real.estate.sale.agreement'

    agent_id = fields.Many2one(
        'res.partner', string='Sold By (Agent / Referrer)', tracking=True, index=True,
        ondelete='restrict',
        help='The agent - or an existing customer - who brought this buyer. '
             'They receive the Level 1 commission.')
    upline_partner_id = fields.Many2one(
        related='agent_id.referred_by_id', string='Upline (Level 2)', store=True, readonly=True,
        help='Whoever referred the seller. Receives the Level 2 commission.')
    commission_ids = fields.One2many('real.estate.commission', 'sale_agreement_id', string='Commissions')
    commission_count = fields.Integer(compute='_compute_commission_totals')
    total_commission = fields.Monetary(string='Total Commission', compute='_compute_commission_totals')

    @api.depends('commission_ids.amount', 'commission_ids.state')
    def _compute_commission_totals(self):
        for rec in self:
            valid = rec.commission_ids.filtered(lambda c: c.state != 'cancelled')
            rec.commission_count = len(valid)
            rec.total_commission = sum(valid.mapped('amount'))

    @api.constrains('agent_id', 'customer_id')
    def _check_agent_not_buyer(self):
        for rec in self:
            if rec.agent_id and rec.agent_id == rec.customer_id:
                raise ValidationError(_('The seller / agent cannot be the buyer of the same agreement.'))

    @api.onchange('booking_id')
    def _onchange_booking_id_agent(self):
        if self.booking_id and self.booking_id.agent_id and not self.agent_id:
            self.agent_id = self.booking_id.agent_id

    # ---- lifecycle hooks -------------------------------------------
    def action_activate(self):
        res = super().action_activate()
        self._link_buyer_to_agent()
        self._generate_commissions()
        return res

    def action_cancel(self):
        res = super().action_cancel()
        unpaid = self.mapped('commission_ids').filtered(lambda c: c.state in ('draft', 'approved'))
        unpaid.write({'state': 'cancelled'})
        return res

    def action_generate_commissions(self):
        """Manual (re)generation, e.g. after adding an agent to an agreement
        that is already active or after creating the rules."""
        for rec in self:
            if rec.state not in ('active', 'completed'):
                raise ValidationError(_('Commissions can only be generated for active or completed agreements.'))
            if not rec.agent_id:
                raise ValidationError(_('Set "Sold By (Agent / Referrer)" first.'))
        self._link_buyer_to_agent()
        self._generate_commissions()

    def _link_buyer_to_agent(self):
        """The buyer becomes the agent's customer (if not already referred by
        somebody) - this is what later makes the agent the Level 2 upline when
        that buyer sells to a new person."""
        for rec in self:
            buyer, agent = rec.customer_id, rec.agent_id
            if not agent or buyer.referred_by_id or buyer == agent:
                continue
            node, seen, cycle = agent, set(), False
            while node and node.id not in seen:
                if node == buyer:
                    cycle = True
                    break
                seen.add(node.id)
                node = node.referred_by_id
            if not cycle:
                buyer.sudo().write({'referred_by_id': agent.id})

    def _generate_commissions(self):
        Commission = self.env['real.estate.commission'].sudo()
        Rule = self.env['real.estate.commission.rule']
        for rec in self:
            if not rec.agent_id:
                continue
            existing = rec.commission_ids.filtered(lambda c: c.state != 'cancelled')
            targets = [('1', rec.agent_id)]
            upline = rec.agent_id.referred_by_id
            if upline and upline not in (rec.customer_id, rec.agent_id):
                targets.append(('2', upline))
            for level, partner in targets:
                if existing.filtered(lambda c, lv=level: c.level == lv):
                    continue
                rule = Rule._get_rule(level, rec.project_id, rec.company_id)
                if not rule:
                    rec.message_post(body=_(
                        'No active Level %(lvl)s commission rule found - no commission generated for %(who)s.',
                        lvl=level, who=partner.display_name))
                    continue
                Commission.create({
                    'sale_agreement_id': rec.id,
                    'level': level,
                    'beneficiary_id': partner.id,
                    'calc_type': rule.calc_type,
                    'rate_value': rule.value,
                })

    def action_view_commissions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Commissions'),
            'res_model': 'real.estate.commission',
            'view_mode': 'tree,form',
            'domain': [('sale_agreement_id', '=', self.id)],
        }
