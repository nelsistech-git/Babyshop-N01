from odoo import api, fields, models

class HideMenuTemplate(models.Model):
    _name = 'sh.hide.menu.template'
    _description = "Hide Menu Template"

    name = fields.Char(string = "Name",required=True)
    menu_ids = fields.Many2many('ir.ui.menu',string = "Menus",required=True)
