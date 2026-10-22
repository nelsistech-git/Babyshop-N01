# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentStyle(models.Model):
    """Style Master — single source of truth for a garment style, shared by
    Merchandising, BOM, Costing, Sampling, Production and Quality. See
    Style Library & Product Development SRS, sections 6-11 & 22-25."""
    _name = 'garment.style'
    _description = 'Garment Style Master'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'style_name'

    # ------------------------------------------------------------------
    # General Information
    # ------------------------------------------------------------------
    style_number = fields.Char(string='Style Number', copy=False, readonly=True, default=lambda s: _('New'))
    buyer_style_number = fields.Char(string='Buyer Style Number')
    factory_style_number = fields.Char(string='Factory Style Number')
    style_name = fields.Char(string='Style Name', required=True, tracking=True)
    product_name = fields.Char(string='Product Name')
    brand = fields.Char(string='Brand')
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', tracking=True)
    collection = fields.Char(string='Collection')
    season = fields.Char(string='Season')
    style_category_id = fields.Many2one('garment.style.category', string='Product Category', tracking=True)
    product_type = fields.Char(string='Product Type')
    gender = fields.Selection([
        ('men', 'Men'), ('women', 'Women'), ('unisex', 'Unisex'), ('boys', 'Boys'), ('girls', 'Girls'),
    ], string='Gender')
    age_group = fields.Selection([
        ('adult', 'Adult'), ('kids', 'Kids'), ('infant', 'Infant'), ('toddler', 'Toddler'),
    ], string='Age Group')
    market = fields.Selection([('domestic', 'Domestic'), ('export', 'Export')], string='Market')
    country_id = fields.Many2one('res.country', string='Country')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda s: s.env.company.currency_id)

    # Bangladesh Garment Industry — Export Requirements (SRS section 40)
    export_documentation_ref = fields.Char(string='Export Documentation Reference')
    port_destination = fields.Char(string='Port of Destination')
    packaging_instructions = fields.Text(string='Packaging Instructions')

    # ------------------------------------------------------------------
    # Product Attributes
    # ------------------------------------------------------------------
    sleeve_type = fields.Char(string='Sleeve Type')
    neck_type = fields.Char(string='Neck Type')
    collar_type = fields.Char(string='Collar Type')
    hood_type = fields.Char(string='Hood Type')
    pocket_type = fields.Char(string='Pocket Type')
    waist_type = fields.Char(string='Waist Type')
    bottom_type = fields.Char(string='Bottom Type')
    closure_type = fields.Char(string='Closure Type')
    fit_type = fields.Char(string='Fit Type')
    construction_type = fields.Char(string='Construction Type')
    stitch_type = fields.Char(string='Stitch Type')

    # ------------------------------------------------------------------
    # Design Information / Decoration
    # ------------------------------------------------------------------
    front_view_image = fields.Binary(string='Front View', attachment=True)
    back_view_image = fields.Binary(string='Back View', attachment=True)
    side_view_image = fields.Binary(string='Side View', attachment=True)
    inside_view_image = fields.Binary(string='Inside View', attachment=True)

    # Design Elements (SRS section 10) — distinct from the Product Attribute
    # "Type" fields above: these capture the actual design/construction notes
    # for each element.
    collar_design = fields.Char(string='Collar Design')
    sleeve_design = fields.Char(string='Sleeve Design')
    pocket_design = fields.Char(string='Pocket Design')
    hood_design = fields.Char(string='Hood Design')
    waist_design = fields.Char(string='Waist Design')
    bottom_design = fields.Char(string='Bottom Design')
    hem_design = fields.Char(string='Hem Design')
    cuff_design = fields.Char(string='Cuff Design')
    label_position = fields.Char(string='Label Position')
    logo_placement = fields.Char(string='Logo Placement')

    decoration_type_ids = fields.Selection([
        ('printing', 'Printing'), ('embroidery', 'Embroidery'), ('applique', 'Appliqué'),
        ('heat_transfer', 'Heat Transfer'), ('sublimation', 'Sublimation'), ('silicone_patch', 'Silicone Patch'),
        ('leather_patch', 'Leather Patch'), ('rubber_patch', 'Rubber Patch'), ('reflective_print', 'Reflective Print'),
    ], string='Primary Decoration')
    # Decoration checklist (SRS section 10) — a style commonly combines more
    # than one decoration method, so these supplement the single "Primary
    # Decoration" selection above.
    decoration_printing = fields.Boolean(string='Printing')
    decoration_embroidery = fields.Boolean(string='Embroidery')
    decoration_applique = fields.Boolean(string='Appliqué')
    decoration_heat_transfer = fields.Boolean(string='Heat Transfer')
    decoration_sublimation = fields.Boolean(string='Sublimation')
    decoration_silicone_patch = fields.Boolean(string='Silicone Patch')
    decoration_leather_patch = fields.Boolean(string='Leather Patch')
    decoration_rubber_patch = fields.Boolean(string='Rubber Patch')
    decoration_reflective_print = fields.Boolean(string='Reflective Print')
    decoration_notes = fields.Text(string='Decoration Notes')

    # ------------------------------------------------------------------
    # Fabric / Trim specification lines
    # ------------------------------------------------------------------
    fabric_line_ids = fields.One2many('garment.style.fabric.line', 'style_id', string='Fabric Details')
    trim_line_ids = fields.One2many('garment.style.trim.line', 'style_id', string='Trim Details')

    # ------------------------------------------------------------------
    # Status / PLM Lifecycle
    # ------------------------------------------------------------------
    status = fields.Selection([
        ('draft', 'Draft'),
        ('development', 'Development'),
        ('internal_review', 'Internal Review'),
        ('sample_development', 'Sample Development'),
        ('buyer_review', 'Buyer Review'),
        ('approved', 'Approved'),
        ('production_ready', 'Production Ready'),
        ('archived', 'Archived'),
    ], string='Style Status', default='draft', tracking=True, group_expand='_expand_states')
    lifecycle_stage = fields.Selection([
        ('concept', 'Concept'), ('design', 'Design'), ('technical_development', 'Technical Development'),
        ('pattern_development', 'Pattern Development'), ('measurement_approval', 'Measurement Approval'),
        ('sample_development', 'Sample Development'), ('internal_approval', 'Internal Approval'),
        ('buyer_approval', 'Buyer Approval'), ('production_release', 'Production Release'),
        ('active', 'Active'), ('discontinued', 'Discontinued'), ('archived', 'Archived'),
    ], string='PLM Stage', default='concept', tracking=True)
    is_locked = fields.Boolean(string='Locked (Approved)', default=False, copy=False,
                                help='Approved style versions are locked against direct editing; '
                                     'changes must go through a Revision or ECR.')

    designer_id = fields.Many2one('res.users', string='Fashion Designer', tracking=True)
    pattern_master_id = fields.Many2one('res.users', string='Pattern Master')
    development_request_id = fields.Many2one('garment.style.development.request', string='Development Request')

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    color_ids = fields.One2many('garment.style.color', 'style_id', string='Colorways')
    image_ids = fields.One2many('garment.style.image', 'style_id', string='Image Gallery')
    document_ids = fields.One2many('garment.style.document', 'style_id', string='Digital Assets')
    measurement_chart_ids = fields.One2many('garment.measurement.chart', 'style_id', string='Measurement Charts')
    pattern_ids = fields.One2many('garment.pattern', 'style_id', string='Patterns')
    cad_file_ids = fields.One2many('garment.cad.file', 'style_id', string='CAD Files')
    revision_ids = fields.One2many('garment.style.revision', 'style_id', string='Revisions')
    ecr_ids = fields.One2many('garment.ecr', 'style_id', string='Engineering Change Requests')
    approval_ids = fields.One2many('garment.style.approval', 'style_id', string='Approvals')

    color_count = fields.Integer(compute='_compute_counts')
    pattern_count = fields.Integer(compute='_compute_counts')
    revision_count = fields.Integer(compute='_compute_counts')
    ecr_count = fields.Integer(compute='_compute_counts')

    # Automation Rule (SRS section 28): "Alert users when required assets
    # (CAD, pattern, artwork) are missing" + section 29 "Missing Document
    # Count" technical KPI.
    missing_assets_warning = fields.Text(string='Missing Assets', compute='_compute_missing_assets_warning')
    has_missing_assets = fields.Boolean(string='Has Missing Assets', compute='_compute_missing_assets_warning',
                                         store=True)

    # ------------------------------------------------------------------
    # AI Assist
    # ------------------------------------------------------------------
    ai_similar_style_ids = fields.Many2many('garment.style', 'garment_style_similarity_rel',
                                             'style_id', 'similar_style_id', string='AI Suggested Similar Styles',
                                             readonly=True)
    ai_last_insight = fields.Text(string='AI Insight', readonly=True)
    ai_last_run = fields.Datetime(string='AI Last Analyzed', readonly=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('style_number_uniq', 'unique(style_number, company_id)', 'Style Number must be unique per company!'),
    ]

    @api.depends('color_ids', 'pattern_ids', 'revision_ids', 'ecr_ids')
    def _compute_counts(self):
        for rec in self:
            rec.color_count = len(rec.color_ids)
            rec.pattern_count = len(rec.pattern_ids)
            rec.revision_count = len(rec.revision_ids)
            rec.ecr_count = len(rec.ecr_ids)

    @api.depends('status', 'pattern_ids', 'cad_file_ids', 'document_ids', 'document_ids.asset_category',
                 'measurement_chart_ids', 'color_ids')
    def _compute_missing_assets_warning(self):
        for rec in self:
            missing = []
            if rec.status not in ('draft', 'development'):
                if not rec.pattern_ids:
                    missing.append(_('Pattern'))
                if not rec.cad_file_ids:
                    missing.append(_('CAD File'))
                if not rec.measurement_chart_ids:
                    missing.append(_('Measurement Chart'))
                if not rec.color_ids:
                    missing.append(_('Colorway'))
                if not any(d.asset_category in ('document', '3d_asset') for d in rec.document_ids):
                    missing.append(_('Artwork / Tech Pack Document'))
            rec.has_missing_assets = bool(missing)
            rec.missing_assets_warning = (
                _('Missing required assets: %s') % ', '.join(missing)) if missing else False

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('style_number', _('New')) == _('New'):
                vals['style_number'] = self._generate_style_number(vals.get('style_category_id'))
        records = super().create(vals_list)
        records._generate_default_approval_steps()
        return records

    def _generate_style_number(self, style_category_id):
        """Configurable Style Number generation (SRS section 7), e.g.
        ST-2026-KN-000001: Company/Year + Product-Category code + running
        sequence."""
        year = fields.Date.context_today(self).year
        category = self.env['garment.style.category'].browse(style_category_id) if style_category_id else False
        category_code = (category.code or 'GEN').upper() if category else 'GEN'
        running_number = self.env['ir.sequence'].next_by_code('garment.style') or '000001'
        return 'ST-%s-%s-%s' % (year, category_code, running_number)

    def write(self, vals):
        for rec in self:
            if rec.is_locked and not self.env.user.has_group('garment_style_library.group_style_design_manager') \
                    and any(f not in ('status', 'lifecycle_stage', 'is_locked') for f in vals.keys()):
                raise UserError(_(
                    'Style "%s" is locked (Approved). Raise a Revision or an Engineering Change Request '
                    'to modify it.') % rec.style_name)
        previous_status = {rec.id: rec.status for rec in self} if 'status' in vals else {}
        result = super().write(vals)
        if 'status' in vals:
            self._notify_status_change(previous_status)
        return result

    def _notify_status_change(self, previous_status):
        """Automation Rules (SRS section 28): notify the Pattern team after
        design approval, and notify Sampling after pattern approval."""
        for rec in self:
            before = previous_status.get(rec.id)
            after = rec.status
            if before == after:
                continue
            if after == 'sample_development' and rec.pattern_master_id:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Pattern development ready to start'),
                    note=_('Style "%s" has moved to Sample Development — please begin pattern work.')
                    % rec.style_name,
                    user_id=rec.pattern_master_id.id,
                )
            if after in ('sample_development', 'buyer_review') and before == 'internal_review':
                rec.message_post(body=_(
                    'Pattern/technical development approved — style is ready for Sampling.'))

    def _generate_default_approval_steps(self):
        """Seed approval_ids from the matching garment.style.approval.rule
        records (Configuration > Approval Rules) if none exist yet."""
        ApprovalRule = self.env['garment.style.approval.rule']
        for rec in self:
            if rec.approval_ids:
                continue
            rules = ApprovalRule.search([
                '|', ('style_category_id', '=', rec.style_category_id.id), ('style_category_id', '=', False),
            ], order='sequence')
            if not rules:
                continue
            rec.write({'approval_ids': [
                (0, 0, {
                    'sequence': rule.sequence,
                    'approval_step': rule.approval_step,
                }) for rule in rules
            ]})

    def action_generate_approvals_from_rules(self):
        """Manual trigger (button) to seed missing approval steps from the
        configured Approval Rules — useful for styles created before a
        matching rule existed."""
        targets = self.filtered(lambda r: not r.approval_ids)
        if not targets:
            raise UserError(_('All selected styles already have approval steps.'))
        targets._generate_default_approval_steps()

    def action_lock_style(self):
        self.write({'is_locked': True})

    def action_unlock_style(self):
        self.write({'is_locked': False})

    def action_create_revision(self):
        self.ensure_one()
        last_rev = self.env['garment.style.revision'].search(
            [('style_id', '=', self.id)], order='version_number desc', limit=1)
        next_version = (last_rev.version_number or 0) + 1
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Revision'),
            'res_model': 'garment.style.revision',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_style_id': self.id, 'default_version_number': next_version,
                        'default_parent_version_id': last_rev.id if last_rev else False},
        }

    def action_run_ai_similarity(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            similar_styles, insight = ai_engine.find_similar_styles(rec)
            rec.write({
                'ai_similar_style_ids': [(6, 0, similar_styles.ids)],
                'ai_last_insight': insight,
                'ai_last_run': fields.Datetime.now(),
            })
        return True

    def action_view_patterns(self):
        self.ensure_one()
        return {
            'name': _('Patterns'), 'type': 'ir.actions.act_window', 'res_model': 'garment.pattern',
            'view_mode': 'tree,form', 'domain': [('style_id', '=', self.id)],
            'context': {'default_style_id': self.id},
        }

    def action_view_revisions(self):
        self.ensure_one()
        return {
            'name': _('Revisions'), 'type': 'ir.actions.act_window', 'res_model': 'garment.style.revision',
            'view_mode': 'tree,form', 'domain': [('style_id', '=', self.id)],
            'context': {'default_style_id': self.id},
        }

    def action_view_ecrs(self):
        self.ensure_one()
        return {
            'name': _('ECRs'), 'type': 'ir.actions.act_window', 'res_model': 'garment.ecr',
            'view_mode': 'tree,form', 'domain': [('style_id', '=', self.id)],
            'context': {'default_style_id': self.id},
        }
