# -*- coding: utf-8 -*-
"""Sales order integration (SRS 25 / 26 / 27)."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    gc_proposal_id = fields.Many2one(
        'gc.erm.proposal', string='ERM Proposal', copy=False, index=True,
        ondelete='set null')
    gc_lead_id = fields.Many2one(
        'gc.erm.lead', string='ERM Lead', copy=False, index=True,
        ondelete='set null')
    gc_survey_id = fields.Many2one(
        'gc.erm.survey', string='ERM Survey', copy=False, ondelete='set null')
    gc_boq_id = fields.Many2one(
        'gc.erm.boq', string='ERM BOQ', copy=False, ondelete='set null')
    gc_work_order_ids = fields.One2many(
        'gc.erm.work.order', 'sale_order_id', string='Work Orders')
    gc_work_order_count = fields.Integer(compute='_compute_gc_work_order_count')
    gc_is_erm_order = fields.Boolean(
        string='From ERM', compute='_compute_gc_is_erm_order', store=True)

    @api.depends('gc_proposal_id', 'gc_lead_id')
    def _compute_gc_is_erm_order(self):
        for order in self:
            order.gc_is_erm_order = bool(order.gc_proposal_id or order.gc_lead_id)

    @api.depends('gc_work_order_ids')
    def _compute_gc_work_order_count(self):
        for order in self:
            order.gc_work_order_count = len(order.gc_work_order_ids)

    def action_confirm(self):
        """Mark the ERM proposal as accepted when the order is confirmed."""
        res = super().action_confirm()
        for order in self.filtered('gc_proposal_id'):
            proposal = order.gc_proposal_id
            if proposal.state in ('approved', 'sent'):
                proposal.with_context(gc_bypass_lock=True)._gc_transition(
                    'accepted',
                    comment=_('Customer accepted through sales order %s.',
                              order.name),
                    extra_vals={
                        'acceptance_method': 'quotation',
                        'acceptance_date': fields.Date.context_today(order),
                        'accepted_by': order.partner_id.display_name,
                    })
            auto = self.env['ir.config_parameter'].sudo().get_param(
                'gc_erm.auto_create_work_order', 'False')
            if auto in ('True', 'true', '1') and not order.gc_work_order_ids:
                order.action_gc_create_work_order()
        return res

    def action_gc_create_work_order(self):
        """SRS 27 -- create the ERM work order from a confirmed order."""
        self.ensure_one()
        if self.state != 'sale':
            raise UserError(_(
                'Customer acceptance is required before creating the work '
                'order. Confirm sales order %s first.', self.name))
        existing = self.gc_work_order_ids.filtered(
            lambda w: w.state != 'cancelled')
        if existing:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'gc.erm.work.order',
                'res_id': existing[0].id, 'view_mode': 'form',
            }
        survey = self.gc_survey_id
        services = survey.service_ids if survey else \
            self.env['gc.erm.service.catalog']
        vals = {
            'sale_order_id': self.id,
            'proposal_id': self.gc_proposal_id.id,
            'lead_id': self.gc_lead_id.id,
            'survey_id': survey.id,
            'boq_id': self.gc_boq_id.id,
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'service_ids': [(6, 0, services.ids)],
            'start_date': fields.Date.context_today(self),
        }
        if survey:
            vals.update({
                'contact_id': survey.contact_id.id,
                'street': survey.street,
                'city': survey.city,
                'district': survey.district,
                'area': survey.area,
                'service_location': survey.service_location,
                'gps_latitude': survey.gps_latitude,
                'gps_longitude': survey.gps_longitude,
                'technical_report_id': survey.technical_report_ids.filtered(
                    lambda r: r.state == 'submitted')[:1].id,
            })
        if services:
            vals.update({
                'billing_policy': services[0].billing_policy,
                'advance_percent': services[0].advance_percent,
                'installation_percent': services[0].installation_percent,
                'completion_percent': services[0].completion_percent,
            })
        # SRS 59 -- the work order is created by the *system* as a consequence
        # of a confirmed sales order, not manually by the salesperson.  It is
        # therefore created with elevated rights while the business guard above
        # (the order must be confirmed) stays in force, and ``create_uid`` still
        # records who triggered it so the audit trail remains accurate.
        work_order = self.env['gc.erm.work.order'].sudo().create(vals)
        work_order.action_confirm()
        work_order = work_order.sudo(False)
        self.message_post(body=_('Work order %s created.', work_order.name))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Work Order'),
            'res_model': 'gc.erm.work.order',
            'res_id': work_order.id, 'view_mode': 'form',
        }

    def action_gc_view_work_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Work Orders'),
            'res_model': 'gc.erm.work.order', 'view_mode': 'tree,form',
            'domain': [('sale_order_id', '=', self.id)],
        }

    def _prepare_invoice(self):
        """Propagate the ERM references onto the customer invoice."""
        vals = super()._prepare_invoice()
        work_order = self.gc_work_order_ids.filtered(
            lambda w: w.state != 'cancelled')[:1]
        vals.update({
            'gc_lead_id': self.gc_lead_id.id,
            'gc_proposal_id': self.gc_proposal_id.id,
            'gc_work_order_id': work_order.id if work_order else False,
        })
        return vals
