# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentOperationRouting(models.Model):
    """Operation Routing (process sequence) per style, with an embedded
    Operation Bulletin / SMV line list. See Production Management SRS s.14,
    Planning & MES SRS s.14, MES SRS s.11, Shop Floor SRS s.9-10 (SMV)."""
    _name = 'garment.operation.routing'
    _description = 'Garment Production Routing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Routing Name', required=True, tracking=True)
    routing_number = fields.Char(string='Routing Number', copy=False, readonly=True, default=lambda s: _('New'))
    style_id = fields.Many2one('garment.style', string='Style', required=True, tracking=True)
    bom_id = fields.Many2one('garment.bom', string='BOM Reference')
    version = fields.Char(string='Version', default='1.0')
    total_smv = fields.Float(string='Total SMV', compute='_compute_total_smv', store=True)
    status = fields.Selection([
        ('draft', 'Draft'), ('active', 'Active'), ('obsolete', 'Obsolete'),
    ], string='Status', default='draft', tracking=True)
    line_ids = fields.One2many('garment.operation.routing.line', 'routing_id', string='Operations')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('line_ids.smv')
    def _compute_total_smv(self):
        for rec in self:
            rec.total_smv = sum(rec.line_ids.mapped('smv'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('routing_number', _('New')) == _('New'):
                vals['routing_number'] = self.env['ir.sequence'].next_by_code('garment.operation.routing') or _('New')
        return super().create(vals_list)

    def action_activate(self):
        self.write({'status': 'active'})


class GarmentOperationRoutingLine(models.Model):
    """Operation Bulletin line: one production operation with SMV, machine
    type, skill and operator requirement."""
    _name = 'garment.operation.routing.line'
    _description = 'Garment Routing Operation Line'
    _order = 'routing_id, sequence'

    routing_id = fields.Many2one('garment.operation.routing', string='Routing', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    operation_name = fields.Char(string='Operation', required=True)
    department = fields.Selection([
        ('cutting', 'Cutting'), ('sewing', 'Sewing'), ('washing', 'Washing'),
        ('finishing', 'Finishing'), ('packing', 'Packing'),
    ], string='Department', default='sewing')
    work_center_id = fields.Many2one('garment.work.center', string='Work Center')
    machine_type = fields.Selection([
        ('single_needle', 'Single Needle'), ('overlock', 'Overlock'), ('flatlock', 'Flatlock'),
        ('bartack', 'Bartack'), ('buttonhole', 'Buttonhole'), ('button_attach', 'Button Attach'),
        ('manual', 'Manual'), ('other', 'Other'),
    ], string='Machine Type')
    smv = fields.Float(string='SMV (Minutes)', digits=(6, 3), help='Standard Minute Value for this operation.')
    skill_level = fields.Selection([
        ('beginner', 'Beginner'), ('intermediate', 'Intermediate'),
        ('skilled', 'Skilled'), ('expert', 'Expert'), ('trainer', 'Trainer'),
    ], string='Required Skill Level', default='skilled')
    operator_requirement = fields.Integer(string='Operators Required', default=1)
