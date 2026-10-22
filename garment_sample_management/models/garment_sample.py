# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentSample(models.Model):
    """Sample Master (SRS section 6) — garment.sample. Central record for the
    complete sample lifecycle: Buyer Request → Material Planning → Pattern →
    Cutting → Sewing → Finishing → QC → Submission → Buyer Review → Approved
    → Bulk Production."""
    _name = 'garment.sample'
    _description = 'Garment Sample'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'sample_number'

    sample_number = fields.Char(string='Sample Number', copy=False, readonly=True, default=lambda s: _('New'))
    style_id = fields.Many2one('garment.style', string='Style', required=True, tracking=True, index=True)
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True, index=True)
    brand = fields.Char(related='style_id.brand', string='Brand', store=True)
    season = fields.Char(related='style_id.season', string='Season', store=True)
    sample_type_id = fields.Many2one('garment.sample.type', string='Sample Type', required=True, tracking=True,
                                      index=True)
    style_category_id = fields.Many2one('garment.style.category', related='style_id.style_category_id',
                                         string='Product Category', store=True)
    order_reference = fields.Char(string='Order Reference',
                                   help='Free-text reference until this sample is linked from the Order '
                                        'Management module (kept free-text here to avoid a reverse module '
                                        'dependency, since garment_order_management already depends on this '
                                        'module).')
    techpack_id = fields.Many2one('garment.techpack', string='Tech Pack Reference',
                                   domain="[('style_id', '=', style_id)]")
    bom_id = fields.Many2one('garment.bom', string='BOM Reference', domain="[('style_id', '=', style_id)]")
    bom_reference = fields.Char(string='BOM Reference (Legacy Text)',
                                 help='Legacy free-text BOM reference, kept for records created before the '
                                      'BOM Reference link field was added. Prefer the BOM Reference field.')
    sample_request_id = fields.Many2one('garment.sample.request', string='Sample Request')
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Medium'), ('2', 'High'), ('3', 'Critical'),
    ], string='Priority', default='1', tracking=True)
    required_date = fields.Date(string='Required Date')
    submission_date = fields.Date(string='Submission Date')
    assigned_merchandiser_id = fields.Many2one('res.users', string='Assigned Merchandiser')
    sample_room_manager_id = fields.Many2one('res.users', string='Sample Room Manager')

    # Bangladesh garment process (SRS section 45)
    garment_process = fields.Selection([
        ('knit', 'Knitwear'), ('woven', 'Woven'), ('sweater', 'Sweater'),
    ], string='Garment Process', default='woven', tracking=True,
        help='Governs which typical sample flow applies: Knitwear (Proto>Fit>Size Set>PP>Shipment), '
             'Woven (Development>Fit>Sealed>Size Set>PP>Shipment) or Sweater (Yarn>Color>Knitting>Linking>Wash>PP).')
    shade_approval_status = fields.Selection([
        ('not_required', 'Not Required'), ('pending', 'Pending'),
        ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Shade Approval', default='not_required', tracking=True)
    wash_approval_status = fields.Selection([
        ('not_required', 'Not Required'), ('pending', 'Pending'),
        ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Wash Approval', default='not_required', tracking=True)
    sealed_sample = fields.Boolean(string='Sealed Sample')
    sealed_sample_reference = fields.Char(string='Sealed Sample Reference')

    status = fields.Selection([
        ('request_created', 'Sample Request Created'),
        ('techpack_review', 'Tech Pack Review'),
        ('material_planning', 'Material Planning'),
        ('pattern_development', 'Pattern Development'),
        ('cutting', 'Cutting'),
        ('sewing', 'Sample Sewing'),
        ('finishing', 'Finishing'),
        ('internal_qc', 'Internal Quality Check'),
        ('submitted', 'Sample Submission'),
        ('buyer_review', 'Buyer Review'),
        ('comments_received', 'Comments Received'),
        ('revision', 'Sample Revision'),
        ('approved', 'Approved'),
        ('bulk_production', 'Bulk Production'),
        ('rejected', 'Rejected'),
    ], string='Status', default='request_created', tracking=True, group_expand='_expand_states', index=True)

    # Buyer approval track (SRS section 36) — distinct from the internal production `status` above:
    # tracks only the buyer-facing decision (Submitted -> Buyer Review -> Approved / Commented / Rejected).
    approval_state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('buyer_review', 'Buyer Review'),
        ('approved', 'Approved'), ('commented', 'Commented'), ('rejected', 'Rejected'),
    ], string='Buyer Approval State', default='draft', tracking=True)

    is_locked = fields.Boolean(string='Locked (Approved)', default=False, copy=False,
                                help='Approved samples become locked (SRS section 39) — only the Sample '
                                     'Manager group may edit a locked sample.')

    # Pattern Development Integration (SRS section 13)
    pattern_id = fields.Many2one('garment.pattern', string='Pattern', domain="[('style_id', '=', style_id)]")
    pattern_created_date = fields.Date(string='Pattern Created Date')
    pattern_version = fields.Char(string='Pattern Version')
    pattern_maker_id = fields.Many2one('res.users', string='Pattern Maker')
    pattern_approval_status = fields.Selection([
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Pattern Approval Status', default='pending', tracking=True)

    # Compliance & Quality Integration (SRS section 46) — tracked here as free text/flags to avoid
    # taking on the full garment_quality/garment_compliance dependency chain for a data-tracking need.
    chemical_requirement = fields.Text(string='Chemical Requirement')
    wash_standard = fields.Char(string='Wash Standard')
    testing_requirement = fields.Text(string='Testing Requirement')
    buyer_compliance_notes = fields.Text(string='Buyer Compliance Notes')

    # Delay / analytics tracking (SRS sections 41-42)
    delay_reason = fields.Text(string='Delay Reason')
    delay_days = fields.Integer(string='Delay (Days)', compute='_compute_delay_days', store=True)
    approval_duration_days = fields.Integer(string='Approval Duration (Days)',
                                             compute='_compute_approval_duration', store=True)

    approved_image = fields.Binary(string='Approved Reference Image', attachment=True)
    developed_sample_image = fields.Binary(string='Developed Sample Image', attachment=True)

    activity_line_ids = fields.One2many('garment.sample.activity', 'sample_id', string='Development Plan')
    material_ids = fields.One2many('garment.sample.material', 'sample_id', string='Material Reservation')
    qc_ids = fields.One2many('garment.sample.qc', 'sample_id', string='Quality Checks')
    cost_ids = fields.One2many('garment.sample.cost', 'sample_id', string='Cost Sheets')
    approval_ids = fields.One2many('garment.sample.approval', 'sample_id', string='Approvals')
    comment_ids = fields.One2many('garment.sample.comment', 'sample_id', string='Buyer Comments')
    revision_ids = fields.One2many('garment.sample.revision', 'sample_id', string='Revisions')
    courier_ids = fields.One2many('garment.sample.courier', 'sample_id', string='Courier Shipments')

    material_count = fields.Integer(compute='_compute_counts')
    comment_count = fields.Integer(compute='_compute_counts')
    revision_count = fields.Integer(compute='_compute_counts')
    open_comment_count = fields.Integer(compute='_compute_counts')

    # AI Assist
    ai_image_comparison_note = fields.Text(string='AI Image Comparison', readonly=True)
    ai_measurement_note = fields.Text(string='AI Measurement Verification', readonly=True)
    ai_approval_prediction = fields.Float(string='AI Approval Probability (%)', readonly=True)
    ai_prediction_note = fields.Text(string='AI Prediction Notes', readonly=True)
    ai_last_run = fields.Datetime(string='AI Last Analyzed', readonly=True)
    ai_similarity_note = fields.Text(string='AI Similar Samples', readonly=True,
                                      help='AI Sample Similarity Search results (SRS section 33).')

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('sample_number_uniq', 'unique(sample_number, company_id)', 'Sample Number must be unique per company!'),
    ]

    @api.depends('material_ids', 'comment_ids', 'revision_ids', 'comment_ids.completion_status')
    def _compute_counts(self):
        for rec in self:
            rec.material_count = len(rec.material_ids)
            rec.comment_count = len(rec.comment_ids)
            rec.revision_count = len(rec.revision_ids)
            rec.open_comment_count = len(rec.comment_ids.filtered(lambda c: c.completion_status != 'completed'))

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    @api.depends('required_date', 'submission_date')
    def _compute_delay_days(self):
        for rec in self:
            if rec.required_date and rec.submission_date and rec.submission_date > rec.required_date:
                rec.delay_days = (rec.submission_date - rec.required_date).days
            else:
                rec.delay_days = 0

    @api.depends('submission_date', 'approval_ids.status', 'approval_ids.approval_date')
    def _compute_approval_duration(self):
        for rec in self:
            final_approvals = rec.approval_ids.filtered(
                lambda a: a.status == 'approved' and a.approval_date)
            if rec.submission_date and final_approvals:
                last_date = max(final_approvals.mapped('approval_date')).date()
                rec.approval_duration_days = (last_date - rec.submission_date).days
            else:
                rec.approval_duration_days = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sample_number', _('New')) == _('New'):
                vals['sample_number'] = self.env['ir.sequence'].next_by_code('garment.sample') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        # Record Rule (SRS section 39): "Approved samples become locked" — once locked, only the
        # Sample Manager group may change fields other than the small status-transition whitelist
        # that the workflow actions themselves need to keep writing (mirrors garment.bom's pattern).
        allowed_when_locked = {'status', 'approval_state', 'is_locked', 'submission_date',
                                'message_follower_ids', 'message_ids', 'activity_ids'}
        if not self.env.user.has_group('garment_sample_management.group_sample_manager'):
            for rec in self:
                if rec.is_locked and any(f not in allowed_when_locked for f in vals.keys()):
                    raise UserError(_('This sample is approved and locked. Only a Sample Manager can edit it.'))
        return super().write(vals)

    def unlink(self):
        # Record Rule (SRS section 39): "Deleted samples move to archive" — soft-delete instead of a
        # hard database delete so sample history is never lost.
        self.write({'active': False})
        return True

    def action_submit_to_buyer(self):
        self.write({
            'status': 'submitted',
            'submission_date': fields.Date.context_today(self),
            'approval_state': 'submitted',
        })
        self.message_post(body=_('Sample submitted to buyer.'))

    def action_mark_approved(self):
        self.write({'status': 'approved', 'approval_state': 'approved', 'is_locked': True})
        self.message_post(body=_('Sample approved by buyer.'))

    def action_mark_commented(self):
        self.write({'status': 'comments_received', 'approval_state': 'commented'})

    def action_mark_rejected(self):
        self.write({'status': 'rejected', 'approval_state': 'rejected'})
        self.message_post(body=_('Sample rejected by buyer.'))

    def action_transfer_to_bulk_production(self):
        self.write({'status': 'bulk_production'})
        self.message_post(body=_('Sample transferred to Bulk Production.'))

    def action_find_similar_samples(self):
        self.ensure_one()
        ai_engine = self.env['garment.ai.engine']
        similar, note = ai_engine.find_similar_samples(self)
        self.write({'ai_similarity_note': note})
        return {
            'name': _('Similar Samples'), 'type': 'ir.actions.act_window', 'res_model': 'garment.sample',
            'view_mode': 'tree,form', 'domain': [('id', 'in', similar.ids)],
        }

    @api.model
    def _cron_sample_notifications(self):
        """Sample Notification System (SRS section 30) — native Odoo Notification + email
        channel via mail activities/chatter. SMS / WhatsApp / Mobile Push are out of scope here
        (no gateway is configured in this module; Mobile Push already has a dedicated model in
        garment_mobile_platform — garment.mobile.push.notification — for that other module to use)."""
        tomorrow = fields.Date.context_today(self) + timedelta(days=1)

        # Merchandiser: "Fit sample deadline tomorrow"
        fit_due = self.search([
            ('required_date', '=', tomorrow), ('sample_type_id.code', '=', 'fit'),
            ('status', 'not in', ('approved', 'bulk_production', 'rejected')),
        ])
        for rec in fit_due:
            if rec.assigned_merchandiser_id:
                rec.activity_schedule('mail.mail_activity_data_todo',
                                       user_id=rec.assigned_merchandiser_id.id,
                                       summary=_('Fit sample deadline tomorrow'),
                                       note=_('Sample %s is due tomorrow.') % rec.sample_number)

        # Sample Room: "PP Sample production pending"
        pp_pending = self.search([
            ('sample_type_id.code', '=', 'pp'),
            ('status', 'in', ('material_planning', 'pattern_development', 'cutting', 'sewing', 'finishing')),
        ])
        for rec in pp_pending:
            if rec.sample_room_manager_id:
                rec.activity_schedule('mail.mail_activity_data_todo',
                                       user_id=rec.sample_room_manager_id.id,
                                       summary=_('PP Sample production pending'),
                                       note=_('PP Sample %s is still in production.') % rec.sample_number)

        # QA Team: "Sample inspection required"
        qc_needed = self.search([('status', '=', 'internal_qc')])
        qa_group = self.env.ref('garment_sample_management.group_sample_qa_manager', raise_if_not_found=False)
        if qa_group:
            for rec in qc_needed:
                for qa_user in qa_group.users:
                    rec.activity_schedule('mail.mail_activity_data_todo', user_id=qa_user.id,
                                           summary=_('Sample inspection required'),
                                           note=_('Sample %s is awaiting internal QC.') % rec.sample_number)

        # Management: "Buyer approval delayed"
        overdue = self.search([
            ('status', '=', 'buyer_review'),
            ('submission_date', '!=', False),
        ])
        manager_group = self.env.ref('garment_sample_management.group_sample_manager', raise_if_not_found=False)
        for rec in overdue:
            if rec.submission_date and (fields.Date.context_today(self) - rec.submission_date).days > 14:
                if manager_group:
                    for mgr in manager_group.users:
                        rec.activity_schedule('mail.mail_activity_data_todo', user_id=mgr.id,
                                               summary=_('Buyer approval delayed'),
                                               note=_('Sample %s has been awaiting buyer approval for over '
                                                       '14 days.') % rec.sample_number)

    def action_run_ai_analysis(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            image_note = ai_engine.compare_sample_images(rec)
            measurement_note = ai_engine.verify_sample_measurements(rec)
            probability, prediction_note = ai_engine.predict_sample_approval(rec)
            rec.write({
                'ai_image_comparison_note': image_note,
                'ai_measurement_note': measurement_note,
                'ai_approval_prediction': probability,
                'ai_prediction_note': prediction_note,
                'ai_last_run': fields.Datetime.now(),
            })
        return True

    def action_view_materials(self):
        self.ensure_one()
        return {'name': _('Materials'), 'type': 'ir.actions.act_window', 'res_model': 'garment.sample.material',
                'view_mode': 'tree,form', 'domain': [('sample_id', '=', self.id)],
                'context': {'default_sample_id': self.id}}

    def action_view_comments(self):
        self.ensure_one()
        return {'name': _('Buyer Comments'), 'type': 'ir.actions.act_window', 'res_model': 'garment.sample.comment',
                'view_mode': 'tree,form', 'domain': [('sample_id', '=', self.id)],
                'context': {'default_sample_id': self.id}}

    def action_view_revisions(self):
        self.ensure_one()
        return {'name': _('Revisions'), 'type': 'ir.actions.act_window', 'res_model': 'garment.sample.revision',
                'view_mode': 'tree,form', 'domain': [('sample_id', '=', self.id)],
                'context': {'default_sample_id': self.id}}
