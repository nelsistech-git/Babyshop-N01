# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Shipment-linked export workflow + Shipment Readiness Dashboard (SRS
section 43) added onto garment_logistics' garment.shipment: EXP Form,
Customs Documents and Export Incentive claims raised against the
shipment, and a rule-based commercial-document readiness check against
the buyer's document requirement checklist (garment.commercial.doc.
requirement). Production/Quality readiness stay the responsibility of
their own modules — this only covers the commercial-document leg."""
from odoo import api, fields, models, _


class GarmentShipmentExport(models.Model):
    _inherit = 'garment.shipment'

    export_documentation_ids = fields.One2many('garment.export.documentation', 'shipment_id',
                                                 string='Export Documents')
    exp_form_ids = fields.One2many('garment.exp.form', 'shipment_id', string='EXP Forms')
    customs_document_ids = fields.One2many('garment.customs.document', 'shipment_id', string='Customs Documents')
    export_incentive_ids = fields.One2many('garment.export.incentive', 'shipment_id', string='Export Incentives')

    commercial_readiness = fields.Selection([
        ('ready', 'Ready to Ship'), ('not_ready', 'Documents Missing'), ('no_checklist', 'No Checklist Defined'),
    ], string='Commercial Readiness', compute='_compute_commercial_readiness')
    commercial_readiness_note = fields.Text(string='Commercial Readiness Note', compute='_compute_commercial_readiness')

    @api.depends('buyer_id', 'export_documentation_ids.document_type', 'exp_form_ids', 'bl_ids')
    def _compute_commercial_readiness(self):
        DocRequirement = self.env['garment.commercial.doc.requirement']
        for rec in self:
            required = DocRequirement.search([('buyer_id', '=', rec.buyer_id.id), ('is_mandatory', '=', True)])
            if not required:
                rec.commercial_readiness = 'no_checklist'
                rec.commercial_readiness_note = _('No mandatory document checklist defined for this buyer.')
                continue

            present_types = set(rec.export_documentation_ids.mapped('document_type'))
            if rec.exp_form_ids:
                present_types.add('exp_form')
            if rec.bl_ids:
                present_types.add('bill_of_lading')

            missing = required.filtered(lambda r: r.document_type not in present_types)
            if missing:
                rec.commercial_readiness = 'not_ready'
                labels = dict(required._fields['document_type'].selection)
                rec.commercial_readiness_note = _('Missing mandatory document(s): %s') % ', '.join(
                    labels.get(m.document_type, m.document_type) for m in missing)
            else:
                rec.commercial_readiness = 'ready'
                rec.commercial_readiness_note = _('All mandatory commercial documents for this buyer are present.')
