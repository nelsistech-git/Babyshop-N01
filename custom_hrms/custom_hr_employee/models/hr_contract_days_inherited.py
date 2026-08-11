from odoo import models, fields, api


class HrEmployeeContract(models.Model):
    _inherit = 'hr.contract'

    def _get_default_notice_days(self):
        if self.env['ir.config_parameter'].get_param(
                'hr_resignation.notice_period'):
            return self.env['ir.config_parameter'].get_param(
                'hr_resignation.no_of_days')
        else:
            return 0

    notice_days = fields.Integer(string="Notice Period", default=_get_default_notice_days)
    id_card_no = fields.Char(string="Employee ID", groups="hr.group_hr_user", related='employee_id.id_card_no')
    device_user_id = fields.Char(string='Biometric Device ID',
                                 related='employee_id.device_user_id')
    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Working Schedule',
        default=lambda self: self.env.company.resource_calendar_id.id, copy=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    gross_salary = fields.Float(string="Gross Salary")

    @api.model_create_multi
    def create(self, vals):
        contracts = super(HrEmployeeContract, self).create(vals)
        contracts.state = 'open'
        for val in vals:
            if val.get('state') == 'open':
                contracts._assign_open_contract()
        open_contracts = contracts.filtered(
            lambda c: c.state == 'open' or c.state == 'draft' and c.kanban_state == 'done')
        for contract in open_contracts.filtered(lambda c: c.employee_id and c.resource_calendar_id):
            contract.employee_id.tz = contract.resource_calendar_id.tz
        return contracts

    def write(self, vals):
        res = super(HrEmployeeContract, self).write(vals)
        calendar = vals.get('resource_calendar_id')
        if calendar and (self.state == 'open' or (self.state == 'draft' and self.kanban_state == 'done')):
            self.mapped('employee_id').write({'tz': self.resource_calendar_id.tz})
        return res
