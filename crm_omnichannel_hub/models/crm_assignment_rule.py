# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CrmAssignmentRule(models.Model):
    _name = 'crm.assignment.rule'
    _description = 'Agent Assignment Rule'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10, help='Rules are evaluated in order; the first match wins.')
    active = fields.Boolean(default=True)
    rule_type = fields.Selection([
        ('keyword', 'Keyword Match'),
        ('vip', 'VIP Customer'),
        ('working_hours', 'Working Hours Window'),
        ('department', 'Channel / Team Routing'),
        ('default', 'Default (Fallback)'),
    ], required=True, default='department')

    channel_ids = fields.Many2many('crm.channel', string='Channels',
                                    help='Leave empty to apply to all channels.')

    # --- Keyword ---------------------------------------------------------
    keywords = fields.Char(string='Keywords', help='Comma-separated. Matched case-insensitively '
                                                     'against the first inbound message text.')

    # --- VIP ---------------------------------------------------------
    vip_tag_id = fields.Many2one('res.partner.category', string='VIP Contact Tag',
                                  help='Customers whose Contact record has this tag are considered VIP.')

    # --- Working hours ---------------------------------------------------------
    weekdays = fields.Char(string='Active Weekdays',
                            help="Comma-separated weekday numbers, Monday=0 .. Sunday=6, e.g. '0,1,2,3,4'. "
                                 "Leave empty for every day.")
    start_hour = fields.Float(string='Start Hour', default=9.0, help='In the company timezone, 24h, e.g. 9.5 = 9:30.')
    end_hour = fields.Float(string='End Hour', default=18.0)

    # --- Target ---------------------------------------------------------
    team_id = fields.Many2one('crm.team', string='Sales Team')
    target_agent_ids = fields.Many2many('res.users', string='Assign From',
                                         help='Pool of agents to round-robin within. Leave empty to use '
                                              'every member of the Omni-Channel Agent group.')

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    # =====================================================================
    # MATCHING
    # =====================================================================
    def _matches(self, channel, partner=None, message_body=None):
        self.ensure_one()
        if self.channel_ids and channel not in self.channel_ids:
            return False

        if self.rule_type == 'keyword':
            if not self.keywords or not message_body:
                return False
            body_lower = message_body.lower()
            terms = [t.strip().lower() for t in self.keywords.split(',') if t.strip()]
            return any(term in body_lower for term in terms)

        if self.rule_type == 'vip':
            if not self.vip_tag_id or not partner:
                return False
            return self.vip_tag_id in partner.category_id

        if self.rule_type == 'working_hours':
            now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
            weekday_ok = True
            if self.weekdays:
                allowed = {d.strip() for d in self.weekdays.split(',') if d.strip()}
                weekday_ok = str(now.weekday()) in allowed
            hour_now = now.hour + now.minute / 60.0
            hours_ok = self.start_hour <= hour_now <= self.end_hour
            return weekday_ok and hours_ok

        if self.rule_type == 'department':
            return True  # channel match (checked above) is the whole condition

        if self.rule_type == 'default':
            return True

        return False

    @api.model
    def resolve_agent(self, channel, partner=None, message_body=None):
        """Evaluate active rules in order and return (agent, team) for the
        first match, or (empty recordset, empty recordset) if nothing
        matched (caller should fall back to plain round-robin)."""
        rules = self.search([], order='sequence, id')
        for rule in rules:
            if rule._matches(channel, partner=partner, message_body=message_body):
                pool = rule.target_agent_ids
                if not pool:
                    group = self.env.ref('crm_omnichannel_hub.group_omni_agent', raise_if_not_found=False)
                    pool = group.sudo().users if group else self.env['res.users']
                pool = pool.filtered(lambda u: u.active).sorted('id')
                if not pool:
                    continue
                agent = self._round_robin_in_pool(pool, 'crm_omnichannel_hub.rule_agent_%s' % rule.id)
                return agent, rule.team_id
        return self.env['res.users'], self.env['crm.team']

    def _round_robin_in_pool(self, pool, config_key):
        """Rotate through `pool` (already sorted by id), independent of the
        generic group-wide round-robin, so each rule's own agent pool
        gets fair rotation regardless of pool size."""
        param = self.env['ir.config_parameter'].sudo()
        last_agent_id = int(param.get_param(config_key, default='0') or 0)
        pool_ids = pool.ids
        if last_agent_id in pool_ids:
            next_index = (pool_ids.index(last_agent_id) + 1) % len(pool_ids)
        else:
            next_index = 0
        next_agent = self.env['res.users'].browse(pool_ids[next_index])
        param.set_param(config_key, str(next_agent.id))
        return next_agent
