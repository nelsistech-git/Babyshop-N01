# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentCosting(models.Model):
    """Costing Master (SRS sections 6-8, 17-18) — garment.costing. Material
    cost is READ from the linked BOM (Module 5) rather than recalculated —
    there is exactly one place a fabric/trim/packaging price lives."""
    _name = 'garment.costing'
    _description = 'Garment Costing Sheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'costing_date desc'

    costing_number = fields.Char(string='Costing Number', copy=False, readonly=True, default=lambda s: _('New'))
    name = fields.Char(string='Costing Name', compute='_compute_name', store=True)
    costing_type = fields.Selection([
        ('preliminary', 'Preliminary Costing'), ('final', 'Final Costing'), ('revised', 'Revised Costing'),
    ], string='Costing Type', default='preliminary', required=True, tracking=True)

    style_id = fields.Many2one('garment.style', string='Style', required=True, tracking=True)
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', related='style_id.buyer_id', store=True)
    season = fields.Char(related='style_id.season', string='Season', store=True)
    product_category_id = fields.Many2one('garment.style.category', related='style_id.style_category_id',
                                           string='Product Category', store=True)
    sample_id = fields.Many2one('garment.sample', string='Sample Reference',
                                 domain="[('style_id', '=', style_id)]")
    bom_id = fields.Many2one('garment.bom', string='BOM Reference', domain="[('style_id', '=', style_id)]",
                              tracking=True)
    quotation_id = fields.Many2one('garment.merch.quotation', string='Quotation Reference')
    order_quantity = fields.Integer(string='Order Quantity', default=1)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    costing_date = fields.Date(string='Costing Date', default=fields.Date.context_today)
    validity_period = fields.Date(string='Valid Until')

    status = fields.Selection([
        ('draft', 'Draft'), ('material_costing', 'Material Costing'), ('production_costing', 'Production Costing'),
        ('management_review', 'Management Review'), ('buyer_submission', 'Buyer Submission'),
        ('negotiation', 'Negotiation'), ('approved', 'Approved'), ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True, group_expand='_expand_states')
    is_locked = fields.Boolean(string='Locked (Approved)', default=False, copy=False)

    # Incoterms Management (SRS section 29)
    incoterm = fields.Selection([
        ('fob', 'FOB - Free On Board'), ('cif', 'CIF - Cost, Insurance & Freight'),
        ('cfr', 'CFR - Cost & Freight'), ('exw', 'EXW - Ex Works'), ('fca', 'FCA - Free Carrier'),
    ], string='Incoterm', default='fob', required=True, tracking=True)
    international_freight_cost = fields.Monetary(string='International Freight', currency_field='currency_id')
    insurance_cost = fields.Monetary(string='Insurance Cost', currency_field='currency_id')
    incoterm_price = fields.Monetary(string='Price per Incoterm', compute='_compute_totals', store=True,
                                      currency_field='currency_id',
                                      help='FOB + International Freight (CFR) + Insurance (CIF), per SRS section 29.')

    # Material Cost — read live from the linked BOM (Module 5)
    material_cost = fields.Monetary(string='Material Cost (from BOM)', compute='_compute_material_cost', store=True,
                                     currency_field='currency_id')
    fabric_cost = fields.Monetary(string='Fabric Cost', compute='_compute_material_cost', store=True,
                                   currency_field='currency_id')
    trim_cost = fields.Monetary(string='Trim Cost', compute='_compute_material_cost', store=True,
                                 currency_field='currency_id')
    packaging_cost = fields.Monetary(string='Packaging Cost', compute='_compute_material_cost', store=True,
                                      currency_field='currency_id')

    # Manufacturing Cost (CM)
    cm_cost_ids = fields.One2many('garment.cm.cost', 'costing_id', string='CM Cost Sheets')
    cm_cost = fields.Monetary(string='CM Cost', compute='_compute_cm_cost', store=True, currency_field='currency_id')

    # Overhead & Additional Costs
    overhead_cost = fields.Monetary(string='Factory Overhead', currency_field='currency_id')
    testing_cost = fields.Monetary(string='Testing Cost', currency_field='currency_id')
    inspection_cost = fields.Monetary(string='Inspection Cost', currency_field='currency_id')
    sample_cost = fields.Monetary(string='Sample Cost', currency_field='currency_id')
    development_cost = fields.Monetary(string='Development Cost', currency_field='currency_id')
    freight_cost = fields.Monetary(string='Freight Cost', currency_field='currency_id')
    commission_cost = fields.Monetary(string='Commission', currency_field='currency_id')
    bank_charge_cost = fields.Monetary(string='Bank Charge', currency_field='currency_id')
    additional_cost_total = fields.Monetary(string='Total Additional Cost', compute='_compute_totals', store=True,
                                             currency_field='currency_id')

    # Profit & FOB
    profit_margin_type = fields.Selection([
        ('percentage', 'Percentage Margin'), ('fixed', 'Fixed Amount Margin'),
    ], string='Profit Margin Type', default='percentage')
    profit_margin_pct = fields.Float(string='Profit Margin (%)', default=10.0)
    profit_margin_fixed = fields.Monetary(string='Profit Margin (Fixed)', currency_field='currency_id')
    profit_amount = fields.Monetary(string='Profit Amount', compute='_compute_totals', store=True,
                                     currency_field='currency_id')
    profit_margin_actual_pct = fields.Float(string='Actual Profit Margin (%)', compute='_compute_totals', store=True,
                                             help='Profit Amount / FOB Price x 100 (SRS section 18 formula) — the '
                                                  'realized margin, distinct from the input Profit Margin % used '
                                                  'when the margin type is Fixed Amount.')
    fob_price = fields.Monetary(string='FOB Price', compute='_compute_totals', store=True,
                                 currency_field='currency_id')
    fob_value_total = fields.Monetary(string='Total FOB Value', compute='_compute_totals', store=True,
                                       currency_field='currency_id')
    margin_risk_note = fields.Char(string='AI Margin Protection Warning', compute='_compute_totals', store=True,
                                    help='SRS section 43 AI Margin Protection: warns when the actual profit margin '
                                         'falls below the recommended minimum of 8%.')

    # Currency Management — automatic conversion (SRS section 24)
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency', store=True)
    fob_price_company_currency = fields.Monetary(
        string='FOB Price (Company Currency)', compute='_compute_fob_price_company_currency',
        currency_field='company_currency_id',
        help='FOB Price converted to the company currency using the latest applicable Exchange Rate on/before '
             'the Costing Date (SRS section 24: "USD Cost x Exchange Rate = BDT Cost").')

    # Buyer Price Negotiation (SRS section 19) & Payment Terms (SRS section 28)
    negotiation_ids = fields.One2many('garment.cost.negotiation', 'costing_id', string='Buyer Negotiations')
    payment_term_ids = fields.One2many('garment.cost.payment.term', 'costing_id', string='Payment Terms')
    negotiation_count = fields.Integer(compute='_compute_counts')

    # Cost Saving Analysis (SRS section 26)
    cost_saving_note = fields.Text(string='AI Cost Saving Recommendation', readonly=True)
    expected_saving_per_unit = fields.Monetary(string='Expected Saving / Unit', currency_field='currency_id',
                                                readonly=True)
    annual_saving_estimate = fields.Monetary(string='Annual Saving Estimate', currency_field='currency_id',
                                              readonly=True)

    revision_ids = fields.One2many('garment.cost.revision', 'costing_id', string='Revisions')
    variance_ids = fields.One2many('garment.cost.variance', 'costing_id', string='Cost Variances')
    approval_ids = fields.One2many('garment.costing.approval', 'costing_id', string='Approvals')
    price_history_ids = fields.One2many('garment.price.history', 'costing_id', string='Supplier Price History')

    revision_count = fields.Integer(compute='_compute_counts')
    variance_count = fields.Integer(compute='_compute_counts')

    # AI Assist
    ai_cost_prediction_note = fields.Text(string='AI Cost Prediction', readonly=True)
    ai_cost_optimization_note = fields.Text(string='AI Cost Optimization', readonly=True)
    ai_buyer_price_note = fields.Text(string='AI Buyer Price / Negotiation Range', readonly=True)
    ai_last_run = fields.Datetime(string='AI Last Analyzed', readonly=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('costing_number_uniq', 'unique(costing_number, company_id)', 'Costing Number must be unique per company!'),
    ]

    @api.depends('style_id.style_name', 'costing_type')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s - %s' % (rec.style_id.style_name or '', dict(
                rec._fields['costing_type'].selection).get(rec.costing_type, ''))

    @api.depends('bom_id.fabric_cost_total', 'bom_id.trim_cost_total', 'bom_id.packaging_cost_total')
    def _compute_material_cost(self):
        for rec in self:
            rec.fabric_cost = rec.bom_id.fabric_cost_total or 0.0
            rec.trim_cost = rec.bom_id.trim_cost_total or 0.0
            rec.packaging_cost = rec.bom_id.packaging_cost_total or 0.0
            rec.material_cost = rec.fabric_cost + rec.trim_cost + rec.packaging_cost

    @api.depends('cm_cost_ids.total_cm')
    def _compute_cm_cost(self):
        for rec in self:
            rec.cm_cost = sum(rec.cm_cost_ids.mapped('total_cm'))

    @api.depends('material_cost', 'cm_cost', 'overhead_cost', 'testing_cost', 'inspection_cost', 'sample_cost',
                 'development_cost', 'freight_cost', 'commission_cost', 'bank_charge_cost',
                 'profit_margin_type', 'profit_margin_pct', 'profit_margin_fixed', 'order_quantity',
                 'incoterm', 'international_freight_cost', 'insurance_cost')
    def _compute_totals(self):
        for rec in self:
            rec.additional_cost_total = (rec.testing_cost + rec.inspection_cost + rec.sample_cost
                                          + rec.development_cost + rec.freight_cost + rec.commission_cost
                                          + rec.bank_charge_cost)
            base_cost = rec.material_cost + rec.cm_cost + rec.overhead_cost + rec.additional_cost_total
            if rec.profit_margin_type == 'fixed':
                rec.profit_amount = rec.profit_margin_fixed
            else:
                rec.profit_amount = base_cost * (rec.profit_margin_pct / 100.0)
            rec.fob_price = base_cost + rec.profit_amount
            rec.fob_value_total = rec.fob_price * (rec.order_quantity or 0)
            # SRS section 18 formula: Profit % = Profit Amount / FOB Price x 100
            rec.profit_margin_actual_pct = (rec.profit_amount / rec.fob_price * 100.0) if rec.fob_price else 0.0
            # SRS section 43 AI Margin Protection
            if rec.fob_price and rec.profit_margin_actual_pct < 8.0:
                rec.margin_risk_note = _(
                    'Warning: current FOB margin %.1f%% is below the recommended minimum of 8%% '
                    '- Low Profitability risk.') % rec.profit_margin_actual_pct
            else:
                rec.margin_risk_note = False
            # SRS section 29 Incoterms Management: FOB + Freight (+ Insurance) adjustment
            if rec.incoterm == 'cif':
                rec.incoterm_price = rec.fob_price + rec.international_freight_cost + rec.insurance_cost
            elif rec.incoterm == 'cfr':
                rec.incoterm_price = rec.fob_price + rec.international_freight_cost
            else:
                rec.incoterm_price = rec.fob_price

    @api.depends('fob_price', 'currency_id', 'company_id', 'costing_date')
    def _compute_fob_price_company_currency(self):
        exchange_rate = self.env['garment.exchange.rate']
        for rec in self:
            target = rec.company_id.currency_id
            if not target or rec.currency_id == target:
                rec.fob_price_company_currency = rec.fob_price
            else:
                rate = exchange_rate.get_rate(rec.currency_id, target, rec.costing_date)
                rec.fob_price_company_currency = (rec.fob_price * rate) if rate else 0.0

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    @api.depends('revision_ids', 'variance_ids', 'negotiation_ids')
    def _compute_counts(self):
        for rec in self:
            rec.revision_count = len(rec.revision_ids)
            rec.variance_count = len(rec.variance_ids)
            rec.negotiation_count = len(rec.negotiation_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('costing_number', _('New')) == _('New'):
                vals['costing_number'] = self.env['ir.sequence'].next_by_code('garment.costing') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        for rec in self:
            if rec.is_locked and not self.env.user.has_group('garment_costing.group_costing_manager') \
                    and any(f not in ('status', 'is_locked') for f in vals.keys()):
                raise UserError(_(
                    'Costing "%s" is locked (Approved). Raise a Revision to modify it.') % rec.costing_number)
        return super().write(vals)

    def action_lock(self):
        self.write({'is_locked': True, 'status': 'approved'})

    def action_unlock(self):
        self.write({'is_locked': False})

    def action_create_revision(self):
        self.ensure_one()
        last_rev = self.env['garment.cost.revision'].search(
            [('costing_id', '=', self.id)], order='version_number desc', limit=1)
        next_version = (last_rev.version_number or 0) + 1
        return {
            'type': 'ir.actions.act_window', 'name': _('New Cost Revision'),
            'res_model': 'garment.cost.revision', 'view_mode': 'form', 'target': 'new',
            'context': {'default_costing_id': self.id, 'default_version_number': next_version,
                        'default_previous_fob_price': self.fob_price},
        }

    def action_run_ai_analysis(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            prediction = ai_engine.predict_costing(rec)
            optimization = ai_engine.suggest_costing_optimization(rec)
            buyer_price = ai_engine.predict_buyer_price_range(rec)
            saving_note, saving_per_unit, annual_saving = ai_engine.suggest_cost_saving(rec)
            rec.write({
                'ai_cost_prediction_note': prediction,
                'ai_cost_optimization_note': optimization,
                'ai_buyer_price_note': buyer_price,
                'cost_saving_note': saving_note,
                'expected_saving_per_unit': saving_per_unit,
                'annual_saving_estimate': annual_saving,
                'ai_last_run': fields.Datetime.now(),
            })
        return True

    def action_open_cost_simulation(self):
        """AI Cost Simulation (SRS section 43): "What happens if fabric price increases 10%?" """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('AI Cost Simulation'),
            'res_model': 'garment.cost.simulation.wizard', 'view_mode': 'form', 'target': 'new',
            'context': {'default_costing_id': self.id},
        }

    def action_view_revisions(self):
        self.ensure_one()
        return {'name': _('Revisions'), 'type': 'ir.actions.act_window', 'res_model': 'garment.cost.revision',
                'view_mode': 'tree,form', 'domain': [('costing_id', '=', self.id)],
                'context': {'default_costing_id': self.id}}

    def action_view_variances(self):
        self.ensure_one()
        return {'name': _('Variances'), 'type': 'ir.actions.act_window', 'res_model': 'garment.cost.variance',
                'view_mode': 'tree,form', 'domain': [('costing_id', '=', self.id)],
                'context': {'default_costing_id': self.id}}

    def action_view_negotiations(self):
        self.ensure_one()
        return {'name': _('Buyer Negotiations'), 'type': 'ir.actions.act_window',
                'res_model': 'garment.cost.negotiation', 'view_mode': 'tree,form',
                'domain': [('costing_id', '=', self.id)], 'context': {'default_costing_id': self.id}}
