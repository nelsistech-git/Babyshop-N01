# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RealEstateUnit(models.Model):
    """A saleable/rentable property unit (apartment, shop, office, etc.).

    NOTE (Phase 5 forward-reference): the rule "a unit cannot have more
    than one active booking/sale/rental agreement at the same time" will
    be enforced by a constraint added once the Booking model exists in
    Phase 5, following the same _inherit extension pattern used for
    project_id on Land in this phase.
    """
    _name = 'real.estate.unit'
    _description = 'Real Estate Property Unit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'building_id, floor_number, name'

    name = fields.Char(string='Unit Number', required=True, tracking=True,
                        help='e.g. A-1203')

    floor_id = fields.Many2one('real.estate.floor', string='Floor', required=True,
                                ondelete='restrict', tracking=True)
    building_id = fields.Many2one(related='floor_id.building_id', string='Building',
                                   store=True, readonly=True)
    block_id = fields.Many2one(related='floor_id.block_id', string='Block',
                                store=True, readonly=True)
    project_id = fields.Many2one(related='floor_id.project_id', string='Project',
                                  store=True, readonly=True)
    floor_number = fields.Integer(related='floor_id.floor_number', string='Floor No.',
                                   store=True, readonly=True)

    unit_type = fields.Selection([
        ('apartment', 'Apartment'),
        ('duplex', 'Duplex'),
        ('penthouse', 'Penthouse'),
        ('studio', 'Studio'),
        ('shop', 'Shop'),
        ('office', 'Office'),
        ('parking', 'Parking Space'),
        ('warehouse', 'Warehouse'),
        ('other', 'Other'),
    ], string='Unit Type', required=True, default='apartment', tracking=True)

    area = fields.Float(string='Area (Sqft)', digits=(12, 2))
    saleable_area = fields.Float(string='Saleable Area (Sqft)', digits=(12, 2))
    usable_area = fields.Float(string='Usable Area (Sqft)', digits=(12, 2))
    balcony_area = fields.Float(string='Balcony Area (Sqft)', digits=(12, 2))

    bedrooms = fields.Integer(string='Bedrooms')
    bathrooms = fields.Integer(string='Bathrooms')
    parking_count = fields.Integer(string='Parking Spaces')

    facing = fields.Selection([
        ('north', 'North'), ('south', 'South'), ('east', 'East'), ('west', 'West'),
        ('north_east', 'North-East'), ('north_west', 'North-West'),
        ('south_east', 'South-East'), ('south_west', 'South-West'),
    ], string='Facing')

    # ---- Pricing ----
    pricing_method = fields.Selection([
        ('fixed', 'Fixed Price'),
        ('per_sqft', 'Per Square Foot'),
    ], string='Pricing Method', default='per_sqft', required=True, tracking=True)
    price_per_sqft = fields.Monetary(string='Price per Sqft')
    fixed_base_price = fields.Monetary(
        string='Fixed Base Price',
        help='Used when Pricing Method = Fixed Price.')
    base_price = fields.Monetary(string='Base Price', compute='_compute_base_price',
                                  store=True, tracking=True)

    charge_line_ids = fields.One2many('real.estate.unit.charge', 'unit_id',
                                       string='Additional Charges')
    additional_charges_total = fields.Monetary(
        string='Additional Charges', compute='_compute_totals', store=True)
    discount = fields.Monetary(string='Discount')
    final_price = fields.Monetary(string='Final Price', compute='_compute_totals', store=True)

    owner_share_percentage = fields.Float(string='Owner Share (%)', digits=(5, 2))
    developer_share_percentage = fields.Float(string='Developer Share (%)', digits=(5, 2))

    status = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('booked', 'Booked'),
        ('sold', 'Sold'),
        ('under_construction', 'Under Construction'),
        ('ready', 'Ready'),
        ('rented', 'Rented'),
        ('blocked', 'Blocked'),
        ('cancelled', 'Cancelled'),
        ('handover_pending', 'Handover Pending'),
        ('handed_over', 'Handed Over'),
    ], string='Status', default='available', required=True, tracking=True, copy=False)

    notes = fields.Text(string='Notes')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'real_estate_unit_ir_attachment_rel',
        'unit_id', 'attachment_id', string='Documents')

    active = fields.Boolean(default=True)
    company_id = fields.Many2one(related='project_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(
        related='company_id.currency_id', string='Currency', readonly=True)

    _sql_constraints = [
        ('name_building_uniq', 'unique(name, building_id)',
         'This Unit Number already exists in this building.'),
        ('shares_check', 'CHECK(owner_share_percentage + developer_share_percentage <= 100.01)',
         'Owner Share + Developer Share cannot exceed 100%.'),
    ]

    @api.depends('pricing_method', 'fixed_base_price', 'price_per_sqft', 'saleable_area', 'area')
    def _compute_base_price(self):
        for rec in self:
            if rec.pricing_method == 'fixed':
                rec.base_price = rec.fixed_base_price
            else:
                area = rec.saleable_area or rec.area
                rec.base_price = (rec.price_per_sqft or 0.0) * (area or 0.0)

    @api.depends('base_price', 'discount', 'charge_line_ids.amount')
    def _compute_totals(self):
        for rec in self:
            rec.additional_charges_total = sum(rec.charge_line_ids.mapped('amount'))
            rec.final_price = rec.base_price + rec.additional_charges_total - rec.discount

    @api.constrains('discount', 'base_price', 'additional_charges_total')
    def _check_discount(self):
        for rec in self:
            if rec.discount and rec.discount > (rec.base_price + rec.additional_charges_total):
                raise ValidationError(
                    'Discount cannot exceed Base Price + Additional Charges for '
                    'unit "%s".' % rec.name)

    @api.constrains('owner_share_percentage', 'developer_share_percentage')
    def _check_shares(self):
        for rec in self:
            total = rec.owner_share_percentage + rec.developer_share_percentage
            if total and round(total, 2) > 100.0:
                raise ValidationError(
                    'Owner Share + Developer Share cannot exceed 100%% for '
                    'unit "%s" (currently %.2f%%).' % (rec.name, total))

    def action_set_available(self):
        self.write({'status': 'available'})

    def action_set_blocked(self):
        self.write({'status': 'blocked'})

    def action_set_under_construction(self):
        self.write({'status': 'under_construction'})

    def action_set_ready(self):
        self.write({'status': 'ready'})
