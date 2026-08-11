# coding=utf-8
from odoo import fields, models, api
from odoo.addons.helper import validator



class ContractParticularSettings(models.Model):
    """ To create probation period length """
    _name = 'hr.contract.particular.settings'
    _description = 'Contract Particular Settings'

    def _get_selection_options(self):
        return [
            ('basic', 'Basic(%) of Gross'),
            ('da', 'Dearness Allowance (%) of Gross'),
            ('hra', 'HRA(%) of Gross'),
            ('hra_on_basic', 'HRA(%) of Basic'),  # IMBD  #Halima
            ('travel', 'Conveyance(%) of Gross'),
            ('travel_on_basic', 'Conveyance(%) of Basic'),  # Halima
            ('meal', 'Meal(%) of Gross'),
            ('food_on_basic', 'Meal(%) of Basic'),  # IMBD #Halima
            ('food_on_fixed', 'Meal(Fixed)'),  # IMBD
            ('medical', 'Medical(%) of Gross'),
            ('medical_fixed', 'Medical (Fixed)'),  # IMBD, need to check execute first priority
            ('medical_on_basic', 'Medical(%) of Basic'),  # IMBD #Halima
            ('basic_gmv', 'Basic (Gross-Medical)/Value'),  # IMBD , need to check execute first priority
            ('pf', 'PF(%) of Gross'),
            ('pf_on_basic', 'PF(%) of Basic'),  # IMBD
            # ('company_pf', 'Company PF Contribution(%) of PF'),
            # ('festival_bonus', 'Festival Bonus(%) of Gross'),
            ('attendance_fixed_bonus', 'Attendance Bonus(Fixed)'),
            ('attendance_fixed_tiffin', 'Daily Tiffin(Fixed)')]

    name = fields.Selection(selection=_get_selection_options, required=True)
    value = fields.Float(string='Value', default=0, required=True)

    @api.constrains('name')
    def _check_unique_constraint_name(self):
        msg = "Particular"
        envobj = self.env['hr.contract.particular.settings']

        conditionlist1 = [('name', '=ilike', self.name)]
        validator.check_duplicate_value(self, envobj, conditionlist1, msg)
