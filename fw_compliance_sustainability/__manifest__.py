# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Compliance & Sustainability - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Factory-owned certifications, environmental/sustainability metrics, '
                'and internal social compliance self-audits - distinct from buyer-'
                'conducted audits in FW Buyer 360.',
    'description': """
FW Compliance & Sustainability
=================================
Phase 6 module of the Nelsis Footwear ERP platform (Odoo Community 17).

FW Buyer 360 tracks compliance FROM THE BUYER'S SIDE - certificates the
buyer requires you to hold, and audits the buyer conducts on your
factory. This module is the mirror image: what the FACTORY itself
tracks and manages proactively, which increasingly matters for EU/US
buyers and platforms like Higg Index/Worldly, bluesign, and GRS.

Features
--------
* Factory Certification tracking (ISO 9001/14001/45001, BSCI, WRAP,
  SEDEX, Higg Index, bluesign, GRS, OEKO-TEX) with expiry status
* Environmental & Sustainability periodic metrics: water and energy
  consumption, waste generated vs. recycled, CO2 emission, chemical
  incident count
* Internal Social Compliance Self-Audit with score, result, findings,
  and a Corrective Action Plan (CAP) - run proactively by the factory
  itself ahead of a real buyer audit

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'hr', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_compliance_sustainability_sequence.xml',
        'views/fw_factory_certification_views.xml',
        'views/fw_environmental_record_views.xml',
        'views/fw_social_compliance_audit_views.xml',
        'views/fw_compliance_sustainability_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
