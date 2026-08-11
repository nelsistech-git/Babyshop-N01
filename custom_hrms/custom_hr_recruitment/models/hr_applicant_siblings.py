from odoo import fields, models


class HrApplicantSiblings(models.Model):
    _name = 'hr.applicant.siblings'
    _description = 'Applicant Siblings'

    applicant_id = fields.Many2one('hr.applicant', string='Applicant', required=True)

    sibling_name = fields.Char(string="Name")
    sibling_age = fields.Integer(string="Age")
    sibling_occupation = fields.Char(string="Occupation")
    sibling_organization = fields.Char(string="Organization")
    sibling_contact = fields.Char(string="Contact")

# sibling_2_name = fields.Char(string="Sibling 2 Name", size=100)
# sibling_2_age = fields.Integer(string="Sibling 2 Age", size=100)
# sibling_2_occupation = fields.Char(string="Sibling 2 Occupation", size=100)
# sibling_2_organization = fields.Char(string="Sibling 2 Organization", size=100)
# sibling_2_contact = fields.Char(string="Sibling 2 Contact", size=100)
#
# sibling_3_name = fields.Char(string="Sibling 3 Name", size=100)
# sibling_3_age = fields.Integer(string="Sibling 3 Age", size=100)
# sibling_3_occupation = fields.Char(string="Sibling 3 Occupation", size=100)
# sibling_3_organization = fields.Char(string="Sibling 3 Organization", size=100)
# sibling_3_contact = fields.Char(string="Sibling 3 Contact", size=100)
#
# sibling_4_name = fields.Char(string="Sibling 4 Name", size=100)
# sibling_4_age = fields.Integer(string="Sibling 4 Age", size=100)
# sibling_4_occupation = fields.Char(string="Sibling 4 Occupation", size=100)
# sibling_4_organization = fields.Char(string="Sibling 4 Organization", size=100)
# sibling_4_contact = fields.Char(string="Sibling 4 Contact", size=100)
