# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import UserError

# Product Classification (SRS section 7) — Knit / Woven / Sweater / Other
GARMENT_TYPE_SELECTION = [
    # Knit
    ('tshirt', 'T-Shirt'), ('polo', 'Polo'), ('sweatshirt', 'Sweatshirt'),
    ('hoodie', 'Hoodie'), ('leggings', 'Leggings'), ('joggers', 'Joggers'),
    # Woven
    ('shirt', 'Shirt'), ('trouser', 'Trouser'), ('jacket', 'Jacket'),
    ('dress', 'Dress'), ('skirt', 'Skirt'),
    # Sweater
    ('pullover', 'Pullover'), ('cardigan', 'Cardigan'), ('vest', 'Vest'),
    # Other
    ('denim', 'Denim'), ('outerwear', 'Outerwear'), ('uniform', 'Uniform'), ('sportswear', 'Sportswear'),
]


class GarmentTechpack(models.Model):
    """Tech Pack Master (SRS section 6-7) — garment.techpack.
    Single technical source of truth shared between buyer, merchandising,
    sampling, production, quality and engineering teams."""
    _name = 'garment.techpack'
    _description = 'Garment Tech Pack'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    # ------------------------------------------------------------------
    # Basic Information
    # ------------------------------------------------------------------
    techpack_number = fields.Char(string='Tech Pack Number', copy=False, readonly=True, default=lambda s: _('New'))
    name = fields.Char(string='Tech Pack Name', required=True, tracking=True)
    version = fields.Char(string='Current Version', default='1.0', tracking=True)
    style_id = fields.Many2one('garment.style', string='Style', required=True, tracking=True, ondelete='cascade')
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', related='style_id.buyer_id', store=True, readonly=True)
    brand = fields.Char(string='Brand', related='style_id.brand', store=True, readonly=False)
    style_number = fields.Char(related='style_id.style_number', string='Style Number', store=True)
    buyer_style_number = fields.Char(related='style_id.buyer_style_number', string='Buyer Style Number')
    factory_style_number = fields.Char(related='style_id.factory_style_number', string='Factory Style Number')
    style_category_id = fields.Many2one('garment.style.category', string='Product Category',
                                         related='style_id.style_category_id', store=True)
    product_type = fields.Char(string='Product Type')
    season = fields.Char(related='style_id.season', string='Season', store=True)
    collection = fields.Char(related='style_id.collection', string='Collection', store=True)
    gender = fields.Selection(related='style_id.gender', string='Gender', store=True)
    age_group = fields.Selection(related='style_id.age_group', string='Age Group', store=True)
    department = fields.Char(string='Department')
    assigned_merchandiser_id = fields.Many2one('res.users', string='Assigned Merchandiser', tracking=True)
    technical_owner_id = fields.Many2one('res.users', string='Technical Owner', tracking=True)

    # ------------------------------------------------------------------
    # Product Information
    # ------------------------------------------------------------------
    product_name = fields.Char(string='Product Name')
    product_description = fields.Text(string='Product Description')
    fabric_category = fields.Selection([
        ('knit', 'Knit'), ('woven', 'Woven'), ('sweater', 'Sweater'), ('other', 'Other'),
    ], string='Fabric Category', tracking=True, help='Product Classification top-level category (SRS section 7).')
    garment_type = fields.Selection(GARMENT_TYPE_SELECTION, string='Garment Type', tracking=True)
    construction_method = fields.Char(string='Construction Method')
    fit_type = fields.Char(string='Fit Type')
    usage_purpose = fields.Char(string='Usage Purpose')
    target_market = fields.Char(string='Target Market')
    country_id = fields.Many2one('res.country', string='Country')

    # Style image, pulled through for Kanban cards (SRS section 38)
    style_image = fields.Binary(related='style_id.front_view_image', string='Style Image', readonly=True)

    # Bangladesh Factory Requirements (SRS section 46) — multiple factories/units/lines
    factory = fields.Char(string='Factory')
    production_unit = fields.Char(string='Production Unit')

    # ------------------------------------------------------------------
    # Status / Lifecycle (SRS section 5)
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('registration', 'Tech Pack Registration'),
        ('technical_review', 'Technical Review'),
        ('data_entry', 'Data Entry'),
        ('internal_verification', 'Internal Verification'),
        ('sample_development', 'Sample Development'),
        ('buyer_review', 'Buyer Review'),
        ('approved', 'Approved'),
        ('production_release', 'Production Release'),
        ('archived', 'Archived'),
    ], string='Status', default='registration', tracking=True, group_expand='_expand_states')
    is_locked = fields.Boolean(string='Locked (Approved)', default=False, copy=False)
    approval_date = fields.Date(string='Approval Date', readonly=True)

    # Production Release Certificate (SRS section 23)
    production_release_date = fields.Date(string='Release Date', readonly=True, copy=False)
    released_by_id = fields.Many2one('res.users', string='Released By', readonly=True, copy=False)

    # Calendar View deadlines (SRS section 39)
    review_deadline = fields.Date(string='Tech Pack Review Deadline', tracking=True)
    buyer_submission_deadline = fields.Date(string='Buyer Submission Date', tracking=True)
    approval_deadline = fields.Date(string='Approval Deadline', tracking=True)

    # Development Timeline groundwork for a Gantt-capable view (SRS section 40).
    # Odoo Community 17 has no built-in Gantt widget (web_gantt is Enterprise-only);
    # these dates are modeled now so an OCA/Enterprise Gantt view can plug in later.
    planned_start_date = fields.Date(string='Development Start Date')
    planned_end_date = fields.Date(string='Development End Date')
    is_delayed = fields.Boolean(string='Delayed', compute='_compute_is_delayed', store=True)
    delay_days = fields.Integer(string='Delay (Days)', compute='_compute_is_delayed', store=True)

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------
    tech_spec_ids = fields.One2many('garment.tech.spec', 'techpack_id', string='Technical Specifications')
    construction_detail_ids = fields.One2many('garment.construction.detail', 'techpack_id', string='Construction Details')
    artwork_ids = fields.One2many('garment.artwork', 'techpack_id', string='Artwork')
    label_spec_ids = fields.One2many('garment.label.spec', 'techpack_id', string='Labels')
    packaging_spec_ids = fields.One2many('garment.packaging.spec', 'techpack_id', string='Packaging Specifications')
    measurement_sheet_ids = fields.One2many('garment.measurement.sheet', 'techpack_id', string='Measurement Sheets')
    version_ids = fields.One2many('garment.techpack.version', 'techpack_id', string='Versions')
    review_ids = fields.One2many('garment.tech.review', 'techpack_id', string='Technical Reviews')
    approval_ids = fields.One2many('garment.tech.approval', 'techpack_id', string='Approvals')
    change_ids = fields.One2many('garment.tech.change', 'techpack_id', string='Change Requests')
    attachment_ids = fields.One2many('garment.tech.attachment', 'techpack_id', string='Attachments')
    task_ids = fields.One2many('garment.techpack.task', 'techpack_id', string='Tasks')

    artwork_count = fields.Integer(compute='_compute_counts', store=True)
    version_count = fields.Integer(compute='_compute_counts', store=True)
    change_count = fields.Integer(compute='_compute_counts', store=True)
    task_count = fields.Integer(compute='_compute_counts', store=True)
    open_task_count = fields.Integer(compute='_compute_counts', store=True)
    # BOM Integration (SRS section 16). garment.bom (garment_bom_management) already
    # carries a Many2one back to garment.techpack — adding a hard 'depends' the other
    # way would create a circular module dependency, so the link is read defensively
    # through the registry instead of a stored relational field.
    bom_count = fields.Integer(compute='_compute_bom_count')

    # ------------------------------------------------------------------
    # AI Assist
    # ------------------------------------------------------------------
    ai_missing_fields_note = fields.Text(string='AI Missing Data Report', readonly=True)
    ai_validation_note = fields.Text(string='AI Validation Report', readonly=True)
    ai_similar_techpack_ids = fields.Many2many(
        'garment.techpack', 'garment_techpack_similarity_rel', 'techpack_id', 'similar_techpack_id',
        string='AI Suggested Similar Tech Packs', readonly=True)
    ai_last_run = fields.Datetime(string='AI Last Analyzed', readonly=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('techpack_number_uniq', 'unique(techpack_number, company_id)', 'Tech Pack Number must be unique per company!'),
    ]

    @api.depends('artwork_ids', 'version_ids', 'change_ids', 'task_ids', 'task_ids.status')
    def _compute_counts(self):
        for rec in self:
            rec.artwork_count = len(rec.artwork_ids)
            rec.version_count = len(rec.version_ids)
            rec.change_count = len(rec.change_ids)
            rec.task_count = len(rec.task_ids)
            rec.open_task_count = len(rec.task_ids.filtered(lambda t: t.status not in ('done', 'cancelled')))

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['state'].selection]

    def _compute_bom_count(self):
        Bom = self.env['garment.bom'] if 'garment.bom' in self.env.registry else None
        for rec in self:
            rec.bom_count = Bom.search_count([('techpack_id', '=', rec.id)]) if Bom is not None and rec.id else 0

    @api.depends('planned_end_date', 'state')
    def _compute_is_delayed(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.planned_end_date and rec.state not in ('approved', 'production_release', 'archived') \
                    and rec.planned_end_date < today:
                rec.is_delayed = True
                rec.delay_days = (today - rec.planned_end_date).days
            else:
                rec.is_delayed = False
                rec.delay_days = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('techpack_number', _('New')) == _('New'):
                vals['techpack_number'] = self.env['ir.sequence'].next_by_code('garment.techpack') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        for rec in self:
            if rec.is_locked and not self.env.user.has_group('garment_techpack.group_techpack_technical_manager') \
                    and any(f not in ('state', 'is_locked', 'approval_date') for f in vals.keys()):
                raise UserError(_(
                    'Tech Pack "%s" is locked (Approved). Raise a Tech Change Request to modify it.') % rec.name)
        return super().write(vals)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_lock(self):
        self.write({'is_locked': True, 'approval_date': fields.Date.context_today(self)})

    def action_unlock(self):
        self.write({'is_locked': False})

    def action_check_production_release(self):
        """Production Release Control (SRS section 23) — verify every
        prerequisite is approved before allowing production release:
        Tech Pack / BOM / Measurement / Sample / Artwork / Packaging /
        Buyer Approval."""
        self.ensure_one()
        Bom = self.env['garment.bom'] if 'garment.bom' in self.env.registry else None
        Sample = self.env['garment.sample'] if 'garment.sample' in self.env.registry else None
        bom_ok = True
        if Bom is not None:
            boms = Bom.search([('techpack_id', '=', self.id)])
            bom_ok = bool(boms) and all(b.status in ('production_approved', 'active') for b in boms)
        sample_ok = True
        if Sample is not None:
            samples = Sample.search([('techpack_id', '=', self.id)])
            sample_ok = bool(samples) and all(s.status in ('approved', 'bulk_production') for s in samples)
        buyer_approved = any(
            a.approval_stage == 'buyer_approved' and a.status == 'approved' for a in self.approval_ids)
        checks = {
            'Tech Pack Approved': self.state in ('approved', 'production_release'),
            'BOM Approved': bom_ok,
            'Measurement Approved': bool(self.measurement_sheet_ids.filtered(lambda m: m.status == 'approved')),
            'Sample Approved': sample_ok,
            'Artwork Approved': not self.artwork_ids or all(a.approval_status == 'approved' for a in self.artwork_ids),
            'Packaging Approved': not self.packaging_spec_ids or all(
                p.approval_status == 'approved' for p in self.packaging_spec_ids),
            'Buyer Approval Completed': buyer_approved or self.state == 'production_release',
        }
        failed = [name for name, ok in checks.items() if not ok]
        if failed:
            raise UserError(_('Cannot release to production. Pending: %s') % ', '.join(failed))
        self.write({
            'state': 'production_release',
            'production_release_date': fields.Date.context_today(self),
            'released_by_id': self.env.user.id,
        })
        return True

    def action_view_boms(self):
        """Open the Bills of Material linked to this Tech Pack (SRS section 16
        BOM Integration). Requires garment_bom_management to be installed."""
        self.ensure_one()
        if 'garment.bom' not in self.env.registry:
            raise UserError(_('The BOM Management module is not installed.'))
        return {'name': _('Bills of Material'), 'type': 'ir.actions.act_window', 'res_model': 'garment.bom',
                'view_mode': 'tree,form', 'domain': [('techpack_id', '=', self.id)],
                'context': {'default_techpack_id': self.id, 'default_style_id': self.style_id.id}}

    def action_generate_approval_stages(self):
        """Auto-create the full internal + buyer Approval Workflow sequence
        (SRS section 21) so each stage can be tracked and signed off."""
        Approval = self.env['garment.tech.approval']
        stages = ['merchandiser_review', 'technical_manager', 'quality_review', 'production_review',
                  'buyer_submission', 'buyer_review', 'buyer_approved']
        existing = set(self.approval_ids.mapped('approval_stage'))
        for idx, stage in enumerate(stages):
            if stage not in existing:
                Approval.create({'techpack_id': self.id, 'sequence': (idx + 1) * 10, 'approval_stage': stage})
        return True

    def action_run_ai_analysis(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            missing = ai_engine.detect_missing_techpack_fields(rec)
            validation = ai_engine.validate_techpack_specification(rec)
            similar, _insight = ai_engine.find_similar_techpacks(rec)
            rec.write({
                'ai_missing_fields_note': missing,
                'ai_validation_note': validation,
                'ai_similar_techpack_ids': [(6, 0, similar.ids)],
                'ai_last_run': fields.Datetime.now(),
            })
        return True

    def action_view_artworks(self):
        self.ensure_one()
        return {'name': _('Artwork'), 'type': 'ir.actions.act_window', 'res_model': 'garment.artwork',
                'view_mode': 'tree,form', 'domain': [('techpack_id', '=', self.id)],
                'context': {'default_techpack_id': self.id}}

    def action_view_versions(self):
        self.ensure_one()
        return {'name': _('Versions'), 'type': 'ir.actions.act_window', 'res_model': 'garment.techpack.version',
                'view_mode': 'tree,form', 'domain': [('techpack_id', '=', self.id)],
                'context': {'default_techpack_id': self.id}}

    def action_view_changes(self):
        self.ensure_one()
        return {'name': _('Change Requests'), 'type': 'ir.actions.act_window', 'res_model': 'garment.tech.change',
                'view_mode': 'tree,form', 'domain': [('techpack_id', '=', self.id)],
                'context': {'default_techpack_id': self.id}}

    def action_view_tasks(self):
        self.ensure_one()
        return {'name': _('Tasks'), 'type': 'ir.actions.act_window', 'res_model': 'garment.techpack.task',
                'view_mode': 'tree,form', 'domain': [('techpack_id', '=', self.id)],
                'context': {'default_techpack_id': self.id}}

    def action_open_version_compare(self):
        """Version Comparison (SRS section 19) — open the compare wizard
        pre-filled with this Tech Pack's two most recent versions."""
        self.ensure_one()
        versions = self.version_ids.sorted(key=lambda v: v.create_date, reverse=True)
        vals = {'default_techpack_id': self.id}
        if len(versions) >= 2:
            vals['default_version_to_id'] = versions[0].id
            vals['default_version_from_id'] = versions[1].id
        return {
            'name': _('Compare Tech Pack Versions'), 'type': 'ir.actions.act_window',
            'res_model': 'garment.techpack.version.compare', 'view_mode': 'form', 'target': 'new',
            'context': vals,
        }

    def action_generate_standard_tasks(self):
        """Auto-create Technical / Sampling / Production tasks (SRS section 26)."""
        Task = self.env['garment.techpack.task']
        templates = [
            ('Review Tech Pack', 'technical'), ('Prepare Measurement Chart', 'technical'),
            ('Verify Construction', 'technical'), ('Prepare BOM', 'technical'),
            ('Create Pattern', 'sampling'), ('Cut Sample', 'sampling'),
            ('Sew Sample', 'sampling'), ('Finish Sample', 'sampling'), ('Send For Approval', 'sampling'),
            ('Review Specification', 'production'), ('Prepare Line Setup', 'production'),
            ('Train Operators', 'production'),
        ]
        for name, department in templates:
            Task.create({'techpack_id': self.id, 'name': name, 'department': department})
        return True
