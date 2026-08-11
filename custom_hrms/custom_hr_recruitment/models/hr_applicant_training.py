from odoo import fields, models, api


class HrApplicantProfessional(models.Model):
    _name = 'hr.applicant.training'
    _description = "Applicant Training"

    @api.model
    def _get_default_country(self):
        id = ''
        contry_obj = self.env['res.country'].search([('code', '=ilike', 'bd')], limit=1)
        if contry_obj:
            id = contry_obj[0].id
        return id

    applicant_id = fields.Many2one('hr.applicant', string='Applicant', required=True, ondelete="cascade")

    category = fields.Selection(
        string='Training Category',
        selection=[('1', 'Qualification'), ('2', 'Training')],
        default="", required=True)

    type_cer = fields.Selection([
        ('official', 'Official'),
        ('personal', 'Personal')
    ])

    training_mode = fields.Selection([
        ('inhouse', 'Inhouse'),
        ('outsource', 'Outsource')
    ])

    t_costing = fields.Float(string="Total Cost")
    passing_year = fields.Char(string="Passing year")
    attachment_ids = fields.Many2many('ir.attachment', 'hr_certification_ir_attachments_rel', 'attachment_id',
                                      string="Attachments", help="Attach Multiple file")
    expire = fields.Boolean('Expire', help="Expire", default=False)

    start_date = fields.Date('Start date')
    end_date = fields.Date('End date')
    certification = fields.Char(string='Training Title', help='Training Title')
    institute_id = fields.Char(string='Name of Institute / Organization / Firm',
                               help="Name of Institute / Organization / Firm")
    location = fields.Char(string='Address', help="Address of Institute / Organization / Firm")
    country = fields.Many2one('res.country', string='Country Name', default=_get_default_country)
    training_result = fields.Char(string="Qualification Gained / Achievement")
