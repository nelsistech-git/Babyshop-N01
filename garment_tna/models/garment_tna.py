# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentTna(models.Model):
    """TNA Master (SRS section 6-7) — garment.tna. One per order, the
    execution timeline every downstream department plans against."""
    _name = 'garment.tna'
    _description = 'Garment TNA (Time & Action Calendar)'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'shipment_date'

    tna_number = fields.Char(string='TNA Number', copy=False, readonly=True, default=lambda s: _('New'))
    name = fields.Char(string='TNA Name', compute='_compute_name', store=True)

    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True)
    buying_house = fields.Char(string='Buying House')
    order_confirmation_id = fields.Many2one('garment.merch.order.confirmation', string='Order Confirmation')
    purchase_order = fields.Char(string='Purchase Order Reference')
    style_id = fields.Many2one('garment.style', string='Style', required=True, tracking=True)
    order_number = fields.Char(string='Order Number')
    season = fields.Char(related='style_id.season', string='Season', store=True)
    product_category_id = fields.Many2one('garment.style.category', related='style_id.style_category_id',
                                           string='Product Category', store=True)
    order_quantity = fields.Integer(string='Order Quantity')
    factory = fields.Char(string='Factory')
    production_unit = fields.Char(string='Production Unit')
    shipment_date = fields.Date(string='Shipment Date', required=True, tracking=True)

    merchandiser_id = fields.Many2one('res.users', string='Merchandiser')
    owner_id = fields.Many2one('res.users', string='TNA Owner', default=lambda s: s.env.user)
    template_id = fields.Many2one('garment.tna.template', string='TNA Template')

    # Integration Architecture (SRS section 35): Tech Pack -> BOM -> Costing
    techpack_id = fields.Many2one('garment.techpack', string='Tech Pack')
    bom_id = fields.Many2one('garment.bom', string='BOM')
    costing_id = fields.Many2one('garment.costing', string='Costing')

    # Multi Currency & Export Support (SRS section 44)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda s: s.env.company.currency_id)
    port = fields.Char(string='Port')
    vessel = fields.Char(string='Vessel')
    forwarder = fields.Char(string='Forwarder')
    buyer_country_id = fields.Many2one('res.country', string='Buyer Country')
    destination = fields.Char(string='Destination')

    status = fields.Selection([
        ('draft', 'Draft'), ('generated', 'Generated'), ('department_review', 'Department Review'),
        ('active', 'Active'), ('monitoring', 'Monitoring'), ('completed', 'Completed'), ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True, group_expand='_expand_states')

    # FIXED: Renamed from 'activity_ids' to 'tna_activity_ids' to avoid conflict with mail.activity.mixin
    tna_activity_ids = fields.One2many('garment.tna.activity', 'tna_id', string='TNA Activities')
    milestone_ids = fields.One2many('garment.tna.milestone', 'tna_id', string='Milestones')
    delay_ids = fields.One2many('garment.tna.delay', 'tna_id', string='Delays')
    risk_ids = fields.One2many('garment.tna.risk', 'tna_id', string='Risks')
    approval_ids = fields.One2many('garment.tna.approval', 'tna_id', string='Approvals')
    notification_ids = fields.One2many('garment.tna.notification', 'tna_id', string='Notifications')
    revision_ids = fields.One2many('garment.tna.revision', 'tna_id', string='Revisions')

    progress = fields.Float(string='Overall Progress (%)', compute='_compute_progress', store=True)
    risk_level = fields.Selection([
        ('normal', 'Normal'), ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical'),
    ], string='Risk Level', compute='_compute_risk_level', store=True, tracking=True)

    risk_score = fields.Float(string='Risk Score (%)', compute='_compute_risk_score', store=True)
    main_risk_issue = fields.Char(string='Main Issue', compute='_compute_risk_score', store=True)

    activity_count = fields.Integer(compute='_compute_counts')
    delay_count = fields.Integer(compute='_compute_counts')
    critical_activity_count = fields.Integer(compute='_compute_counts')
    revision_count = fields.Integer(compute='_compute_counts')

    ai_shipment_risk_note = fields.Text(string='AI Shipment Risk', readonly=True)
    ai_schedule_suggestion_note = fields.Text(string='AI Schedule Suggestion', readonly=True)
    ai_shipment_probability_pct = fields.Float(string='AI Shipment Probability (%)', readonly=True)
    ai_expected_delay_days = fields.Integer(string='AI Expected Delay (Days)', readonly=True)
    ai_last_run = fields.Datetime(string='AI Last Analyzed', readonly=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('tna_number_uniq', 'unique(tna_number, company_id)', 'TNA Number must be unique per company!'),
    ]

    @api.depends('style_id.style_name', 'buyer_id.name')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s - %s' % (rec.style_id.style_name or '', rec.buyer_id.name or '')

    # FIXED: Updated depends and references to use tna_activity_ids
    @api.depends('tna_activity_ids.progress_pct')
    def _compute_progress(self):
        for rec in self:
            activities = rec.tna_activity_ids
            rec.progress = (sum(activities.mapped('progress_pct')) / len(activities)) if activities else 0.0

    @api.depends('delay_ids.severity')
    def _compute_risk_level(self):
        order = {'normal': 0, 'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        for rec in self:
            open_delays = rec.delay_ids
            if not open_delays:
                rec.risk_level = 'normal'
                continue
            worst = max(open_delays.mapped('severity'), key=lambda s: order.get(s, 0))
            rec.risk_level = worst

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    # FIXED: Updated depends and references to use tna_activity_ids
    @api.depends('tna_activity_ids', 'delay_ids', 'tna_activity_ids.is_critical_path', 'revision_ids')
    def _compute_counts(self):
        for rec in self:
            rec.activity_count = len(rec.tna_activity_ids)
            rec.delay_count = len(rec.delay_ids)
            rec.critical_activity_count = len(rec.tna_activity_ids.filtered('is_critical_path'))
            rec.revision_count = len(rec.revision_ids)

    @api.depends('risk_ids.probability_pct', 'risk_ids.impact', 'risk_ids.status',
                 'delay_ids.severity', 'delay_ids.activity_id.activity_name', 'delay_ids.delay_reason')
    def _compute_risk_score(self):
        """TNA Risk Management (SRS section 28) — rule-based Order Risk Score."""
        impact_weight = {'low': 1, 'medium': 2, 'high': 3}
        severity_weight = {'normal': 0, 'low': 10, 'medium': 25, 'high': 45, 'critical': 70}
        reason_labels = dict(self.env['garment.tna.delay']._fields['delay_reason'].selection)
        risk_labels = dict(self.env['garment.tna.risk']._fields['risk_type'].selection)
        for rec in self:
            score = 0.0
            best_contrib = -1.0
            main_issue = ''
            for risk in rec.risk_ids.filtered(lambda r: r.status != 'closed'):
                contrib = (risk.probability_pct or 0.0) * impact_weight.get(risk.impact, 1) / 3.0
                score += contrib
                if contrib > best_contrib:
                    best_contrib = contrib
                    main_issue = risk_labels.get(risk.risk_type, risk.risk_type)
            for delay in rec.delay_ids:
                contrib = severity_weight.get(delay.severity, 0) * 0.3
                score += contrib
                if contrib > best_contrib:
                    best_contrib = contrib
                    main_issue = delay.activity_id.activity_name or reason_labels.get(
                        delay.delay_reason, delay.delay_reason)
            rec.risk_score = max(0.0, min(100.0, score))
            rec.main_risk_issue = main_issue or _('No significant risk detected')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('tna_number', _('New')) == _('New'):
                vals['tna_number'] = self.env['ir.sequence'].next_by_code('garment.tna') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        if 'shipment_date' in vals and not self.env.context.get('tna_revision_apply'):
            for rec in self:
                if rec.status in ('completed', 'closed') and rec.shipment_date != vals['shipment_date']:
                    raise UserError(_(
                        '"%s" is %s — create a TNA Revision to change the Shipment Date instead of '
                        'editing it directly.') % (rec.tna_number, dict(rec._fields['status'].selection)
                                                    .get(rec.status)))
        return super().write(vals)

    def action_submit_for_review(self):
        for rec in self:
            if rec.status not in ('draft', 'generated'):
                raise UserError(_('Only a Draft/Generated TNA can be submitted for Department Review.'))
        self.write({'status': 'department_review'})

    def action_activate(self):
        for rec in self:
            if rec.status != 'department_review':
                raise UserError(_('Only a TNA in Department Review can be Activated.'))
            pending = rec.approval_ids.filtered(lambda a: a.status == 'pending')
            if pending:
                raise UserError(_('All Department Approvals must be Approved or Rejected before Activation.'))
        self.write({'status': 'active'})

    def action_start_monitoring(self):
        for rec in self:
            if rec.status != 'active':
                raise UserError(_('Only an Active TNA can move to Monitoring.'))
        self.write({'status': 'monitoring'})

    def action_complete(self):
        for rec in self:
            if rec.status != 'monitoring':
                raise UserError(_('Only a Monitoring TNA can be marked Completed.'))
        self.write({'status': 'completed'})

    def action_close(self):
        for rec in self:
            if rec.status != 'completed':
                raise UserError(_('Only a Completed TNA can be Closed.'))
        self.write({'status': 'closed'})

    def action_create_revision(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Create TNA Revision'),
            'res_model': 'garment.tna.revision', 'view_mode': 'form', 'target': 'new',
            'context': {
                'default_tna_id': self.id,
                'default_previous_shipment_date': self.shipment_date,
                'default_new_shipment_date': self.shipment_date,
                'default_requested_by_id': self.env.user.id,
            },
        }

    def action_view_revisions(self):
        self.ensure_one()
        return {'name': _('Revisions'), 'type': 'ir.actions.act_window', 'res_model': 'garment.tna.revision',
                'view_mode': 'tree,form', 'domain': [('tna_id', '=', self.id)],
                'context': {'default_tna_id': self.id}}

    def action_generate_from_template(self):
        for rec in self:
            if rec.template_id and rec.shipment_date:
                rec.template_id.action_apply_to_tna(rec)
                rec.write({'status': 'generated'})
        return True

    def action_run_ai_analysis(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            risk_note = ai_engine.predict_shipment_risk(rec)
            schedule_note = ai_engine.suggest_tna_schedule_adjustment(rec)
            probability_pct, expected_delay_days = ai_engine.predict_shipment_probability(rec)
            rec.write({
                'ai_shipment_risk_note': risk_note,
                'ai_schedule_suggestion_note': schedule_note,
                'ai_shipment_probability_pct': probability_pct,
                'ai_expected_delay_days': expected_delay_days,
                'ai_last_run': fields.Datetime.now(),
            })
        return True

    def action_view_activities(self):
        self.ensure_one()
        return {'name': _('Activities'), 'type': 'ir.actions.act_window', 'res_model': 'garment.tna.activity',
                'view_mode': 'tree,form', 'domain': [('tna_id', '=', self.id)],
                'context': {'default_tna_id': self.id}}

    def action_view_delays(self):
        self.ensure_one()
        return {'name': _('Delays'), 'type': 'ir.actions.act_window', 'res_model': 'garment.tna.delay',
                'view_mode': 'tree,form', 'domain': [('tna_id', '=', self.id)],
                'context': {'default_tna_id': self.id}}