from odoo import models, fields, api
from odoo.exceptions import AccessError


class AppCollection(models.Model):
    _name = 'app.collection'
    _description = 'App Collection'
    _order = 'sequence, id'

    name = fields.Char(required=True, string='Name')
    sequence = fields.Integer(default=10)
    color_index = fields.Integer(default=0, string='Color')
    icon = fields.Char(default='📁', string='Icon')
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user,
        ondelete='cascade',
        required=True,
    )
    menu_ids = fields.Many2many(
        'ir.ui.menu',
        'app_collection_menu_rel',
        'collection_id',
        'menu_id',
        string='Apps',
    )

    def _check_owner(self):
        for rec in self:
            if rec.user_id.id != self.env.user.id:
                raise AccessError("You can only manage your own collections.")

    @api.model
    def get_user_collections(self):
        collections = self.search([('user_id', '=', self.env.user.id)])
        return [{
            'id': col.id,
            'name': col.name,
            'sequence': col.sequence,
            'color_index': col.color_index,
            'icon': col.icon or '📁',
            'menu_ids': col.menu_ids.ids,
        } for col in collections]

    @api.model
    def create_collection(self, name, icon='📁'):
        col = self.create({'name': name, 'icon': icon})
        return {
            'id': col.id,
            'name': col.name,
            'sequence': col.sequence,
            'color_index': col.color_index,
            'icon': col.icon,
            'menu_ids': [],
        }

    @api.model
    def rename_collection(self, collection_id, name, icon):
        col = self.browse(collection_id)
        col._check_owner()
        col.write({'name': name, 'icon': icon})
        return True

    @api.model
    def delete_collection(self, collection_id):
        col = self.browse(collection_id)
        col._check_owner()
        col.unlink()
        return True

    @api.model
    def add_app_to_collection(self, menu_id, collection_id):
        col = self.browse(collection_id)
        col._check_owner()
        col.write({'menu_ids': [(4, menu_id)]})
        return col.menu_ids.ids

    @api.model
    def remove_app_from_collection(self, menu_id, collection_id):
        col = self.browse(collection_id)
        col._check_owner()
        col.write({'menu_ids': [(3, menu_id)]})
        return col.menu_ids.ids

    @api.model
    def reorder_collections(self, ordered_ids):
        for seq, col_id in enumerate(ordered_ids, start=1):
            col = self.browse(col_id)
            if col.user_id.id == self.env.user.id:
                col.sequence = seq
        return True
