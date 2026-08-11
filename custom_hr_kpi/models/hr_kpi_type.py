from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# class HrKpiDevelopmentPlan(models.Model):
#     _name = 'hr.kpi.development.plan'

#     kpi_id = fields.Many2one('hr.kpi', string='KPI Record', required=True, ondelete='cascade')
#     objective = fields.Char(string='Development Objectives')
#     initiative = fields.Char(string='Development Initiatives')
#     description = fields.Text(string='Development Initiative Description')
#     priority = fields.Selection([('high', 'High'), ('medium', 'Medium'), ('low', 'Low')], string='Priority')
#     due_date = fields.Date(string='Due Date')

class HrKpiType(models.Model):
    _name = "hr.kpi.type"

    name = fields.Char(string="KPI Types", required=True)
    description = fields.Text(string="KPI Description")
    code = fields.Char(string="Type Code", help="Optional short code for the KPI type")
    active = fields.Boolean(default=True, string="Active")
    sequence = fields.Integer(string="Sequence", default=10)

class HrKpiName(models.Model):
    _name = "hr.kpi.type.line"
    _description = "KPI Name"
    
    
    # normal fields
    name = fields.Char(string="KPI Name", required=True)
    description = fields.Text(string="KPI Description")
    active = fields.Boolean(default=True, string="Active")
    
    # many2one fields
    kpi_type_id = fields.Many2one(
        "hr.kpi.type", string="KPI Types", required=True, help="Type of the KPI"
    )
    
    # one2many fields
    
    # many2many fields
    
    # computed fields
    
    # onchange methods
    
    # constraints

    # sql constraints
    _sql_constraints = [
        (
            "unique_name_per_type",
            "unique(name, kpi_type_id)",
            "A KPI with the same name already exists under this type.",
        )
    ]
    
    