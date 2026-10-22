# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentTnaTemplate(models.Model):
    """TNA Template Management (SRS section 8) — garment.tna.template.
    Buyer-specific timelines, e.g. "Buyer A - Knitwear" or "Buyer B - Woven"."""
    _name = 'garment.tna.template'
    _description = 'Garment TNA Template'
    _order = 'name'

    name = fields.Char(string='Template Name', required=True)
    buyer_id = fields.Many2one('garment.buyer', string='Buyer')
    style_category_id = fields.Many2one('garment.style.category', string='Product Category')
    lead_time_days = fields.Integer(string='Lead Time (days)')
    shipment_type = fields.Selection([
        ('sea', 'Sea Freight'), ('air', 'Air Freight'), ('road', 'Road'), ('rail', 'Rail'), ('courier', 'Courier'),
    ], string='Shipment Type', default='sea')
    line_ids = fields.One2many('garment.tna.template.line', 'template_id', string='Template Activities')
    active = fields.Boolean(default=True)

    # Buyer Specific TNA Management (SRS section 42): Lead Time and
    # Milestones already exist above (line_ids.is_milestone); these cover
    # the remaining buyer-specific settings.
    approval_steps = fields.Text(string='Approval Steps',
                                  help='Buyer-specific approval workflow steps, e.g. "Merchandiser -> '
                                       'Merchandising Manager -> Buyer".')
    required_documents = fields.Text(string='Required Documents',
                                      help='Documents this buyer requires at each stage, e.g. lab dip approval '
                                           'letter, inspection report.')
    escalation_rules = fields.Text(string='Escalation Rules',
                                    help='Buyer-specific escalation notes, overriding the standard 4-level '
                                         'auto-escalation timing where needed.')

    def action_apply_to_tna(self, tna):
        """Generate TNA activities on the given garment.tna record, counting
        each line's days_before_shipment back from the TNA's shipment date,
        then wires up any line-to-line Dependencies (SRS sections 8, 13) on
        the newly-created activities."""
        Activity = self.env['garment.tna.activity']
        line_to_activity = {}
        for line in self.line_ids:
            planned_end = fields.Date.subtract(tna.shipment_date, days=line.days_before_shipment) \
                if tna.shipment_date else False
            activity = Activity.create({
                'tna_id': tna.id,
                'activity_name': line.activity_name,
                'category': line.category,
                'department': line.department,
                'planned_end_date': planned_end,
                'is_milestone': line.is_milestone,
                'sequence': line.sequence,
            })
            line_to_activity[line.id] = activity
        for line in self.line_ids:
            predecessor_activity = line_to_activity.get(line.predecessor_line_id.id)
            if predecessor_activity:
                line_to_activity[line.id].write({
                    'dependency_type': line.dependency_type,
                    'predecessor_activity_id': predecessor_activity.id,
                })
        return True


class GarmentTnaTemplateLine(models.Model):
    _name = 'garment.tna.template.line'
    _description = 'Garment TNA Template Activity Line'
    _order = 'sequence'

    template_id = fields.Many2one('garment.tna.template', string='Template', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    activity_name = fields.Char(string='Activity', required=True)
    category = fields.Selection([
        ('merchandising', 'Merchandising'), ('product_development', 'Product Development'),
        ('material', 'Material'), ('production', 'Production'), ('quality', 'Quality'), ('commercial', 'Commercial'),
    ], string='Category', required=True)
    department = fields.Char(string='Department')
    days_before_shipment = fields.Integer(string='Days Before Shipment', required=True)
    is_milestone = fields.Boolean(string='Milestone')

    # Dependency Management (SRS section 13), pre-configured on the
    # template and copied onto the generated activities on Apply.
    dependency_type = fields.Selection([
        ('finish_to_start', 'Finish-to-Start'), ('start_to_start', 'Start-to-Start'),
        ('finish_to_finish', 'Finish-to-Finish'),
    ], string='Dependency Type')
    predecessor_line_id = fields.Many2one('garment.tna.template.line', string='Predecessor Activity',
                                           domain="[('template_id', '=', template_id)]")
