from odoo import models, fields


class HrEmployee(models.Model):
    """inherited the model to add some fields"""
    _inherit = 'hr.employee'

    insurance_percentage = fields.Float(string="Company Percentage ",
                                        help="Company insurance percentage")
    deduced_amount_per_month = fields.Float(string="Salary deduced per month",
                                            compute="get_deduced_amount",
                                            help="Amount that is deduced from "
                                                 "the salary per month")
    deduced_amount_per_year = fields.Float(string="Salary deduced per year",
                                           compute="get_deduced_amount",
                                           help="Amount that is deduced from "
                                                "the salary per year")
    insurance_ids = fields.One2many('hr.insurance',
                                    'employee_id',
                                    string="Insurance", help="Insurance",
                                    domain=[('state', '=', 'active')])

    def get_deduced_amount(self):
        """used to get deduced amount"""
        current_date = fields.date.today()
        for emp in self:
            ins_amount = 0
            for ins in emp.insurance_ids:
                if ins.date_from <= current_date:
                    if ins.date_to >= current_date:
                        if ins.policy_coverage == 'monthly':
                            ins_amount = ins_amount + (ins.amount*12)
                        else:
                            ins_amount = ins_amount + ins.amount
            emp.deduced_amount_per_year = ins_amount-((ins_amount*emp.insurance_percentage)/100)
            emp.deduced_amount_per_month = emp.deduced_amount_per_year/12
