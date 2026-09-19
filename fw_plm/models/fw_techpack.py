# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models


class FwTechpack(models.Model):
    _name = 'fw.techpack'
    _description = 'Footwear Tech Pack'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'style_id, revision desc'

    name = fields.Char(string='Tech Pack Reference', compute='_compute_name', store=True)
    style_id = fields.Many2one('fw.style', string='Style', required=True, tracking=True,
                                ondelete='cascade')
    revision = fields.Char(string='Revision', default='Rev 1', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('review', 'Under Review'),
        ('approved', 'Approved'),
        ('obsolete', 'Obsolete'),
    ], string='Status', default='draft', tracking=True)

    construction_type = fields.Char(string='Construction Type',
                                     help="E.g. Cement, Vulcanized, Injection Molded, Stitch-down")
    upper_material = fields.Char(string='Upper Material')
    sole_material = fields.Char(string='Sole Material')
    lining_material = fields.Char(string='Lining Material')

    line_ids = fields.One2many('fw.techpack.spec.line', 'techpack_id', string='Spec Lines')

    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    approved_date = fields.Datetime(string='Approved On', readonly=True, copy=False)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.depends('style_id', 'revision')
    def _compute_name(self):
        for rec in self:
            if rec.style_id:
                rec.name = "%s - %s" % (rec.style_id.style_no or rec.style_id.name,
                                         rec.revision or '')
            else:
                rec.name = rec.revision or 'New Tech Pack'

    def action_send_review(self):
        self.write({'state': 'review'})

    def action_approve(self):
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })

    def action_set_obsolete(self):
        self.write({'state': 'obsolete'})

    def action_reset_draft(self):
        self.write({'state': 'draft', 'approved_by': False, 'approved_date': False})


class FwTechpackSpecLine(models.Model):
    _name = 'fw.techpack.spec.line'
    _description = 'Tech Pack Construction Spec Line'
    _order = 'sequence, id'

    techpack_id = fields.Many2one('fw.techpack', string='Tech Pack',
                                   required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    part_name = fields.Char(string='Part', required=True,
                             help="E.g. Upper, Lining, Sole, Insole, Outsole, Laces, Eyelets")
    material_description = fields.Char(string='Material / Spec Description')
    color_id = fields.Many2one('fw.color', string='Color')
    remarks = fields.Char(string='Remarks')
