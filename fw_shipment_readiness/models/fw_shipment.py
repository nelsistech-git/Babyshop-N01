# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models


class FwShipment(models.Model):
    _inherit = 'fw.shipment'

    aql_inspection_ids = fields.One2many('fw.aql.inspection', 'shipment_id',
                                          string='AQL Inspections')
    carton_ids = fields.One2many('fw.carton', 'shipment_id', string='Packing Cartons')
    export_tracking_ids = fields.One2many('fw.export.tracking', 'shipment_id',
                                           string='Export Tracking Records')

    qc_ready = fields.Boolean(string='QC Ready', compute='_compute_readiness', store=True)
    cartons_ready = fields.Boolean(string='Cartons Ready', compute='_compute_readiness',
                                    store=True)
    export_docs_ready = fields.Boolean(string='Export Docs Ready',
                                        compute='_compute_readiness', store=True)
    lc_ready = fields.Boolean(string='L/C Ready', compute='_compute_readiness', store=True)
    overall_ready = fields.Boolean(string='Ready to Ship', compute='_compute_readiness',
                                    store=True)
    readiness_summary = fields.Text(string='Outstanding Items', compute='_compute_readiness',
                                     store=True)

    @api.depends('aql_inspection_ids.state', 'aql_inspection_ids.result',
                 'carton_ids.state', 'export_tracking_ids.state', 'lc_id',
                 'lc_id.all_documents_submitted')
    def _compute_readiness(self):
        for rec in self:
            outstanding = []

            completed_inspections = rec.aql_inspection_ids.filtered(
                lambda a: a.state == 'completed')
            failed_inspections = completed_inspections.filtered(lambda a: a.result == 'fail')
            passed_inspections = completed_inspections.filtered(lambda a: a.result == 'pass')
            rec.qc_ready = bool(passed_inspections) and not failed_inspections
            if not rec.qc_ready:
                if failed_inspections:
                    outstanding.append("QC: %d failed AQL inspection(s) need resolution."
                                        % len(failed_inspections))
                else:
                    outstanding.append("QC: no completed, passed AQL inspection linked yet.")

            rec.cartons_ready = bool(rec.carton_ids) and all(
                c.state in ('packed', 'shipped') for c in rec.carton_ids)
            if not rec.cartons_ready:
                outstanding.append("Cartons: no packing cartons linked, or some are not "
                                    "yet packed.")

            rec.export_docs_ready = bool(rec.export_tracking_ids) and any(
                t.state != 'draft' for t in rec.export_tracking_ids)
            if not rec.export_docs_ready:
                outstanding.append("Export Docs: no export tracking record started yet.")

            rec.lc_ready = (not rec.lc_id) or rec.lc_id.all_documents_submitted
            if not rec.lc_ready:
                outstanding.append("L/C: required documents not all submitted yet.")

            rec.overall_ready = (rec.qc_ready and rec.cartons_ready
                                  and rec.export_docs_ready and rec.lc_ready)
            rec.readiness_summary = '\n'.join(outstanding) if outstanding else \
                'All readiness checks passed.'
