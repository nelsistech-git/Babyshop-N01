# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Number the expense reports that exist already and give the submitted ones a Submission Date
    (their creation date), so old reports print the new Ref. No. / Submission Date as well."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Sheet = env['hr.expense.sheet'].with_context(active_test=False)
    for sheet in Sheet.search([('sheet_number', 'in', (False, 'New'))], order='id'):
        vals = {'sheet_number': env['ir.sequence'].next_by_code('hr.expense.sheet.number')}
        if sheet.state != 'draft' and not sheet.submission_date:
            vals['submission_date'] = sheet.create_date.date()
        sheet.write(vals)
    env['payment.due.item']._sync()
