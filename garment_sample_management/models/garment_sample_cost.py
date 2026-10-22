# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentSampleCost(models.Model):
    """Sample Cost Management + Cost Approval (SRS sections 20-21) —
    garment.sample.cost."""
    _name = 'garment.sample.cost'
    _description = 'Garment Sample Cost'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    sample_id = fields.Many2one('garment.sample', string='Sample', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    fabric_cost = fields.Monetary(string='Fabric Cost', currency_field='currency_id')
    trim_cost = fields.Monetary(string='Trim Cost', currency_field='currency_id')
    label_cost = fields.Monetary(string='Label Cost', currency_field='currency_id')
    packaging_material_cost = fields.Monetary(string='Packaging Material Cost', currency_field='currency_id')
    material_cost = fields.Monetary(string='Material Cost', compute='_compute_totals', store=True,
                                     currency_field='currency_id')

    cutting_labor_cost = fields.Monetary(string='Cutting Labor', currency_field='currency_id')
    sewing_labor_cost = fields.Monetary(string='Sewing Labor', currency_field='currency_id')
    finishing_labor_cost = fields.Monetary(string='Finishing Labor', currency_field='currency_id')
    qc_labor_cost = fields.Monetary(string='QC Labor', currency_field='currency_id')
    labor_cost = fields.Monetary(string='Labor Cost', compute='_compute_totals', store=True,
                                  currency_field='currency_id')

    printing_cost = fields.Monetary(string='Printing Cost', currency_field='currency_id')
    embroidery_cost = fields.Monetary(string='Embroidery Cost', currency_field='currency_id')
    washing_cost = fields.Monetary(string='Washing Cost', currency_field='currency_id')
    special_treatment_cost = fields.Monetary(string='Special Treatment Cost', currency_field='currency_id')
    processing_cost = fields.Monetary(string='Processing Cost', compute='_compute_totals', store=True,
                                       currency_field='currency_id')

    machine_cost = fields.Monetary(string='Machine Cost', currency_field='currency_id')
    courier_cost = fields.Monetary(string='Courier Cost', currency_field='currency_id')
    miscellaneous_cost = fields.Monetary(string='Miscellaneous Cost', currency_field='currency_id')

    total_cost = fields.Monetary(string='Total Sample Cost', compute='_compute_totals', store=True,
                                  currency_field='currency_id')

    state = fields.Selection([
        ('draft', 'Sample Cost Created'), ('merchandiser_review', 'Merchandiser Review'),
        ('costing_approval', 'Costing Team Approval'), ('management_approval', 'Management Approval'),
        ('final', 'Final Cost'),
    ], string='Status', default='draft', tracking=True)

    @api.depends('fabric_cost', 'trim_cost', 'label_cost', 'packaging_material_cost',
                 'cutting_labor_cost', 'sewing_labor_cost', 'finishing_labor_cost', 'qc_labor_cost',
                 'printing_cost', 'embroidery_cost', 'washing_cost', 'special_treatment_cost',
                 'machine_cost', 'courier_cost', 'miscellaneous_cost')
    def _compute_totals(self):
        for rec in self:
            rec.material_cost = rec.fabric_cost + rec.trim_cost + rec.label_cost + rec.packaging_material_cost
            rec.labor_cost = (rec.cutting_labor_cost + rec.sewing_labor_cost
                               + rec.finishing_labor_cost + rec.qc_labor_cost)
            rec.processing_cost = (rec.printing_cost + rec.embroidery_cost
                                    + rec.washing_cost + rec.special_treatment_cost)
            rec.total_cost = (rec.material_cost + rec.labor_cost + rec.processing_cost
                               + rec.machine_cost + rec.courier_cost + rec.miscellaneous_cost)

    def action_next_stage(self):
        flow = ['draft', 'merchandiser_review', 'costing_approval', 'management_approval', 'final']
        for rec in self:
            idx = flow.index(rec.state)
            if idx < len(flow) - 1:
                rec.state = flow[idx + 1]
