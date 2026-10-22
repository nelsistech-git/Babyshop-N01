# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
PLM Project (SRS sections 4, 9-12, 19, 50-51) — garment.plm.project.

This is the OVERARCHING stage-gate governance record for a style's PLM
journey. It does not re-model Style / Tech Pack / BOM / Sample / Costing
data — those already live in garment_style_library, garment_techpack,
garment_bom_management, garment_sample_management and garment_costing. This
model links out to them (Many2one / computed relations) and tracks the
cross-module journey: Concept -> Design -> Sourcing -> Sampling -> Costing
-> Approval -> Production Handover.
"""
from odoo import api, fields, models, _

PLM_STAGES = [
    ('concept', 'Concept'),
    ('design', 'Design'),
    ('sourcing', 'Sourcing'),
    ('sampling', 'Sampling'),
    ('costing', 'Costing'),
    ('approval', 'Approval'),
    ('production_handover', 'Production Handover'),
]


class GarmentPlmProject(models.Model):
    """PLM Project — one record per style's end-to-end development journey."""
    _name = 'garment.plm.project'
    _description = 'Garment PLM Project (Stage-Gate Journey)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    # ------------------------------------------------------------------
    # General Information
    # ------------------------------------------------------------------
    plm_number = fields.Char(string='PLM Number', copy=False, readonly=True, default=lambda s: _('New'))
    name = fields.Char(string='Project Name', compute='_compute_name', store=True, readonly=False)
    style_id = fields.Many2one('garment.style', string='Style', required=True, tracking=True, ondelete='cascade')
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', related='style_id.buyer_id', store=True, readonly=True)
    style_number = fields.Char(related='style_id.style_number', string='Style Number', store=True)
    style_category_id = fields.Many2one('garment.style.category', related='style_id.style_category_id',
                                         string='Product Category', store=True)
    product_type = fields.Char(related='style_id.product_type', string='Product Type', store=True)
    season = fields.Char(related='style_id.season', string='Season', store=True)
    collection = fields.Char(related='style_id.collection', string='Collection', store=True)

    request_source = fields.Selection([
        ('buyer_inquiry', 'Buyer Inquiry'),
        ('merchandising', 'Merchandising Team'),
        ('internal_design', 'Internal Design Team'),
    ], string='Development Request Source', default='merchandising', tracking=True)
    development_request_id = fields.Many2one('garment.style.development.request', string='Development Request',
                                               domain="[('style_id', '=', style_id)]")
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Urgent'),
    ], string='Priority', default='1', tracking=True)

    target_launch_date = fields.Date(string='Target Production-Ready Date', tracking=True)
    actual_launch_date = fields.Date(string='Actual Production-Ready Date', tracking=True, copy=False)

    # ------------------------------------------------------------------
    # Cross-Module Links (Style -> Tech Pack -> BOM -> Sample -> Costing)
    # ------------------------------------------------------------------
    techpack_id = fields.Many2one('garment.techpack', string='Primary Tech Pack',
                                   domain="[('style_id', '=', style_id)]", tracking=True)
    bom_id = fields.Many2one('garment.bom', string='Primary BOM',
                              domain="[('style_id', '=', style_id)]", tracking=True)
    sample_id = fields.Many2one('garment.sample', string='Primary Sample',
                                 domain="[('style_id', '=', style_id)]", tracking=True)
    costing_id = fields.Many2one('garment.costing', string='Primary Costing',
                                  domain="[('style_id', '=', style_id)]", tracking=True)

    techpack_count = fields.Integer(string='Tech Packs', compute='_compute_cross_module_counts')
    bom_count = fields.Integer(string='BOMs', compute='_compute_cross_module_counts')
    sample_count = fields.Integer(string='Samples', compute='_compute_cross_module_counts')
    costing_count = fields.Integer(string='Costings', compute='_compute_cross_module_counts')
    ecr_count = fields.Integer(string='ECRs', compute='_compute_cross_module_counts')

    techpack_status = fields.Selection(related='techpack_id.state', string='Tech Pack Status', readonly=True)
    bom_status = fields.Selection(related='bom_id.status', string='BOM Status', readonly=True)
    sample_status = fields.Selection(related='sample_id.status', string='Sample Status', readonly=True)
    costing_status = fields.Selection(related='costing_id.status', string='Costing Status', readonly=True)
    style_status = fields.Selection(related='style_id.status', string='Style Status', readonly=True)

    # ------------------------------------------------------------------
    # Cross-Functional Team / Stage Gates / Tasks
    # ------------------------------------------------------------------
    team_ids = fields.One2many('garment.plm.team.member', 'project_id', string='Development Team')
    team_count = fields.Integer(string='Team Members', compute='_compute_team_task_counts')
    stage_gate_ids = fields.One2many('garment.plm.stage.gate', 'project_id', string='Stage Gates')
    task_ids = fields.One2many('garment.plm.task', 'project_id', string='Tasks')
    task_count = fields.Integer(string='Tasks', compute='_compute_team_task_counts')
    open_task_count = fields.Integer(string='Open Tasks', compute='_compute_team_task_counts')
    notification_ids = fields.One2many('garment.plm.notification', 'project_id', string='Notifications')

    # ------------------------------------------------------------------
    # Status / Progress
    # ------------------------------------------------------------------
    current_stage = fields.Selection(PLM_STAGES, string='Current Stage', default='concept', tracking=True,
                                      group_expand='_expand_stages')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('completed', 'Production Ready'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, group_expand='_expand_states')

    progress = fields.Float(string='Progress (%)', compute='_compute_progress', store=True)
    is_delayed = fields.Boolean(string='Delayed', compute='_compute_progress', store=True)
    delayed_stage_count = fields.Integer(string='Delayed Stages', compute='_compute_progress', store=True)
    pending_gate_approval_count = fields.Integer(string='Pending Gate Approvals', compute='_compute_progress',
                                                  store=True)

    # ------------------------------------------------------------------
    # AI Assist (extends the shared Garment AI Engine — Buyer CRM)
    # ------------------------------------------------------------------
    ai_last_insight = fields.Text(string='AI Development Insight', readonly=True)
    ai_last_run = fields.Datetime(string='AI Last Analyzed', readonly=True)
    ai_risk_level = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'),
    ], string='AI Production Risk', readonly=True, tracking=True)

    description = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('plm_number_uniq', 'unique(plm_number, company_id)', 'PLM Number must be unique per company!'),
    ]

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends('style_id', 'style_id.style_name', 'style_id.style_number')
    def _compute_name(self):
        for rec in self:
            if rec.style_id:
                rec.name = _('PLM Journey - %s') % (rec.style_id.style_name or rec.style_id.style_number or '')
            elif not rec.name:
                rec.name = _('New PLM Project')

    def _compute_cross_module_counts(self):
        for rec in self:
            style = rec.style_id
            rec.techpack_count = self.env['garment.techpack'].search_count(
                [('style_id', '=', style.id)]) if style else 0
            rec.bom_count = self.env['garment.bom'].search_count([('style_id', '=', style.id)]) if style else 0
            rec.sample_count = self.env['garment.sample'].search_count([('style_id', '=', style.id)]) if style else 0
            rec.costing_count = self.env['garment.costing'].search_count(
                [('style_id', '=', style.id)]) if style else 0
            rec.ecr_count = self.env['garment.ecr'].search_count([('style_id', '=', style.id)]) if style else 0

    @api.depends('team_ids', 'task_ids', 'task_ids.status')
    def _compute_team_task_counts(self):
        for rec in self:
            rec.team_count = len(rec.team_ids)
            rec.task_count = len(rec.task_ids)
            rec.open_task_count = len(rec.task_ids.filtered(lambda t: t.status not in ('completed', 'cancelled')))

    @api.depends('stage_gate_ids.status', 'stage_gate_ids.is_delayed',
                 'stage_gate_ids.gate_approval_ids.status')
    def _compute_progress(self):
        for rec in self:
            gates = rec.stage_gate_ids
            total = len(gates)
            completed = len(gates.filtered(lambda g: g.status == 'completed'))
            rec.progress = (completed / total * 100.0) if total else 0.0
            delayed = gates.filtered(lambda g: g.is_delayed)
            rec.delayed_stage_count = len(delayed)
            rec.is_delayed = bool(delayed)
            pending_approvals = gates.mapped('gate_approval_ids').filtered(lambda a: a.status == 'pending')
            rec.pending_gate_approval_count = len(pending_approvals)

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['state'].selection]

    def _expand_stages(self, stages, domain):
        return [key for key, _val in self._fields['current_stage'].selection]

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('plm_number', _('New')) == _('New'):
                vals['plm_number'] = self.env['ir.sequence'].next_by_code('garment.plm.project') or _('New')
        records = super().create(vals_list)
        for rec in records:
            if not rec.stage_gate_ids:
                rec._generate_default_stage_gates()
        return records

    def _generate_default_stage_gates(self):
        """Seed the 7 standard PLM stage gates (SRS section 4) for a new project."""
        StageGate = self.env['garment.plm.stage.gate']
        for rec in self:
            lines = []
            for idx, (stage_key, _stage_label) in enumerate(PLM_STAGES, start=1):
                lines.append((0, 0, {
                    'sequence': idx * 10,
                    'stage': stage_key,
                    'status': 'pending' if idx > 1 else 'in_progress',
                }))
            rec.write({'stage_gate_ids': lines})

    def action_generate_stage_gates(self):
        for rec in self:
            if not rec.stage_gate_ids:
                rec._generate_default_stage_gates()

    def action_advance_stage(self):
        """Advance current_stage to the next stage in the PLM flow."""
        flow = [key for key, _label in PLM_STAGES]
        for rec in self:
            idx = flow.index(rec.current_stage)
            if idx < len(flow) - 1:
                rec.current_stage = flow[idx + 1]
                if rec.state == 'draft':
                    rec.state = 'in_progress'
            else:
                rec.write({'state': 'completed', 'actual_launch_date': fields.Date.context_today(rec)})

    def action_mark_production_ready(self):
        self.write({'state': 'completed', 'current_stage': 'production_handover',
                    'actual_launch_date': fields.Date.context_today(self)})

    def action_run_ai_insight(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            risk_level, insight = ai_engine.analyze_plm_project_risk(rec)
            rec.write({
                'ai_risk_level': risk_level,
                'ai_last_insight': insight,
                'ai_last_run': fields.Datetime.now(),
            })
        return True

    # ------------------------------------------------------------------
    # Smart button navigation
    # ------------------------------------------------------------------
    def action_view_techpacks(self):
        self.ensure_one()
        return self._view_related_action('garment.techpack', _('Tech Packs'))

    def action_view_boms(self):
        self.ensure_one()
        return self._view_related_action('garment.bom', _('BOMs'))

    def action_view_samples(self):
        self.ensure_one()
        return self._view_related_action('garment.sample', _('Samples'))

    def action_view_costings(self):
        self.ensure_one()
        return self._view_related_action('garment.costing', _('Costings'))

    def action_view_ecrs(self):
        self.ensure_one()
        return self._view_related_action('garment.ecr', _('Engineering Change Requests'))

    def _view_related_action(self, model_name, title):
        return {
            'name': title, 'type': 'ir.actions.act_window', 'res_model': model_name,
            'view_mode': 'tree,form', 'domain': [('style_id', '=', self.style_id.id)],
            'context': {'default_style_id': self.style_id.id},
        }
