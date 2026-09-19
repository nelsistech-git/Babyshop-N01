# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import fields, models


class FwAqlTable(models.Model):
    _name = 'fw.aql.table'
    _description = 'Footwear AQL Sampling Reference Table'
    _order = 'inspection_level, lot_size_min'

    # NOTE FOR IMPLEMENTERS:
    # The default rows shipped with this module are commonly used reference values
    # for General Inspection Level II at AQL 2.5 (Major) and AQL 4.0 (Minor). They
    # are provided as a practical starting point only. Always verify against your
    # buyer's official AQL requirement or the current ISO 2859-1 / ANSI-ASQ Z1.4
    # published table before relying on this for compliance or contractual
    # decisions. Edit or add rows freely to match your buyer's exact chart.

    code_letter = fields.Char(string='Sample Size Code Letter', required=True)
    inspection_level = fields.Selection([
        ('i', 'Level I (Reduced)'),
        ('ii', 'Level II (Normal)'),
        ('iii', 'Level III (Tightened)'),
    ], string='Inspection Level', default='ii', required=True)

    lot_size_min = fields.Integer(string='Lot Size From', required=True)
    lot_size_max = fields.Integer(string='Lot Size To',
                                   help="Leave 0 to mean 'and above' (no upper limit).")

    sample_size = fields.Integer(string='Sample Size', required=True)

    aql_major_percent = fields.Float(string='AQL Major (%)', default=2.5)
    ac_major = fields.Integer(string='Accept (Major)')
    re_major = fields.Integer(string='Reject (Major)')

    aql_minor_percent = fields.Float(string='AQL Minor (%)', default=4.0)
    ac_minor = fields.Integer(string='Accept (Minor)')
    re_minor = fields.Integer(string='Reject (Minor)')

    ac_critical = fields.Integer(string='Accept (Critical)', default=0)
    re_critical = fields.Integer(string='Reject (Critical)', default=1)

    active = fields.Boolean(default=True)
