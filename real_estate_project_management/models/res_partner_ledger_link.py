# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartnerLedgerLink(models.Model):
    """Phase 6: Customer Ledger view (spec section 40) - all computed
    from Sale Agreements / Installments / Collections already tied to
    this partner, no separate ledger table."""
    _inherit = 'res.partner'

    installment_ids = fields.One2many('real.estate.installment', 'customer_id', string='Installments')
    collection_ids = fields.One2many('real.estate.collection', 'customer_id', string='Collections')
    collection_count = fields.Integer(compute='_compute_ledger')

    ledger_total_agreement_value = fields.Monetary(string='Total Agreement Value', compute='_compute_ledger')
    ledger_total_paid = fields.Monetary(string='Total Paid', compute='_compute_ledger')
    ledger_total_due = fields.Monetary(string='Total Due', compute='_compute_ledger')
    ledger_overdue_amount = fields.Monetary(string='Overdue', compute='_compute_ledger')
    ledger_next_due_date = fields.Date(string='Next Due Date', compute='_compute_ledger')
    currency_id = fields.Many2one('res.currency', compute='_compute_ledger')

    @api.depends('sale_agreement_ids.net_price', 'sale_agreement_ids.state',
                 'installment_ids.due_amount', 'installment_ids.status', 'installment_ids.due_date',
                 'collection_ids.amount', 'collection_ids.state')
    def _compute_ledger(self):
        for rec in self:
            agreements = rec.sale_agreement_ids.filtered(lambda a: a.state in ('active', 'completed'))
            rec.ledger_total_agreement_value = sum(agreements.mapped('net_price'))
            rec.ledger_total_paid = sum(rec.collection_ids.filtered(
                lambda c: c.state == 'confirmed').mapped('amount'))
            rec.ledger_total_due = sum(rec.installment_ids.mapped('due_amount'))
            overdue = rec.installment_ids.filtered(lambda i: i.status == 'overdue')
            rec.ledger_overdue_amount = sum(overdue.mapped('due_amount'))
            upcoming = rec.installment_ids.filtered(
                lambda i: i.status in ('upcoming', 'due_today') and i.due_date)
            rec.ledger_next_due_date = min(upcoming.mapped('due_date')) if upcoming else False
            rec.collection_count = len(rec.collection_ids)
            rec.currency_id = rec.env.company.currency_id

    def action_view_installments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Installments',
            'res_model': 'real.estate.installment',
            'view_mode': 'tree,form',
            'domain': [('customer_id', '=', self.id)],
        }

    def action_view_collections(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'res_model': 'real.estate.collection',
            'view_mode': 'tree,form',
            'domain': [('customer_id', '=', self.id)],
            'context': {'default_customer_id': self.id},
        }
