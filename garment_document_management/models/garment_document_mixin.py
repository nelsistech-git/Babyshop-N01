# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import _, fields, models


class GarmentDocumentMixin(models.AbstractModel):
    """Reusable mixin any other module's model can add to its own
    ``_inherit`` list (alongside ``mail.thread``, e.g.
    ``_inherit = ['mail.thread', 'mail.activity.mixin', 'garment.document.mixin']``)
    to get a ready-made "Documents" smart button wired to the central
    ``garment.document`` register, without garment_document_management ever
    needing to depend on that module.

    It purposely carries no dependency in the other direction either: it
    only reads ``garment.document`` through the generic ``res_model``/
    ``res_id`` reference, so any of the other 27 modules in this suite can
    add ``garment_document_management`` to their own ``depends`` and inherit
    this mixin as a follow-up integration step — see IMPLEMENTATION_NOTES.md
    for the shortlist of modules that would benefit most (style_library,
    techpack, supplier, compliance, finance/LC, hr)."""
    _name = 'garment.document.mixin'
    _description = 'Garment Document Mixin'

    garment_document_count = fields.Integer(
        string='Documents', compute='_compute_garment_document_count')

    def _compute_garment_document_count(self):
        Document = self.env['garment.document']
        for rec in self:
            rec.garment_document_count = Document.search_count([
                ('res_model', '=', rec._name), ('res_id', '=', rec.id),
            ])

    def action_view_garment_documents(self):
        """Smart-button action: opens the central document register
        filtered to the documents linked to this specific record."""
        self.ensure_one()
        docs = self.env['garment.document'].search([
            ('res_model', '=', self._name), ('res_id', '=', self.id),
        ])
        return {
            'type': 'ir.actions.act_window',
            'name': _('Documents'),
            'res_model': 'garment.document',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', docs.ids)],
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
                'default_name': self.display_name,
            },
        }
