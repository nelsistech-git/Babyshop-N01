from odoo import fields, models, _


class ImportLogs(models.TransientModel):
    _name = "import.logs"
    _description = "Import Logs"

    name = fields.Text(string='Logs')
