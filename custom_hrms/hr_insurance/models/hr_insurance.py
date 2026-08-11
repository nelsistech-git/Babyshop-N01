from odoo import fields, models


class HrInsurance(models.Model):
    """created a new model for employee insurance"""
    _name = 'hr.insurance'
    _description = 'HR Insurance'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Employee',
                                  required=True, help="Employee")
    policy_id = fields.Many2one('insurance.policy',
                                string='Policy', required=True, help="Policy")
    amount = fields.Float(string='Premium', required=True, help="Policy amount")
    sum_insured = fields.Float(string="Sum Insured", required=True,
                               help="Insured sum")
    policy_coverage = fields.Selection([('monthly', 'Monthly'),
                                        ('yearly', 'Yearly')],
                                       required=True, default='monthly',
                                       string='Policy Coverage',
                                       help="During of the policy")
    date_from = fields.Date(string='Date From',
                            default=fields.date.today(), readonly=True,
                            help="Start date")
    date_to = fields.Date(string='Date To', help="End date")
    state = fields.Selection([('active', 'Active'),
                              ('expired', 'Expired'), ],
                             default='active', string="State",
                             compute='get_status')
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, help="Company",
                                 default=lambda self: self.env.user.company_id)

    def get_status(self):
        """this function is get and set state"""
        current_date = fields.date.today()
        for rec in self:
            if rec.policy_coverage == 'monthly':
                rec.date_to = fields.Date.end_of(self.date_from, 'month')
            if rec.policy_coverage == 'yearly':
                rec.date_to = fields.Date.end_of(self.date_from, 'year')
            if rec.date_from <= current_date:
                if rec.date_to and rec.date_to >= current_date:
                    rec.state = 'active'
                else:
                    rec.state = 'expired'
