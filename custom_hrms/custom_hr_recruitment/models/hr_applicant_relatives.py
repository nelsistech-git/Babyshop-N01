from odoo import fields, models


class HrApplicantRelatives(models.Model):
    _name = 'hr.applicant.relatives'
    _description = 'Applicant Relatives'

    applicant_id = fields.Many2one('hr.applicant', string='Applicant', required=True)

    name = fields.Char(string="Name")
    designation = fields.Char(string="Designation")
    department = fields.Char(string="Department & Workstation")
    organization = fields.Char(string="Organization")
    relation = fields.Char(string="Relationship")


class HrApplicantRelativesOutside(models.Model):
    _name = 'hr.applicant.relatives.outside'
    _description = 'Applicant Relatives Outside'

    applicant_id = fields.Many2one('hr.applicant', string='Applicant', required=True)

    name = fields.Char(string="Name")
    designation_department = fields.Char(string="Designation & Department")
    organization = fields.Char(string="Organization")
    org_contact = fields.Text(string="Contact address & Phone number")
    relation = fields.Char(string="Relationship")
