from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_round


class HrKpi(models.Model):
    _name = "hr.kpi"
    _description = "Human Resource Key Performance Indicators"

    # work section

    # 5.a Where would you like to be in 1-3 years (max 300 chars)
    five_a_career_1_3yrs = fields.Text(
        string=_("5.a Where would you like to be in 1-3 years"),
        help=_("Describe where you'd like to be in 1-3 years (max 300 characters)."),
        placeholder="e.g. Senior Software Engineer, Team Lead, etc.",
    )

    # 5.b What support will you require from the organization
    five_b_org_support = fields.Text(
        string=_("5.b What support will you require from the organization"),
        help=_("Describe the support you need from the organisation to fulfil your aspiration."),
        placeholder=_("e.g. Training, Mentorship, Resources, etc."),
    )

    # 5.c Expected Job Position in 1-3 years (selection)
    five_c_expected_job = fields.Selection(
        selection=[
            ("same", "Same as today"),
            ("other_same_level", "Other position at same level"),
            ("higher", "Higher level position"),
            ("other", "Others (please specify)"),
        ],
        string=_("5.c Expected Job Position in 1-3 years"),
        default="same",
        required=True,
    )

    # please_specify for 5.c (text) — stored separately
    five_c_expected_job_specify = fields.Text(
        string=_("If 'Others', please specify"),
        help=_("Specify the expected job/title when 'Others (please specify)' is selected."),
        placeholder=_("e.g. Senior Software Engineer, Team Lead, etc."),
    )

    five_d_international_mobility = fields.Selection(
        selection=[("yes", "Yes"), ("no", "No")],
        string=_("5.d International Mobility — Are you willing to be relocated to another country?"),
        required=True,
        default="no",
    )
    
    @api.constrains("five_c_expected_job", "five_c_expected_job_specify")
    def _check_five_c_specify_if_other(self):
        for rec in self:
            if rec.five_c_expected_job == "other" and not rec.five_c_expected_job_specify:
                raise ValidationError(_("Please specify the expected job when you choose 'Others'."))

    # work section end
    
    
    # Default Values
    DEFAULT_EVALUATION_ROWS = [
        ("2A", "2A. Performance Rating from Section 1", 0.0),
        ("2B", "2B. Strategic Thinking", 0.0),
        ("2C", "2C. Business Acumen", 0.0),
        ("2D", "2D. Results Achievement", 0.0),
        ("2E", "2E. Coalition Building", 0.0),
        ("2F", "2F. Customer Orientation", 0.0),
        ("2G", "2G. People Management & Development", 0.0),
        ("2H", "2H. Personal Attributes", 0.0),
    ]

    # normal fields
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_review", "In Review"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        default="draft",
        index=True,
        tracking=True,
    )
    name = fields.Char(
        string="KPI Reference",
        required=True,
        copy=False,
        help="Human-readable reference, e.g. KPI-2025-EMP001",
    )
    period_start = fields.Date(string="Period Start", required=True)
    period_end = fields.Date(string="Period End", required=True)
    staff_id = fields.Char(
        string="Staff ID", related="employee_id.barcode", readonly=True, store=True
    )
    supervisor_position = fields.Char(
        string="Supervisor Position",
        related="supervisor_id.job_id.name",
        readonly=True,
        store=True,
        help="Job/position of the supervisor (related to hr.employee.job_id).",
    )
    next_level_supervisor_position = fields.Char(
        string="Next Level Supervisor Position",
        related="next_level_supervisor_id.job_id.name",
        readonly=True,
        store=True,
        help="Job/position of the next level supervisor.",
    )
    notes = fields.Text(string="Notes")

    # Many2one fields
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True)
    supervisor_id = fields.Many2one(
        "hr.employee",
        string="Supervisor",
        help="Direct supervisor / manager for the employee.",
    )
    next_level_supervisor_id = fields.Many2one(
        "hr.employee",
        string="Next Level Supervisor",
        help="Supervisor of the supervisor (one level up).",
    )
    job_id = fields.Many2one(
        "hr.job",
        string="Job Position",
        related="employee_id.job_id",
        readonly=True,
        store=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        related="employee_id.department_id",
        readonly=False,
    )

    # One2many fields
    corporate_performance_ids = fields.One2many(
        "hr.kpi.corporate.performance",
        "kpi_id",
        string="Corporate KPI Lines",
        copy=True,
    )
    individual_performance_ids = fields.One2many(
        "hr.kpi.individual.performance",
        "kpi_id",
        string="Individual KPI Lines",
        copy=True,
    )
    # development_plan_ids = fields.One2many(
    #     "hr.kpi.development.plan", "kpi_id", string="Development Plans", copy=True
    # )

    evaluation_line_ids = fields.One2many(
        "hr.kpi.consolidated.performance.rating",
        "kpi_id",
        string="Behaviour / Competency Lines",
        copy=True,
    )

    development_plan_ids = fields.One2many(
        "hr.kpi.development.plan",
        "kpi_id",
        string="Development Plans",
        copy=True,
    )

    # Helper Functions
    @api.model
    def _map_weighted_total_to_performance_rating(self, total):
        """
        following the provided Excel formula from corporate.
        =   IF(Q30>=4.75,5,
            IF(Q30>=4.25,4.5,
            IF(Q30>=3.75,4,
            IF(Q30>=3.25,3.5,
            IF(Q30>=3,3,
            IF(Q30<3,Q30,"Error!"))))))

        and also

        following the provided Excel formula from individual.
        =	IF(R18>=4.75,5,
            IF(R18>=4.25,4.5,
            IF(R18>=3.75,4,
            IF(R18>=3.25,3.5,
            IF(R18>=3,3,
            IF(R18<3,R18,"Error!"))))))

        following is the provided excel fomula.
        =	IF(E28>=4.75,5,
            IF(E28>=4.25,4.5,
            IF(E28>=3.75,4,
            IF(E28>=3.25,3.5,
            IF(E28>=3,3,
            IF(E28<3,E28,"Error!"))))))

        """
        try:
            t = float(total)
        except (TypeError, ValueError):
            return 0.0

        if t >= 4.75:
            return 5.0
        if t >= 4.25:
            return 4.5
        if t >= 3.75:
            return 4.0
        if t >= 3.25:
            return 3.5
        if t >= 3.0:
            return 3.0
        return float_round(t, precision_digits=2)

    def _sync_individual_performance_to_2a(self):
        for rec in self:
            ind_perf = rec.individual_performance_score_after_alignment or 0.0
            line_2a = rec.evaluation_line_ids.filtered(lambda l: l.code == "2A")
            if line_2a:
                line_2a.write({"rating": ind_perf})
            else:
                rec.write(
                    {
                        "evaluation_line_ids": [
                            (
                                0,
                                0,
                                {
                                    "code": "2A",
                                    "evaluation_area": "2A. Performance Rating from Section 1",
                                    "rating": ind_perf,
                                    "weight": 0.0,
                                    "weighted_rating": 0.0,
                                },
                            )
                        ]
                    }
                )

    # computed fields =====================================================================
    # Corporate
    total_weighted_achivement_incentive_payout = fields.Float(
        string="Total Weighted Achievement (Incentive Payout)",
        compute="_compute_total_weighted_achivement_incentive_payout",
        store=True,
        help="Sum of all corporate weighted_achivement_incentive_payout (Q30).",
    )

    total_weighted_achivement_performace_rating = fields.Float(
        string="Total Weighted Achievement (Performance Rating)",
        compute="_compute_total_weighted_achivement_performace_rating",
        store=True,
        help="Sum of all corporate  weighted_achivement_performace_rating.",
    )

    mapped_weighted_achievement_incentive_payout = fields.Float(
        string="Rounded Weighted Achievement (Incentive Payout)",
        compute="_compute_mapped_weighted_achievement_incentive_payout",
        store=True,
        help=(
            "Mapped performance rating based on total weighted achievement (Q30). "
            'Excel logic: =IF(Q30>=4.75,5,IF(Q30>=4.25,4.5,IF(Q30>=3.75,4,IF(Q30>=3.25,3.5,IF(Q30>=3,3,IF(Q30<3,Q30,"Error!"))))))'
        ),
    )

    # Individual
    total_weighted_achivement_incentive_payout_individuals = fields.Float(
        string="Total Weighted Achievement (Incentive Payout) - Individuals",
        compute="_compute_total_weighted_achivement_incentive_payout_individuals",
        store=True,
        help="Sum of all individual weighted_achivement_incentive_payout (from hr.kpi.individual.performance).",
    )

    total_weighted_achivement_performace_rating_individuals = fields.Float(
        string="Total Weighted Achievement (Performance Rating) - Individuals",
        compute="_compute_total_weighted_achivement_performace_rating_individuals",
        store=True,
        help="Sum of all individual weighted_achivement_performace_rating (from hr.kpi.individual.performance).",
    )

    mapped_weighted_achievement_incentive_payout_individuals = fields.Float(
        string="Mapped Weighted Achievement (Incentive Payout) - Individuals",
        compute="_compute_mapped_weighted_achievement_incentive_payout_individuals",
        store=True,
        help=(
            "Mapped performance rating based on total weighted achievement of individuals.\n"
            'Excel logic: =IF(R18>=4.75,5,IF(R18>=4.25,4.5,IF(R18>=3.75,4,IF(R18>=3.25,3.5,IF(R18>=3,3,IF(R18<3,R18,"Error!"))))))\n'
            "Where R18 = Total Weighted Achievement Incentive Payout (Of Individuals)."
        ),
    )

    # Additional

    final_individual_performance_rating = fields.Float(
        string="Final Individual Performance Rating",
        compute="_compute_final_rating",
        store=True,
    )

    # Total
    individual_performance_score_after_alignment = fields.Float(
        string="Individual Performance Score (Aligned with Company)",
        compute="_compute_individual_performance_score_after_alignment",
        store=True,
        help=(
            "Sum of total_weighted_achivement_performace_rating_individuals "
            "and total_weighted_achivement_performace_rating."
        ),
    )

    @api.depends(
        "corporate_performance_ids",
        "corporate_performance_ids.weighted_achivement_incentive_payout",
    )
    def _compute_total_weighted_achivement_incentive_payout(self):
        for rec in self:
            total = 0.0
            for line in rec.corporate_performance_ids:
                total += line.weighted_achivement_incentive_payout or 0.0
            rec.total_weighted_achivement_incentive_payout = float_round(
                total, precision_digits=2
            )

    @api.depends(
        "corporate_performance_ids",
        "corporate_performance_ids.weighted_achivement_performace_rating",
    )
    def _compute_total_weighted_achivement_performace_rating(self):
        for rec in self:
            total = 0.0
            for line in rec.corporate_performance_ids:
                total += line.weighted_achivement_performace_rating or 0.0
            rec.total_weighted_achivement_performace_rating = float_round(
                total, precision_digits=2
            )

    @api.depends("total_weighted_achivement_incentive_payout")
    def _compute_mapped_weighted_achievement_incentive_payout(self):
        for rec in self:
            rec.mapped_weighted_achievement_incentive_payout = (
                self._map_weighted_total_to_performance_rating(
                    rec.total_weighted_achivement_incentive_payout
                )
            )

    # Individual
    @api.depends(
        "individual_performance_ids",
        "individual_performance_ids.weighted_achivement_incentive_payout",
    )
    def _compute_total_weighted_achivement_incentive_payout_individuals(self):
        for rec in self:
            total = 0.0
            for line in rec.individual_performance_ids:
                total += line.weighted_achivement_incentive_payout or 0.0
            rec.total_weighted_achivement_incentive_payout_individuals = float_round(
                total, precision_digits=2
            )

    @api.depends(
        "individual_performance_ids",
        "individual_performance_ids.weighted_achivement_performace_rating",
    )
    def _compute_total_weighted_achivement_performace_rating_individuals(self):
        for rec in self:
            total = 0.0
            for line in rec.individual_performance_ids:
                total += line.weighted_achivement_performace_rating or 0.0
            rec.total_weighted_achivement_performace_rating_individuals = float_round(
                total, precision_digits=2
            )

    @api.depends("total_weighted_achivement_incentive_payout_individuals")
    def _compute_mapped_weighted_achievement_incentive_payout_individuals(self):
        for rec in self:
            rec.mapped_weighted_achievement_incentive_payout_individuals = (
                self._map_weighted_total_to_performance_rating(
                    rec.total_weighted_achivement_incentive_payout_individuals
                )
            )

    @api.depends(
        "total_weighted_achivement_performace_rating_individuals",
        "total_weighted_achivement_performace_rating",
    )
    def _compute_individual_performance_score_after_alignment(self):
        for rec in self:
            indiv = rec.total_weighted_achivement_performace_rating_individuals or 0.0
            corp = rec.total_weighted_achivement_performace_rating or 0.0
            rec.individual_performance_score_after_alignment = float_round(
                (indiv + corp), precision_digits=2
            )

    @api.depends("evaluation_line_ids", "evaluation_line_ids.weighted_rating")
    def _compute_final_rating(self):
        for rec in self:
            total = 0.0
            for line in rec.evaluation_line_ids:
                total += line.weighted_rating or 0.0
            rec.final_individual_performance_rating = (
                rec._map_weighted_total_to_performance_rating(total)
            )

    # Onchange methods =====================================================================
    @api.onchange("employee_id")
    def _onchange_employee_supervisors(self):
        for rec in self:
            if not rec.employee_id:
                continue
            emp_manager = getattr(rec.employee_id, "parent_id", False)
            if emp_manager and not rec.supervisor_id:
                rec.supervisor_id = emp_manager
            sup = rec.supervisor_id or emp_manager
            next_manager = getattr(sup, "parent_id", False) if sup else False
            if next_manager and not rec.next_level_supervisor_id:
                rec.next_level_supervisor_id = next_manager

    @api.onchange("individual_performance_score_after_alignment")
    def _onchange_individual_performance_score_after_alignment(self):
        for rec in self:
            if not rec.evaluation_line_ids:
                continue
            ind_perf = rec.individual_performance_score_after_alignment or 0.0
            line_2a = rec.evaluation_line_ids.filtered(lambda l: l.code == "2A")
            print("individual perf", ind_perf, "line 2a", line_2a)
            print("evaluation_line_ids", rec.evaluation_line_ids)
            if line_2a:
                for line in line_2a:
                    line.rating = ind_perf

    # Constraints
    @api.constrains("period_start", "period_end")
    def _check_period(self):
        for rec in self:
            if (
                rec.period_start
                and rec.period_end
                and rec.period_start > rec.period_end
            ):
                raise ValidationError(_("Period start must be before period end."))

    # Super methods
    @api.model
    def create(self, vals):
        # sequence name
        if not vals.get("name") or vals.get("name") in ("/", False):
            seq = self.env["ir.sequence"].next_by_code("hr.kpi") or "/"
            vals["name"] = seq

        # populate default evaluation lines
        if "evaluation_line_ids" not in vals or not vals.get("evaluation_line_ids"):
            ind_perf = vals.get("individual_performance_score_after_alignment", 0.0)
            lines = []
            for code, label, weight in self.DEFAULT_EVALUATION_ROWS:
                rating = ind_perf if code == "2A" else 0.0
                lines.append(
                    (
                        0,
                        0,
                        {
                            "code": code,
                            "evaluation_area": label,
                            "rating": rating,
                            "weight": weight,
                            "weighted_rating": 0.0,
                        },
                    )
                )
            vals["evaluation_line_ids"] = lines

        rec = super(HrKpi, self).create(vals)

        if vals.get("individual_performance_score_after_alignment") is not None:
            rec._sync_individual_performance_to_2a()

        rec._onchange_individual_performance_score_after_alignment()
        return rec

    def write(self, vals):
        res = super(HrKpi, self).write(vals)
        if "individual_performance_score_after_alignment" in vals:
            self._sync_individual_performance_to_2a()
        self._onchange_individual_performance_score_after_alignment()

        return res

    # Button methods
    def action_submit_for_review(self):
        for rec in self:
            if rec.state != "draft":
                continue
            rec.write({"state": "in_review"})

    def action_approve(self):
        for rec in self:
            if rec.state not in ("in_review", "draft"):
                continue
            rec.write({"state": "approved"})

    def action_reject(self, reason=None):
        for rec in self:
            if rec.state not in ("in_review", "draft"):
                continue
            rec.write({"state": "rejected"})

    def action_set_draft(self):
        for rec in self:
            rec.write({"state": "draft"})


class HrKpiCorporatePerformance(models.Model):
    _name = "hr.kpi.corporate.performance"
    _description = "Corporate Key Performance Indicators"

    # normal fields
    kpi_name_description = fields.Text(
        string="Description",
        related="kpi_name_id.description",
        readonly=True,
        store=True,
    )
    kpi_name_weight = fields.Float(string="Weightage", help="Weight for incentive")
    kpi_name_timeframe = fields.Char(string="Timeframe")
    target_l1 = fields.Float(string="L-1")
    target_l2 = fields.Float(string="L-2")
    target_l3 = fields.Float(string="L-3")
    target_l4 = fields.Float(string="L-4")
    target_l5 = fields.Float(string="L-5")
    achieved_value = fields.Float(string="Achieved Value", store=True)
    kpi_weightage_incentive_payout = fields.Float(
        string="KPI Weightage for Incentive Payout",
        help="Weight for incentive payout",
    )

    # many2one fields
    kpi_id = fields.Many2one(
        "hr.kpi", string="KPI Record", required=True, ondelete="cascade"
    )
    kpi_type_id = fields.Many2one("hr.kpi.type", string="Type")
    kpi_name_id = fields.Many2one(
        "hr.kpi.type.line",
        string="Name",
        domain="[('kpi_type_id','=', kpi_type_id)]",
        help="Pointer to configured KPI name",
    )
    # one2many fields

    # computed fields
    achieved_level = fields.Float(
        string="Achieved Level",
        compute="_compute_achieved_level",
        store=True,
        readonly=True,
    )

    kpi_weightage_performace_rating = fields.Float(
        string="KPI Weightage for Performance Rating",
        compute="_compute_kpi_weightage_performace_rating",
        readonly=True,
        store=True,
        help="Weight for performance rating",
    )

    weighted_achivement_incentive_payout = fields.Float(
        string="Weighted Achievement for Incentive Payout",
        compute="_compute_weighted_achivement_incentive_payout",
        store=True,
        help="Weighted achievement for incentive payout (achieved_level * kpi_weightage_incentive_payout)",
    )

    weighted_achivement_performace_rating = fields.Float(
        string="Weighted Achievement for Performance Rating",
        compute="_compute_weighted_achivement_performace_rating",
        store=True,
        help="Weighted achievement for performance rating (achieved_level * kpi_weightage_performace_rating)",
    )

    @api.depends("target_l2", "target_l3", "target_l4", "target_l5", "achieved_value")
    def _compute_achieved_level(self):
        """
        Formula to calculate achieved level based on targets:
        =   IF(M23>=L23,5,
            IF(M23>=K23,4+((1/(L23-K23))*(M23-K23)),
            IF(M23>=J23,3+((1/(K23-J23))*(M23-J23)),
            IF(M23>=I23,2+((1/(J23-I23))*(M23-I23)),
            IF(M23<I23,1,"Error!")))))
        """
        for rec in self:
            a = rec.achieved_value or 0.0
            t2 = rec.target_l2
            t3 = rec.target_l3
            t4 = rec.target_l4
            t5 = rec.target_l5
            lvl = 0.0
            if t5 is not False and t5 is not None and a >= t5:
                lvl = 5.0
            elif t4 is not False and t4 is not None and a >= t4:
                if t5 and (t5 - t4) > 0:
                    lvl = 4.0 + (1.0 / (t5 - t4)) * (a - t4)
                else:
                    lvl = 5.0 if t5 and a >= t5 else 4.0
            elif t3 is not False and t3 is not None and a >= t3:
                if t4 and (t4 - t3) > 0:
                    lvl = 3.0 + (1.0 / (t4 - t3)) * (a - t3)
                else:
                    lvl = 4.0 if t4 and a >= t4 else 3.0
            elif t2 is not False and t2 is not None and a >= t2:
                if t3 and (t3 - t2) > 0:
                    lvl = 2.0 + (1.0 / (t3 - t2)) * (a - t2)
                else:
                    lvl = 3.0 if t3 and a >= t3 else 2.0
            elif t2 is not False and t2 is not None and a < t2:
                lvl = 1.0
            else:
                lvl = 0.0
            if lvl and lvl != 0.0:
                if lvl < 1.0:
                    lvl = 1.0
                if lvl > 5.0:
                    lvl = 5.0
            rec.achieved_level = float(round(lvl, 2))

    @api.depends("kpi_weightage_incentive_payout")
    def _compute_kpi_weightage_performace_rating(self):
        for rec in self:
            if rec.kpi_weightage_incentive_payout:
                rec.kpi_weightage_performace_rating = float_round(
                    rec.kpi_weightage_incentive_payout * 0.6, precision_digits=2
                )
            else:
                rec.kpi_weightage_performace_rating = 0.0

    @api.depends("achieved_level", "kpi_weightage_incentive_payout")
    def _compute_weighted_achivement_incentive_payout(self):
        for rec in self:
            achieved = rec.achieved_level or 0.0
            pct = rec.kpi_weightage_incentive_payout or 0.0
            if pct > 1.0:
                pct = pct / 100.0
                # print(pct)
            rec.weighted_achivement_incentive_payout = float_round(
                achieved * pct, precision_digits=2
            )

    @api.depends("achieved_level", "kpi_weightage_performace_rating")
    def _compute_weighted_achivement_performace_rating(self):
        for rec in self:
            achieved = rec.achieved_level or 0.0
            pct = rec.kpi_weightage_performace_rating or 0.0
            # If stored as percent (e.g. 12 for 12%), convert to decimal for multiplication
            if pct > 1.0:
                pct = pct / 100.0
            rec.weighted_achivement_performace_rating = float_round(
                achieved * pct, precision_digits=2
            )

    # onchange fields

    # constraints


class HrKpiIndividualPerformance(models.Model):
    _name = "hr.kpi.individual.performance"
    _description = "Individual Key Performance Indicators"

    # normal fields
    kpi_name_description = fields.Text(
        string="Description",
        related="kpi_name_id.description",
        readonly=True,
        store=True,
    )
    kpi_name_weight = fields.Float(
        string="Weightage",
        readonly=True,
        store=True,
        help="Weight for incentive",
    )
    kpi_name_timeframe = fields.Char(string="Timeframe", readonly=True, store=True)
    target_l1 = fields.Float(string="L-1")
    target_l2 = fields.Float(string="L-2")
    target_l3 = fields.Float(string="L-3")
    target_l4 = fields.Float(string="L-4")
    target_l5 = fields.Float(string="L-5")
    achieved_value = fields.Float(string="Achieved Value", compute="_compute_achieved_value", readonly=True, store=True)

    kpi_weightage_incentive_payout = fields.Float(
        string="KPI Weightage for Incentive Payout",
        store=True,
        help="Weight for incentive payout",
    )

    # many2one fields
    kpi_id = fields.Many2one(
        "hr.kpi", string="KPI Record", required=True, ondelete="cascade"
    )
    kpi_type_id = fields.Many2one("hr.kpi.type", string="Type")
    kpi_name_id = fields.Many2one(
        "hr.kpi.type.line",
        string="Name",
        domain="[('kpi_type_id','=', kpi_type_id)]",
        help="Pointer to configured KPI name",
    )
    # one2many fields

    # computed fields
    achieved_level = fields.Float(
        string="Achieved Level",
        compute="_compute_achieved_level",
        store=True,
        readonly=True,
    )

    kpi_weightage_performace_rating = fields.Float(
        string="KPI Weightage for Performance Rating",
        readonly=True,
        store=True,
        compute="_compute_kpi_weightage_performace_rating",
        help="Weight for performance rating (40% of incentive weight).",
    )

    weighted_achivement_incentive_payout = fields.Float(
        string="Weighted Achievement for Incentive Payout",
        store=True,
        readonly=True,
        compute="_compute_weighted_achivement_incentive_payout",
        help="Weighted achievement for incentive payout (achieved_level * kpi weight%).",
    )

    weighted_achivement_performace_rating = fields.Float(
        string="Weighted Achievement for Performance Rating",
        store=True,
        readonly=True,
        compute="_compute_weighted_achivement_performace_rating",
        help="Weighted achievement for performance rating (achieved_level * kpi weight%).",
    )

    @api.depends("achieved_value", "target_l2", "target_l3", "target_l4", "target_l5")
    def _compute_achieved_level(self):
        """
        Formula to calculate achieved level based on targets:
        =   IF(N10>=M10,5,
            IF(N10>=L10,4+((1/(M10-L10))*(N10-L10)),
            IF(N10>=K10,3+((1/(L10-K10))*(N10-K10)),
            IF(N10>=J10,2+((1/(K10-J10))*(N10-J10)),
            IF(N10<J10,1,"Error!")))))
        """
        for rec in self:
            av = float(rec.achieved_value or 0.0)
            t2 = float(rec.target_l2 or 0.0)
            t3 = float(rec.target_l3 or 0.0)
            t4 = float(rec.target_l4 or 0.0)
            t5 = float(rec.target_l5 or 0.0)

            level = 0.0

            if av >= t5:
                level = 5.0

            elif av >= t4:
                denom = t5 - t4
                if denom > 0:
                    level = 4.0 + (1.0 / denom) * (av - t4)
                else:
                    level = 5.0 if av >= t5 else 4.0

            elif av >= t3:
                denom = t4 - t3
                if denom > 0:
                    level = 3.0 + (1.0 / denom) * (av - t3)
                else:
                    level = 4.0 if av >= t4 else 3.0

            elif av >= t2:
                denom = t3 - t2
                if denom > 0:
                    level = 2.0 + (1.0 / denom) * (av - t2)
                else:
                    level = 3.0 if av >= t3 else 2.0

            else:
                level = 1.0

            level = max(1.0, min(5.0, level))
            rec.achieved_level = round(level, 6)

    @api.depends("kpi_weightage_incentive_payout")
    def _compute_kpi_weightage_performace_rating(self):
        for rec in self:
            rec.kpi_weightage_performace_rating = (
                rec.kpi_weightage_incentive_payout or 0.0
            ) * 0.4

    @api.depends("achieved_level", "kpi_weightage_incentive_payout")
    def _compute_weighted_achivement_incentive_payout(self):
        for rec in self:
            level = float(rec.achieved_level or 0.0)
            pct = float(rec.kpi_weightage_incentive_payout or 0.0)
            rec.weighted_achivement_incentive_payout = round(level * (pct / 100.0), 6)

    @api.depends("achieved_level", "kpi_weightage_performace_rating")
    def _compute_weighted_achivement_performace_rating(self):
        for rec in self:
            level = float(rec.achieved_level or 0.0)
            pct = float(rec.kpi_weightage_performace_rating or 0.0)
            rec.weighted_achivement_performace_rating = round(level * (pct / 100.0), 6)
    
    @api.depends('target_l5')
    def _compute_achieved_value(self):
        for rec in self:
            rec.achieved_value = rec.target_l5

    # constraints


# class HrKpiAdditionalInfo(models.Model):
#     _name = "hr.kpi.additional.info"
#     _description = "Additional Information for HR KPI"

#     kpi_id = fields.Many2one("hr.kpi", string="KPI Record", required=True, ondelete="cascade")
#     additional_info = fields.Text(string="Additional Information")
#     created_by = fields.Many2one("res.users", string="Created By", default=lambda self: self.env.user)
#     created_date = fields.Datetime(string="Created Date", default=fields.Datetime.now)


class ConsolidatedPerformanceRating(models.Model):
    _name = "hr.kpi.consolidated.performance.rating"
    _description = "Consolidated Performance Rating"

    kpi_id = fields.Many2one(
        "hr.kpi", string="KPI Record", required=True, ondelete="cascade"
    )
    code = fields.Char("Code")
    evaluation_area = fields.Char(string="Evaluation Area")
    rating = fields.Float(string="Rating", default=0.0)
    weight = fields.Float(string="Weight", default=0.0)
    weighted_rating = fields.Float(
        string="Weighted Rating",
        compute="_compute_weighted_rating",
        store=True,
    )

    @api.depends("rating", "weight")
    def _compute_weighted_rating(self):
        for rec in self:
            rec.weighted_rating = (rec.rating or 0.0) * (rec.weight or 0.0)


class HrKpiDevelopmentPlan(models.Model):
    _name = "hr.kpi.development.plan"
    _description = "HR KPI Development Plan"

    kpi_id = fields.Many2one(
        "hr.kpi", string="KPI Record", required=True, ondelete="cascade"
    )
    development_objectives = fields.Text(string="Development Objectives")
    development_initiatives = fields.Text(string="Development Initiatives")
    development_initiative_description = fields.Text(
        string="Development Initiative Description"
    )
    priority = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
        ],
        string="Priority",
        default="medium",
    )
    due_date = fields.Date('Due Date')