# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentQualityInspection(models.Model):
    """Unified Quality Inspection document covering every inspection stage
    of the garment quality lifecycle: Incoming Material, Fabric, Accessories,
    Cutting, Sewing Inline, End Line, Washing, Finishing and Final.
    Consolidates base QMS SRS sec. 9-32, Garment QMS SRS sec. 8-25 and
    Advanced QMS SRS sec. 9-30 (all three source SRS documents modeled the
    same underlying flow with different levels of detail)."""
    _name = 'garment.quality.inspection'
    _description = 'Garment Quality Inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'inspection_date desc, id desc'

    inspection_no = fields.Char(string='Inspection No.', copy=False, readonly=True, default=lambda s: _('New'))
    inspection_type = fields.Selection([
        ('incoming_material', 'Incoming Material Inspection'),
        ('fabric', 'Fabric Inspection'),
        ('accessory', 'Accessories Inspection'),
        ('cutting', 'Cutting QC'),
        ('sewing_inline', 'Sewing Inline QC'),
        ('endline', 'End Line QC'),
        ('washing', 'Washing QC'),
        ('finishing', 'Finishing QC'),
        ('final', 'Final Inspection'),
    ], string='Inspection Type', required=True, tracking=True, default='sewing_inline')
    inspection_source = fields.Selection([
        ('purchase_receipt', 'Purchase Receipt / GRN'),
        ('production_order', 'Production Order'),
        ('work_center', 'Work Center'),
        ('shipment', 'Shipment'),
    ], string='Inspection Source', default='production_order')

    # ------------------------------------------------------------------
    # Source linkage — incoming material inspection ties into GRN/material
    # ------------------------------------------------------------------
    grn_id = fields.Many2one('garment.grn', string='GRN')
    grn_line_id = fields.Many2one('garment.grn.line', string='GRN Line')
    material_id = fields.Many2one('garment.material', string='Material')
    supplier_id = fields.Many2one('garment.supplier', string='Supplier')
    roll_number = fields.Char(string='Fabric Roll Number')
    fabric_type = fields.Char(string='Fabric Type')
    total_meter = fields.Float(string='Total Meter / Yardage')

    style_id = fields.Many2one('garment.style', string='Style', tracking=True)
    buyer_id = fields.Many2one('garment.buyer', string='Buyer')

    # ------------------------------------------------------------------
    # Production / shop-floor linkage.
    # NOTE: garment_production (sibling module, built concurrently) does not
    # yet expose a stable "Production Order" model at the time this module
    # was authored. Deliberately kept as free-text soft references instead
    # of a hard Many2one so this module never breaks if the sibling's exact
    # technical name differs. See IMPLEMENTATION_NOTES.md.
    # ------------------------------------------------------------------
    production_order_id = fields.Char(
        string='Production Order Ref.',
        help='Free-text reference to the shop-floor production order (soft link — see '
             'IMPLEMENTATION_NOTES.md for why this is not a hard Many2one).')
    cutting_batch_no = fields.Char(string='Cutting Batch / Bundle No.')
    sewing_line = fields.Char(string='Sewing Line')
    work_center = fields.Char(string='Work Center')
    operation = fields.Char(string='Operation')

    checkpoint_id = fields.Many2one('garment.quality.checkpoint', string='Checkpoint / Checklist Template')
    standard_id = fields.Many2one('garment.quality.standard', string='Quality Standard')

    inspector_id = fields.Many2one('res.users', string='Inspector', required=True,
                                    default=lambda s: s.env.user, tracking=True)
    inspection_date = fields.Datetime(string='Inspection Date', default=fields.Datetime.now, tracking=True)

    inspection_method = fields.Selection([
        ('4_point', '4-Point System'),
        ('10_point', '10-Point System'),
        ('percentage', 'Percentage / AQL'),
        ('visual', 'Visual Check'),
    ], string='Inspection Method', default='visual')
    four_point_defect_points = fields.Integer(string='Total Defect Points (4-Point System)')

    quantity = fields.Float(string='Inspected Quantity', required=True, default=0.0)
    defect_qty = fields.Float(string='Defect Quantity', compute='_compute_quantities', store=True)
    passed_qty = fields.Float(string='Passed Quantity', compute='_compute_quantities', store=True)
    quality_score = fields.Float(string='Quality Score (%)', compute='_compute_quantities', store=True,
                                  help='Accepted Quantity ÷ Inspected Quantity × 100')

    checklist_line_ids = fields.One2many('garment.quality.inspection.checklist.line', 'inspection_id',
                                          string='Checklist Items')
    measurement_line_ids = fields.One2many('garment.quality.measurement.line', 'inspection_id',
                                            string='Measurement Checks')
    defect_ids = fields.One2many('garment.quality.defect', 'inspection_id', string='Defects Found')
    defect_count = fields.Integer(compute='_compute_defect_count')

    photo = fields.Binary(string='Inspection Photo', attachment=True)
    remarks = fields.Text(string='Remarks')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'Inspection Started'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('hold', 'Hold'),
        ('released', 'Released'),
    ], string='Status', default='draft', tracking=True)
    disposition = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('hold', 'Hold'),
        ('conditional', 'Conditional Release'),
    ], string='Disposition', tracking=True)

    capa_id = fields.Many2one('garment.quality.capa', string='CAPA', copy=False)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    @api.depends('quantity', 'defect_ids.quantity')
    def _compute_quantities(self):
        for rec in self:
            defect_qty = sum(rec.defect_ids.mapped('quantity'))
            rec.defect_qty = defect_qty
            rec.passed_qty = max(rec.quantity - defect_qty, 0.0)
            rec.quality_score = (rec.passed_qty / rec.quantity * 100.0) if rec.quantity else 0.0

    @api.depends('defect_ids')
    def _compute_defect_count(self):
        for rec in self:
            rec.defect_count = len(rec.defect_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('inspection_no', _('New')) == _('New'):
                vals['inspection_no'] = self.env['ir.sequence'].next_by_code('garment.quality.inspection') or _('New')
            checkpoint_id = vals.get('checkpoint_id')
            if checkpoint_id and not vals.get('checklist_line_ids'):
                checkpoint = self.env['garment.quality.checkpoint'].browse(checkpoint_id)
                vals['checklist_line_ids'] = [(0, 0, {
                    'checkpoint_line_id': line.id,
                    'check_item': line.check_item,
                }) for line in checkpoint.line_ids]
        return super().create(vals_list)

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_approve(self):
        for rec in self:
            if rec.state not in ('in_progress', 'hold'):
                raise UserError(_('Only an inspection that is in progress or on hold can be approved.'))
        self.write({'state': 'approved', 'disposition': 'pass'})

    def action_reject(self):
        self.write({'state': 'rejected', 'disposition': 'fail'})

    def action_hold(self):
        self.write({'state': 'hold', 'disposition': 'hold'})

    def action_release(self):
        for rec in self:
            if rec.state != 'approved':
                raise UserError(_('Only an approved inspection can be released.'))
        self.write({'state': 'released'})

    def action_create_capa(self):
        self.ensure_one()
        capa = self.env['garment.quality.capa'].create({
            'source': 'inspection',
            'inspection_id': self.id,
            'style_id': self.style_id.id,
            'supplier_id': self.supplier_id.id,
            'problem_description': self.remarks or _('Quality issue raised from inspection %s') % self.inspection_no,
        })
        self.capa_id = capa.id
        return {
            'name': _('CAPA'), 'type': 'ir.actions.act_window', 'res_model': 'garment.quality.capa',
            'view_mode': 'form', 'res_id': capa.id,
        }

    def action_view_defects(self):
        self.ensure_one()
        return {
            'name': _('Defects'), 'type': 'ir.actions.act_window', 'res_model': 'garment.quality.defect',
            'view_mode': 'tree,form', 'domain': [('inspection_id', '=', self.id)],
            'context': {'default_inspection_id': self.id},
        }


class GarmentQualityInspectionChecklistLine(models.Model):
    _name = 'garment.quality.inspection.checklist.line'
    _description = 'Garment Quality Inspection Checklist Line'
    _order = 'sequence, id'

    inspection_id = fields.Many2one('garment.quality.inspection', string='Inspection',
                                     required=True, ondelete='cascade')
    checkpoint_line_id = fields.Many2one('garment.quality.checkpoint.line', string='Checkpoint Item')
    sequence = fields.Integer(default=10)
    check_item = fields.Char(string='Check Item', required=True)
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('na', 'N/A'),
    ], string='Result', default='pass')
    remark = fields.Char(string='Remark')


class GarmentQualityMeasurementLine(models.Model):
    """Measurement Quality Management — see Garment QMS SRS sec. 24 and
    Advanced QMS SRS sec. 28."""
    _name = 'garment.quality.measurement.line'
    _description = 'Garment Quality Measurement Check Line'
    _order = 'sequence, id'

    inspection_id = fields.Many2one('garment.quality.inspection', string='Inspection',
                                     required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    measurement_point = fields.Char(string='Measurement Point', required=True,
                                     help='e.g. Chest, Length, Sleeve, Waist, Collar, Bottom, Hip')
    size = fields.Char(string='Size')
    spec_value = fields.Float(string='Spec Value')
    tolerance = fields.Float(string='Tolerance (+/-)')
    actual_value = fields.Float(string='Actual Value')
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Result', compute='_compute_result', store=True)

    @api.depends('spec_value', 'tolerance', 'actual_value')
    def _compute_result(self):
        for rec in self:
            if rec.actual_value and rec.spec_value:
                rec.result = 'pass' if abs(rec.actual_value - rec.spec_value) <= (rec.tolerance or 0.0) else 'fail'
            else:
                rec.result = 'pass'
