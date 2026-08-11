from odoo import models, fields


class InsurancePolicy(models.Model):
    """used this model for insurance policy"""
    _name = 'insurance.policy'
    _description = 'Insurance Policy'

    name = fields.Char(string='Name', required=True)
    note_field = fields.Html(string='Comment',
                             help="Notes for the insurance policy if any")
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, help="Company",
                                 default=lambda self: self.env.user.company_id)
