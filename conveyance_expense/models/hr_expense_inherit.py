from odoo import models, fields


class HrExpenseInherit(models.Model):
    _inherit = 'hr.expense'

    conveyance_sheet_ids = fields.One2many(
        comodel_name='conveyance.sheet',
        inverse_name='expense_id',
        string='Conveyance Sheets',
    )
    conveyance_sheet_count = fields.Integer(
        string='Conveyance Count',
        compute='_compute_conveyance_sheet_count',
    )

    def _compute_conveyance_sheet_count(self):
        for rec in self:
            rec.conveyance_sheet_count = len(rec.conveyance_sheet_ids)

    def action_open_conveyance_sheet(self):
        self.ensure_one()
        # If a sheet already exists, open it; otherwise open blank form
        existing = self.conveyance_sheet_ids[:1]
        ctx = {
            'default_employee_id': self.employee_id.id,
            'default_expense_id': self.id,
        }
        if existing:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Conveyance Sheet',
                'res_model': 'conveyance.sheet',
                'res_id': existing.id,
                'view_mode': 'form',
                'target': 'new',
                'context': ctx,
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Conveyance Sheet',
            'res_model': 'conveyance.sheet',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx,
        }