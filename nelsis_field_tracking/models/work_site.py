from odoo import fields, models


class NelsisWorkSite(models.Model):
    _name = 'nelsis.work.site'
    _description = 'Work Site (Geofence)'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    latitude = fields.Float(digits=(10, 7), required=True)
    longitude = fields.Float(digits=(10, 7), required=True)
    radius_m = fields.Integer(string='Radius (m)', default=150, required=True)
    address = fields.Char()
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    employee_ids = fields.Many2many('hr.employee', string='Assigned Employees',
                                    help='Leave empty to allow every employee at this site.')

    _sql_constraints = [
        ('radius_positive', 'CHECK(radius_m > 0)', 'Radius must be positive.'),
    ]
