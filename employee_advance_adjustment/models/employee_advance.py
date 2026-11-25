from odoo import fields, models, _
from odoo.exceptions import UserError


class EmployeeAdvance(models.Model):
    _inherit = 'employee.advance'

    state = fields.Selection(
        selection_add=[('closed', 'Adjusted')], ondelete={'closed': 'set default'})
    adjustment_ids = fields.One2many(
        'employee.advance.adjustment', 'advance_id', string='Adjustments', readonly=True)

    def action_create_adjustment(self):
        self.ensure_one()
        if self.state != 'paid':
            raise UserError(_('Only a paid advance can be adjusted.'))
        if self.adjustment_ids.filtered(lambda a: a.state != 'cancel'):
            raise UserError(_('This advance already has an adjustment.'))
        adjustment = self.env['employee.advance.adjustment'].create({'advance_id': self.id})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'employee.advance.adjustment',
            'res_id': adjustment.id,
            'view_mode': 'form',
            'target': 'current',
        }
