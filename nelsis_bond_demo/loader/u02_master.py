# -*- coding: utf-8 -*-
"""Master data: partners, product categories, products and stock locations."""
from odoo import Command

PARTNERS = [
    # key, name, country xmlid, is_company
    ('sup_leather', 'Veneto Conceria S.p.A. (demo supplier)', 'base.it'),
    ('sup_chem', 'Shenzhen Adhesive Technology Co. (demo supplier)', 'base.cn'),
    ('sup_trim', 'Kolkata Trims Pvt. Ltd. (demo supplier)', 'base.in'),
    ('sup_local', 'Dhaka Packaging Works (demo local supplier)', 'base.bd'),
    ('bank_partner', 'Demo Commercial Bank PLC (fictitious)', 'base.bd'),
    ('customs_partner', 'Demo Customs House (fictitious)', 'base.bd'),
]

# key, name, code, uom xmlid, tracking, bonded?, hs, requires expiry, standard price, category key
PRODUCTS = [
    ('lth_black', 'Finished Cow Leather - Black (demo)', 'DEMO-LTH-001',
     'nelsis_bond_inventory.uom_sqm_leather', 'lot', True, 'DEMO-HS-4104.A', False, 6.5, 'leather'),
    ('lth_tan', 'Full-Grain Leather - Tan (demo)', 'DEMO-LTH-002',
     'nelsis_bond_inventory.uom_sqm_leather', 'lot', True, 'DEMO-HS-4104.B', False, 9.8, 'leather'),
    ('chem_pu', 'PU Adhesive (demo)', 'DEMO-CHM-001',
     'uom.product_uom_kgm', 'lot', True, 'DEMO-HS-3506.A', True, 4.2, 'chemicals'),
    ('trim_eyelet', 'Metal Eyelets (demo)', 'DEMO-TRM-001',
     'uom.product_uom_unit', 'lot', True, 'DEMO-HS-8308.A', False, 0.02, 'trims'),
    ('sole_rubber', 'Rubber Outsole Compound (demo)', 'DEMO-SOL-001',
     'uom.product_uom_kgm', 'lot', True, 'DEMO-HS-4005.A', False, 3.1, 'soles'),
    ('lth_suede', 'Suede Leather - Pending Classification (demo)', 'DEMO-LTH-003',
     'nelsis_bond_inventory.uom_sqm_leather', 'lot', False, 'DEMO-HS-4104.C', False, 7.7, 'leather'),
    ('carton', 'Local Cardboard Carton (demo)', 'DEMO-LCL-001',
     'uom.product_uom_unit', 'none', False, False, False, 0.45, 'local'),
]

CATEGORIES = [
    ('leather', 'Demo Bonded Materials / Leather'),
    ('chemicals', 'Demo Bonded Materials / Chemicals'),
    ('trims', 'Demo Bonded Materials / Trims'),
    ('soles', 'Demo Bonded Materials / Sole Materials'),
    ('local', 'Demo Local Materials'),
]

# key, name, parent key ('stock' = warehouse stock location)
LOCATIONS = [
    ('loc_bond_a', 'BOND-A Main Bonded Store'),
    ('loc_bond_b', 'BOND-B Production Buffer (Bonded)'),
    ('loc_nonbond', 'NB-1 Non-Bonded Store'),
]


def run(ctx):
    env = ctx.env

    def partners():
        for key, name, country in PARTNERS:
            if ctx.get('partner_' + key):
                continue
            partner = env['res.partner'].create({
                'name': name, 'company_type': 'company',
                'country_id': env.ref(country).id,
                'comment': 'Fictitious demo partner.',
            })
            ctx.reg('partner_' + key, partner)
        if not ctx.get('bank_demo'):
            bank = env['res.bank'].create({
                'name': 'Demo Commercial Bank PLC (fictitious)',
                'bic': 'DEMOBDDH',
                'country': env.ref('base.bd').id,
            })
            ctx.reg('bank_demo', bank)

    def categories():
        parent = env['product.category'].search([('name', '=', 'Demo Bonded Materials')], limit=1)
        if not parent:
            parent = env['product.category'].create({'name': 'Demo Bonded Materials'})
        ctx.reg('categ_parent', parent)
        for key, complete in CATEGORIES:
            if ctx.get('categ_' + key):
                continue
            name = complete.split(' / ')[-1]
            vals = {'name': name}
            if complete.startswith('Demo Bonded Materials /'):
                vals['parent_id'] = parent.id
            ctx.reg('categ_' + key, env['product.category'].create(vals))

    def products():
        for key, name, code, uom, tracking, bonded, hs, expiry, cost, categ in PRODUCTS:
            if ctx.get('prod_' + key):
                continue
            uom_rec = env.ref(uom)
            tmpl = env['product.template'].create({
                'name': name,
                'default_code': code,
                'detailed_type': 'product',
                'tracking': tracking,
                'uom_id': uom_rec.id,
                'uom_po_id': uom_rec.id,
                'categ_id': ctx.need('categ_' + categ).id,
                'standard_price': cost,
                'list_price': round(cost * 1.3, 2),
                'bond_hs_code': hs or False,
                'bond_requires_expiry': expiry,
                'description': 'Fictitious demo product. HS code is a placeholder, not a tariff code.',
            })
            ctx.reg('prod_' + key, tmpl)
            ctx.reg('pv_' + key, tmpl.product_variant_id)

    def locations():
        warehouse = env['stock.warehouse'].search([('company_id', '=', ctx.company.id)], limit=1)
        stock = warehouse.lot_stock_id
        ctx.reg('warehouse', warehouse)
        ctx.reg('loc_stock', stock)
        for key, name in LOCATIONS:
            if ctx.get(key):
                continue
            loc = env['stock.location'].create({
                'name': name, 'usage': 'internal', 'location_id': stock.id,
                'company_id': ctx.company.id,
            })
            loc.write({'bond_movement_allowed': True})
            ctx.reg(key, loc)

    ctx.step('master.partners', partners)
    ctx.step('master.categories', categories)
    ctx.step('master.products', products)
    ctx.step('master.locations', locations)
