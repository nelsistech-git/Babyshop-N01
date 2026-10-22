# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentPattern(models.Model):
    """Pattern Management (SRS section 19) — garment.pattern."""
    _name = 'garment.pattern'
    _description = 'Garment Pattern'
    _inherit = ['mail.thread']
    _order = 'pattern_number desc'

    pattern_number = fields.Char(string='Pattern Number', copy=False, readonly=True, default=lambda s: _('New'))
    pattern_name = fields.Char(string='Pattern Name', required=True)
    style_id = fields.Many2one('garment.style', string='Style', required=True, ondelete='cascade')
    version = fields.Char(string='Version', default='1.0')
    pattern_type = fields.Selection([
        ('base', 'Base Pattern'), ('graded', 'Graded Pattern'), ('marker', 'Marker Pattern'),
    ], string='Pattern Type', default='base')
    cad_software = fields.Char(string='CAD Software')
    created_by_id = fields.Many2one('res.users', string='Created By', default=lambda s: s.env.user)
    approved_by_id = fields.Many2one('res.users', string='Approved By')
    status = fields.Selection([
        ('draft', 'Draft'), ('under_review', 'Under Review'), ('approved', 'Approved'), ('obsolete', 'Obsolete'),
    ], string='Status', default='draft', tracking=True)

    component_ids = fields.Selection([
        ('front_panel', 'Front Panel'), ('back_panel', 'Back Panel'), ('sleeve', 'Sleeve'), ('collar', 'Collar'),
        ('cuff', 'Cuff'), ('pocket', 'Pocket'), ('hood', 'Hood'), ('waistband', 'Waistband'), ('rib', 'Rib'),
        ('facing', 'Facing'), ('placket', 'Placket'), ('belt_loop', 'Belt Loop'),
    ], string='Primary Component')
    component_notes = fields.Text(string='Component Notes', help='List all pattern components covered by this pattern set.')

    # Pattern Components checklist (SRS section 19) — which components this
    # pattern set actually includes, independent of the single "Primary
    # Component" selection above.
    comp_front_panel = fields.Boolean(string='Front Panel')
    comp_back_panel = fields.Boolean(string='Back Panel')
    comp_sleeve = fields.Boolean(string='Sleeve')
    comp_collar = fields.Boolean(string='Collar')
    comp_cuff = fields.Boolean(string='Cuff')
    comp_pocket = fields.Boolean(string='Pocket')
    comp_hood = fields.Boolean(string='Hood')
    comp_waistband = fields.Boolean(string='Waistband')
    comp_rib = fields.Boolean(string='Rib')
    comp_facing = fields.Boolean(string='Facing')
    comp_placket = fields.Boolean(string='Placket')
    comp_belt_loop = fields.Boolean(string='Belt Loop')

    pattern_size = fields.Char(string='Pattern Size')
    seam_allowance = fields.Char(string='Seam Allowance')
    fabric_grain = fields.Char(string='Fabric Grain')
    notches = fields.Char(string='Notches')
    drill_marks = fields.Char(string='Drill Marks')
    piece_quantity = fields.Integer(string='Piece Quantity')
    fabric_consumption = fields.Float(string='Fabric Consumption')
    marker_efficiency = fields.Float(string='Marker Efficiency (%)')

    pattern_file = fields.Binary(string='Pattern File', attachment=True)
    pattern_filename = fields.Char(string='Filename')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('pattern_number', _('New')) == _('New'):
                vals['pattern_number'] = self.env['ir.sequence'].next_by_code('garment.pattern') or _('New')
        return super().create(vals_list)
