from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrConveyance(models.Model):
    _name = 'hr.conveyance'
    _description = 'Employee Conveyance'
    _rec_name = "name"
    _order = "id desc"

    name = fields.Char(string='Name', copy=False, default=lambda self: _('New'))
    date_requested = fields.Date(string="Date", default=fields.Date.today)

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    employee_id = fields.Many2one('hr.employee', string='Employee', default=_default_employee)
    company_id = fields.Many2one('res.company', string='Company')
    department_id = fields.Many2one('hr.department', string="Department")
    old_empid = fields.Char(string="Employee ID")
    work_location_id = fields.Many2one('stock.location', string='Work/Job Location')
    job_position = fields.Many2one('hr.job', string="Designation")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Submitted'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string="State", default='draft', copy=False)

    conveyance_type = fields.Selection([
        ('tc', 'Travel & Conveyance'),
        ('ef', 'Entertainment & Food Allowance'),
        ('iou', 'IOU')
    ], string="Type", copy=False)

    purpose_id = fields.Many2one('hr.conveyance.settings', string="Purpose",
                                 domain="[('conveyance_type','=', conveyance_type), ('is_active','=', True)]")

    remarks = fields.Text(string='Remarks')

    travel_conveyance_line_ids = fields.One2many('travel.conveyance.line', 'conveyance_id',
                                                 string='Travel and Conveyance Line')
    entertainment_food_allowance_ids = fields.One2many('entertainment.food.allowance.line',
                                                       'entertainment_food_allowance_id',
                                                       string='Entertainment and Food Allowance Line')
    iou_ids = fields.One2many('iou.line', 'iou_id', string='IOU Line')

    def action_submit(self):
        for records in self:
            records.name = self.env['ir.sequence'].get('hr_conveyance_code')
            records.sudo().write({'state': 'confirm'})

    def unlink(self):
        for loan in self:
            if loan.state not in ('draft'):
                raise UserError(
                    'You cannot delete a settelment which is confirmed')
        return super(HrConveyance, self).unlink()

    def action_cancel(self):
        for records in self:
            records.sudo().write({'state': 'cancel'})

    def action_done(self):
        for records in self:
            records.sudo().write({'state': 'done'})

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for rec in self:
            if rec.employee_id:
                rec.work_location_id = rec.employee_id.work_location_id.id
                rec.company_id = rec.employee_id.company_id.id
                rec.department_id = rec.employee_id.department_id.id
                rec.old_empid = rec.employee_id.id_card_no
                rec.job_position = rec.employee_id.job_id.id

    class TravelConveyanceLine(models.Model):
        _name = "travel.conveyance.line"
        _description = 'Travel Conveyance'

        conveyance_id = fields.Many2one('hr.conveyance', required=True, ondelete='cascade')

        date = fields.Date(string='Date', required=True, index=True)
        purpose = fields.Char(string='Purpose')
        start_time = fields.Float(string="Start Time")
        end_time = fields.Float(string="End Time")
        # starting_time = fields.Datetime(string="Starting Time", default=fields.Time.now())
        # ending_time = fields.Datetime(string="Starting Time", default=fields.Time.now())
        from_place = fields.Char(string='From')
        to_place = fields.Char(string='To')
        travel_by = fields.Char(string='Travelled By')
        amount = fields.Float(string='Amount', required=True, default=0)

    class EntertainmentFoodAllowanceLine(models.Model):
        _name = "entertainment.food.allowance.line"
        _description = 'Entertainment and Food Allowance'

        entertainment_food_allowance_id = fields.Many2one('hr.conveyance', required=True, ondelete='cascade')

        date = fields.Date(string='Date', required=True, index=True)
        description_details = fields.Char(string='Description')
        qty = fields.Float(string='Quantity')
        unit_price = fields.Float(string='Unit price')
        amount = fields.Float(string='Amount', required=True, default=0)

        @api.onchange('unit_price', 'qty')
        def _onchange_amount(self):
            for rec in self:
                if rec.qty and rec.unit_price:
                    rec.amount = rec.unit_price * rec.qty

    class IOULine(models.Model):
        _name = "iou.line"
        _description = 'IOU'

        iou_id = fields.Many2one('hr.conveyance', required=True, ondelete='cascade')

        date = fields.Date(string='Date', required=True, index=True)
        description_details = fields.Char(string='Description')
        amount = fields.Float(string='Amount', required=True, default=0)
