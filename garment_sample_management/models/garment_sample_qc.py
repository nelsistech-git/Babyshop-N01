# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models, _


class GarmentSampleQC(models.Model):
    """Sample Quality Check (SRS section 15) — garment.sample.qc."""
    _name = 'garment.sample.qc'
    _description = 'Garment Sample Quality Check'
    _inherit = ['mail.thread']
    _order = 'qc_date desc'

    sample_id = fields.Many2one('garment.sample', string='Sample', required=True, ondelete='cascade')
    qc_date = fields.Date(string='QC Date', default=fields.Date.context_today)
    qc_by_id = fields.Many2one('res.users', string='Checked By', default=lambda s: s.env.user)

    # Measurement checks
    measured_body_length = fields.Float(string='Body Length (measured)')
    measured_chest = fields.Float(string='Chest (measured)')
    measured_sleeve_length = fields.Float(string='Sleeve Length (measured)')
    measured_collar = fields.Float(string='Collar (measured)')
    measured_waist = fields.Float(string='Waist (measured)')
    measured_hip = fields.Float(string='Hip (measured)')

    # Workmanship checks
    chk_stitch_quality = fields.Boolean(string='Stitch Quality OK')
    chk_seam_quality = fields.Boolean(string='Seam Quality OK')
    chk_thread_trimming = fields.Boolean(string='Thread Trimming OK')
    chk_label_position = fields.Boolean(string='Label Position OK')
    chk_finishing_quality = fields.Boolean(string='Finishing Quality OK')

    # Appearance checks
    chk_color = fields.Boolean(string='Color OK')
    chk_shape = fields.Boolean(string='Shape OK')
    chk_design = fields.Boolean(string='Design OK')
    chk_print = fields.Boolean(string='Print OK')
    chk_embroidery = fields.Boolean(string='Embroidery OK')

    result = fields.Selection([
        ('pending', 'Pending'), ('pass', 'Pass'), ('fail', 'Fail'), ('conditional_pass', 'Conditional Pass'),
    ], string='Result', default='pending', tracking=True)
    remarks = fields.Text(string='Remarks')

    def action_pass(self):
        self.write({'result': 'pass'})
        for rec in self:
            rec.sample_id.message_post(body=_('Sample QC passed (checked by %s).') % rec.qc_by_id.name)

    def action_fail(self):
        self.write({'result': 'fail'})
        for rec in self:
            rec.sample_id.message_post(body=_('Sample QC failed (checked by %s): %s') % (
                rec.qc_by_id.name, rec.remarks or '-'))
