# -*- coding: utf-8 -*-
"""Debit Account / Branch moved from the request header to each line:
copy old header values onto the existing lines, and fill the vendor BIN."""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Branch = env['payment.request.branch']
    for request in env['payment.request'].search([]):
        branch = False
        if request.own_bank_branch:
            name = request.own_bank_branch.strip()
            branch = Branch.search([('name', '=', name)], limit=1) or Branch.create({'name': name})
        for line in request.line_ids:
            vals = {}
            if request.own_bank_id:
                vals['own_bank_id'] = request.own_bank_id.id
            if branch:
                vals['own_bank_branch_id'] = branch.id
            if not line.vendor_bin and line.partner_id.vat:
                vals['vendor_bin'] = line.partner_id.vat
            if vals:
                line.write(vals)
