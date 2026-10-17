# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import api, fields, models, _


class NelsisCommercialSetting(models.Model):
    _name = 'nelsis.commercial.setting'
    _description = 'Commercial Settings'

    name = fields.Char(default='Commercial Settings', required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    lc_model_id = fields.Many2one(
        'ir.model', string='LC Model', ondelete='set null',
        help="Pick the model of your existing LC Management module. Commercial files will reference "
             "records of this model; no LC data is copied or duplicated.")
    quantity_tolerance = fields.Float(
        string='Quantity Tolerance (%)', default=0.0,
        help="Company policy tolerance used when comparing documented and received quantities.")
    max_file_size_mb = fields.Float(string='Max Attachment Size (MB)', default=10.0)
    allowed_extensions = fields.Char(
        string='Allowed Attachment Extensions', default='pdf,jpg,jpeg,png,xlsx,xls,docx,doc',
        help="Comma-separated list, lower case, without dots.")

    _sql_constraints = [
        ('company_unique', 'unique(company_id)', 'Only one settings record per company is allowed.'),
    ]

    @api.model
    def get_setting(self):
        rec = self.sudo().search([('company_id', '=', self.env.company.id)], limit=1)
        if not rec:
            rec = self.sudo().create({'company_id': self.env.company.id})
        return rec

    @api.model
    def action_open_setting(self):
        rec = self.get_setting()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Commercial Settings'),
            'res_model': self._name,
            'res_id': rec.id,
            'view_mode': 'form',
            'target': 'current',
        }
