# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ExpressPosDayClosing(models.Model):
    _name = 'express.pos.day.closing'
    _description = 'Express POS Opening/Closing Balance Report'
    _order = 'date desc, id desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    branch_id = fields.Many2one('express.pos.branch', string='Branch/Showroom')
    journal_id = fields.Many2one('account.journal', required=True, domain=[('type', 'in', ['cash', 'bank'])])
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')

    opening_balance = fields.Monetary(required=True)
    system_inflow = fields.Monetary(compute='_compute_system_amounts', help='Sum of inbound payments recorded for the day on this journal.')
    system_outflow = fields.Monetary(compute='_compute_system_amounts', help='Sum of outbound payments/refunds recorded for the day on this journal.')
    system_closing_balance = fields.Monetary(compute='_compute_system_amounts', help='Opening balance + inflow - outflow, as recorded by the system.')
    counted_closing_balance = fields.Monetary(help='Actual cash/bank balance counted at close.')
    variance = fields.Monetary(compute='_compute_variance', help='Counted balance minus system balance. Non-zero values should be explained in the note.')

    responsible_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    state = fields.Selection([('draft', 'Draft'), ('closed', 'Closed')], default='draft', copy=False)
    note = fields.Text()

    @api.depends('date', 'journal_id', 'branch_id')
    def _compute_display_name(self):
        for rec in self:
            branch = rec.branch_id.name or 'All Branches'
            rec.display_name = f"{rec.date} - {rec.journal_id.name or ''} - {branch}"

    @api.depends('date', 'journal_id')
    def _compute_system_amounts(self):
        Payment = self.env['account.payment']
        for rec in self:
            if not rec.journal_id or not rec.date:
                rec.system_inflow = rec.system_outflow = rec.system_closing_balance = 0.0
                continue
            domain = [
                ('journal_id', '=', rec.journal_id.id),
                ('date', '=', rec.date),
                ('state', '=', 'posted'),
            ]
            payments = Payment.search(domain)
            inflow = sum(p.amount for p in payments if p.payment_type == 'inbound')
            outflow = sum(p.amount for p in payments if p.payment_type == 'outbound')
            rec.system_inflow = inflow
            rec.system_outflow = outflow
            rec.system_closing_balance = rec.opening_balance + inflow - outflow

    @api.depends('counted_closing_balance', 'system_closing_balance')
    def _compute_variance(self):
        for rec in self:
            rec.variance = rec.counted_closing_balance - rec.system_closing_balance

    def action_close_day(self):
        for rec in self:
            if rec.state == 'closed':
                continue
            rec.state = 'closed'
            if rec.branch_id:
                orders = self.env['sale.order'].sudo().search([
                    ('is_express_pos', '=', True),
                    ('express_pos_branch_id', '=', rec.branch_id.id),
                    ('date_order', '>=', f'{rec.date} 00:00:00'),
                    ('date_order', '<=', f'{rec.date} 23:59:59'),
                ])
                orders.write({'is_daily_closed': True})

    def action_reopen_day(self):
        """Reopening a closed day is itself a sensitive action - route it through approval."""
        for rec in self:
            if rec.state != 'closed':
                continue
            rec.env['express.approval.request'].sudo().create({
                'res_model': self._name,
                'res_id': rec.id,
                'action_type': 'backdated',
                'reason': _('Request to reopen closed day %s (%s)') % (rec.date, rec.journal_id.name),
                'old_values': '{"state": "closed"}',
                'new_values': '{"state": "draft"}',
                'requires_md_direct': True,
            })
            raise UserError(_('Reopening a closed day requires MD approval. An approval request has been submitted.'))
