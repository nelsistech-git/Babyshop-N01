# -*- coding: utf-8 -*-
"""Central configuration of the ERM behaviour (SRS 18, 41, 60, 67, 81)."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .gc_service_catalog import MARGIN_METHOD_SELECTION


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ---- Workflow security (SRS 67) -----------------------------------
    gc_segregation_of_duties = fields.Boolean(
        string='Segregation of Duties',
        config_parameter='gc_erm.segregation_of_duties', default=True,
        help='Prevent users from approving documents they created or '
             'submitted themselves.')
    gc_technical_review_required = fields.Boolean(
        string='Technical Manager Review',
        config_parameter='gc_erm.technical_review_required',
        help='Require a Technical Manager approval before a technical report '
             'reaches Sales.')
    gc_auto_create_work_order = fields.Boolean(
        string='Auto-create Work Order',
        config_parameter='gc_erm.auto_create_work_order',
        help='Create the work order automatically when an ERM sales order is '
             'confirmed.')

    # ---- Costing (SRS 18) ---------------------------------------------
    gc_default_margin_method = fields.Selection(
        MARGIN_METHOD_SELECTION, string='Default Margin Method',
        config_parameter='gc_erm.default_margin_method', default='cost_pct')
    gc_default_margin_value = fields.Float(
        string='Default Margin Value',
        config_parameter='gc_erm.default_margin_value', default=20.0)

    # ---- Commercial ----------------------------------------------------
    gc_proposal_validity_days = fields.Integer(
        string='Proposal Validity (days)',
        config_parameter='gc_erm.proposal_validity_days', default=30)

    # ---- SLA (SRS 81) --------------------------------------------------
    gc_sla_lead_days = fields.Float(
        string='Lead Approval SLA (days)',
        config_parameter='gc_erm.sla_lead_days', default=1.0)
    gc_sla_survey_days = fields.Float(
        string='Survey SLA (days)',
        config_parameter='gc_erm.sla_survey_days', default=2.0)
    gc_sla_technical_report_days = fields.Float(
        string='Technical Report SLA (days)',
        config_parameter='gc_erm.sla_technical_report_days', default=2.0)
    gc_sla_proposal_days = fields.Float(
        string='Proposal Approval SLA (days)',
        config_parameter='gc_erm.sla_proposal_days', default=1.0)
    gc_sla_implementation_days = fields.Float(
        string='Implementation SLA (days)',
        config_parameter='gc_erm.sla_implementation_days', default=5.0)
    gc_sla_procurement_days = fields.Float(
        string='Procurement SLA (days)',
        config_parameter='gc_erm.sla_procurement_days', default=3.0)
    gc_sla_installation_days = fields.Float(
        string='Installation SLA (days)',
        config_parameter='gc_erm.sla_installation_days', default=3.0)
    gc_sla_billing_days = fields.Float(
        string='Billing SLA (days)',
        config_parameter='gc_erm.sla_billing_days', default=1.0)

    @api.constrains('gc_default_margin_value')
    def _check_margin_value(self):
        for settings in self:
            if settings.gc_default_margin_value < 0:
                raise ValidationError(_(
                    'The default margin value cannot be negative.'))
            if settings.gc_default_margin_method == 'price_pct' and \
                    settings.gc_default_margin_value >= 100:
                raise ValidationError(_(
                    'A margin on selling price must be below 100%.'))

    @api.constrains('gc_proposal_validity_days')
    def _check_validity_days(self):
        for settings in self:
            if settings.gc_proposal_validity_days < 0:
                raise ValidationError(_(
                    'The proposal validity cannot be negative.'))

    def action_gc_open_approval_matrix(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approval Matrix'),
            'res_model': 'gc.erm.approval.matrix',
            'view_mode': 'tree,form',
        }

    def action_gc_open_service_catalog(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Service Catalog'),
            'res_model': 'gc.erm.service.catalog',
            'view_mode': 'tree,form',
        }
