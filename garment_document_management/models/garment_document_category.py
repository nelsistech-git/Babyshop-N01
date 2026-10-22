# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class GarmentDocumentCategory(models.Model):
    """Document folder / category taxonomy (SRS sections 7 and 10) —
    a hierarchical tree that mirrors the Company > Commercial/Production/
    HR/Compliance/Finance > sub-folder repository structure from the SRS.
    Any document department can build its own sub-tree here without this
    module needing to know about garment.hr.department or any other
    department model from another module (kept deliberately decoupled so
    this module stays installable standalone)."""
    _name = 'garment.document.category'
    _description = 'Document Category / Folder'
    _order = 'sequence, complete_name'
    _parent_store = True

    name = fields.Char(string='Category Name', required=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(default=10)
    parent_id = fields.Many2one('garment.document.category', string='Parent Folder', ondelete='cascade')
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many('garment.document.category', 'parent_id', string='Sub-Folders')
    complete_name = fields.Char(string='Full Path', compute='_compute_complete_name', store=True, recursive=True)
    department = fields.Selection([
        ('commercial', 'Commercial'),
        ('production', 'Production'),
        ('hr', 'HR'),
        ('compliance', 'Compliance'),
        ('finance', 'Finance'),
        ('quality', 'Quality'),
        ('logistics', 'Logistics'),
        ('general', 'General / Other'),
    ], string='Department')
    document_type = fields.Selection([
        ('contract', 'Contract'),
        ('invoice', 'Invoice'),
        ('certificate', 'Certificate'),
        ('report', 'Report'),
        ('policy', 'Policy'),
        ('drawing', 'Drawing'),
        ('technical', 'Technical Document'),
        ('other', 'Other'),
    ], string='AI Classification Hint', help='Used by the smart routing / auto-classification '
        'to guess a category for an uploaded file name (SRS sections 10 & 45).')
    color = fields.Integer(string='Color')
    active = fields.Boolean(default=True)
    document_ids = fields.One2many('garment.document', 'category_id', string='Documents')
    document_count = fields.Integer(string='Documents', compute='_compute_document_count')
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'A category with this code already exists!'),
    ]

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for rec in self:
            if rec.parent_id:
                rec.complete_name = '%s / %s' % (rec.parent_id.complete_name, rec.name)
            else:
                rec.complete_name = rec.name

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = self.env['garment.document'].search_count(
                [('category_id', '=', rec.id)])

    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create a recursive category hierarchy.'))

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'garment.document',
            'view_mode': 'tree,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id},
        }
