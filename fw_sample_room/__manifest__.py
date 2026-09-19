# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Sample Room - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Physical storage location tracking for development samples (FW Product '
                'PLM) and a Fabric/Trim Swatch library - the sample room\'s physical '
                'inventory, distinct from PLM\'s approval workflow.',
    'description': """
FW Sample Room
=================
Phase 6 module of the Nelsis Footwear ERP platform (Odoo Community 17).

FW Product PLM's Sample (Module 2) tracks the approval WORKFLOW of a
development sample - request, in progress, submitted, approved. It
does not track where the physical sample actually sits on a shelf.
This module adds a Storage Location master and links it onto the
existing Sample record (additive only - Module 2's model and workflow
are untouched), plus a separate Fabric/Trim Swatch library for the
physical material references merchandisers and designers pull from.

Features
--------
* Storage Location master (rack/bin/drawer) for the sample room
* Storage Location field added to FW Product PLM's Sample record
* Fabric/Trim Swatch library: material type, description, color,
  supplier, storage location, and which Styles reference each swatch

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'fw_plm'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_sample_room_sequence.xml',
        'views/fw_sample_location_views.xml',
        'views/fw_sample_form_location_views.xml',
        'views/fw_fabric_swatch_views.xml',
        'views/fw_sample_room_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
