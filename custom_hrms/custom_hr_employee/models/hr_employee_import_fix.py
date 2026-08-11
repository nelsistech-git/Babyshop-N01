import logging
from odoo import api, models
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class HrEmployeeImportFix(models.Model):
    _inherit = 'hr.employee'

    def _compute_display_name(self):
        for record in self:
            name = record.name or ''
            id_card_no = record.id_card_no
            if id_card_no:
                record.display_name = "%s [%s]" % (name, id_card_no)
            else:
                record.display_name = name

    def name_get(self):
        result = []
        for record in self:
            name = record.name or ''
            id_card_no = record.id_card_no
            if id_card_no:
                name = "%s [%s]" % (name, id_card_no)
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None, order=None):
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            search_domain = []
        else:
            search_domain = [
                '|', '|',
                ('name', operator, name),
                ('id_card_no', operator, name),
                ('work_email', operator, name),
            ]
        return self._search(
            expression.AND([search_domain, args]),
            limit=limit,
            access_rights_uid=name_get_uid,
            order=order,
        )

    @api.model_create_multi
    def create(self, vals_list):
        processed_vals_list = []
        for vals in vals_list:
            safe_vals = dict(vals)
            safe_vals.pop('resource_id', None)
            safe_vals.pop('resource_calendar_id', None)
            processed_vals_list.append(safe_vals)

        employees = super().create(processed_vals_list)

        for employee in employees.filtered('user_id'):
            partner = employee.user_id.partner_id
            if not partner:
                continue
            employee.address_home_id = partner.id
            partner.write({
                'is_employee': True,
                'employee_id': employee.id_card_no,
                'mobile': employee.contact_no,
            })

        return employees