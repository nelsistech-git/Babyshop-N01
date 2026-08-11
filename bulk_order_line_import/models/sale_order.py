# -*- coding: utf-8 -*-
from odoo import models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_open_bulk_import_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Import Order Lines'),
            'res_model': 'wizard.bulk.order.line.import',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': 'sale.order',
                'default_res_id': self.id,
            },
        }
