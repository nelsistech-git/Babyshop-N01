from odoo import fields, models


class HrApplicantDependent(models.Model):
    _name = 'hr.applicant.dependent'
    _description = 'Applicant Dependent'

    applicant_id = fields.Many2one('hr.applicant', string='Applicant', required=True, ondelete="cascade")

    dependent_name = fields.Char(string="Dependent Name")
    dependent_age = fields.Integer(string="Dependent Age")
    dependent_rel = fields.Char(string="Dependent Relationship")

# dependent_2_name = fields.Char(string="Dependent 2 Name", size=100)
# dependent_2_age = fields.Integer(string="Dependent 2 Age")
# dependent_2_rel = fields.Char(string="Dependent 2 Relationship", size=100)
#
# dependent_3_name = fields.Char(string="Dependent 3 Name", size=100)
# dependent_3_age = fields.Integer(string="Dependent 3 Age")
# dependent_3_rel = fields.Char(string="Dependent 3 Relationship", size=100)
#
# dependent_4_name = fields.Char(string="Dependent 4 Name", size=100)
# dependent_4_age = fields.Integer(string="Dependent 4 Age")
# dependent_4_rel = fields.Char(string="Dependent 4 Relationship", size=100)
#
# dependent_5_name = fields.Char(string="Dependent 5 Name", size=100)
# dependent_5_age = fields.Integer(string="Dependent 5 Age")
# dependent_5_rel = fields.Char(string="Dependent 5 Relationship", size=100)
#
# dependent_6_name = fields.Char(string="Dependent 6 Name", size=100)
# dependent_6_age = fields.Integer(string="Dependent 6 Age")
# dependent_6_rel = fields.Char(string="Dependent 6 Relationship", size=100)
