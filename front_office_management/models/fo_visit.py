# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Ammu Raj (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
import datetime
import logging
import requests
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class FoVisit(models.Model):
    """Manages the details of visitors to the Office"""
    _name = 'fo.visit'
    _inherit = ['mail.thread']
    _description = 'Visit'

    name = fields.Char(string="Sequence", default=lambda self: _('New'),
                       help='Sequence number for the visiting')
    visitor_id = fields.Many2one("fo.visitor", string='Visitor',
                                 help='Select the visitor')
    phone = fields.Char(string="Phone", required=True,
                        help='Phone number of the visitor')
    email = fields.Char(string="Email",  help='Email of the Visitor')
    reason_ids = fields.Many2many('fo.purpose', string='Purpose Of Visit',
                                  required=True,
                                  help='Enter the reason for visit')
    belonging_ids = fields.One2many('fo.belongings',
                                    'visit_id',
                                    string="Personal Belongings",
                                    help='Add the belongings details of'
                                         'employee here.')
    check_in_date = fields.Datetime(string="Check In Time", readonly=True,
                                    help='Visitor check in time automatically'
                                         'fills when he checked in to the'
                                         'office')
    check_out_date = fields.Datetime(string="Check Out Time", readonly=True,
                                     help='Visitor check out time automatically'
                                          'fills when he checked out from'
                                          'office')
    employee_id = fields.Many2one('hr.employee', string="Meeting With")
    department_id = fields.Many2one('hr.department', string="Department")
    state = fields.Selection([('draft', 'Draft'),
                              ('check_in', 'Checked In'),
                              ('check_out', 'Checked Out'),
                              ('cancel', 'Cancelled'),
                              ], tracking=True, default='draft',
                             help='Status of the visitor')
    duration = fields.Char(string="Duration", compute='_compute_duration')

    @api.model_create_multi
    def create(self, vals_list):
        """Creating sequence"""
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fo.visit') or _('New')
        return super().create(vals_list)

    def action_cancel(self):
        """Action for cancelling the visitor"""
        self.state = "cancel"

    def _get_sms_config(self):
        """Fetch Diana SMS API configuration from system parameters."""
        ICP = self.env['ir.config_parameter'].sudo()
        return {
            'api_url': ICP.get_param('diana_sms.api_url', 'https://xend.positiveapi.com/api/v3/sms/send'),
            'api_token': ICP.get_param('diana_sms.api_token', ''),
            'sender_id': ICP.get_param('diana_sms.sender_id', 'Blue Dream'),
            'country_code': ICP.get_param('diana_sms.country_code', '880'),
        }

    def _normalize_phone(self, phone, country_code):
        """Convert local BD number to international format required by the API."""
        number = phone.replace(' ', '').replace('-', '').replace('+', '')
        if number.startswith('0'):
            number = country_code + number[1:]
        elif not number.startswith(country_code):
            number = country_code + number
        return number

    def _send_diana_sms(self, recipient, message):
        """Send an SMS via the Xend/Diana SMS API using JSON body."""
        config = self._get_sms_config()
        if not config['api_token']:
            _logger.warning("Diana SMS API token not configured. Skipping SMS to %s.", recipient)
            return
        phone = self._normalize_phone(recipient, config['country_code'])
        try:
            response = requests.post(
                config['api_url'],
                headers={
                    'Authorization': 'Bearer %s' % config['api_token'],
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                json={
                    'recipient': phone,
                    'sender_id': config['sender_id'],
                    'message': message,
                    'type': 'plain',
                },
                timeout=10,
            )
            result = response.json()
            if result.get('status') != 'success':
                _logger.warning("Diana SMS failed for %s: %s", phone, result.get('message'))
            else:
                _logger.info("Diana SMS sent successfully to %s — uid: %s",
                             phone, result.get('data', {}).get('uid', ''))
        except Exception as e:
            _logger.error("Diana SMS API error for %s: %s", phone, str(e))

    def action_check_in(self):
        """Action for checking in the visitor. Sends SMS to visitor and employee."""
        self.state = "check_in"
        self.check_in_date = datetime.datetime.now()

        visitor_name = self.visitor_id.name if self.visitor_id else 'Guest'

        # SMS to visitor
        if self.phone:
            self._send_diana_sms(self.phone, "Welcome to Blue Dream Corporate Office.")

        # SMS to employee (meeting with)
        if self.employee_id:
            emp_phone = (self.employee_id.mobile_phone or
                         self.employee_id.work_phone)
            if emp_phone:
                employee_msg = (
                        "Dear %s,\nYour visitor, %s, has checked in at the "
                        "front office. Please proceed accordingly."
                        % (self.employee_id.name, visitor_name)
                )
                self._send_diana_sms(emp_phone, employee_msg)

    def action_check_out(self):
        """Action for checking out the visitor"""
        self.state = "check_out"
        self.check_out_date = datetime.datetime.now()

    @api.depends('check_in_date', 'check_out_date')
    def _compute_duration(self):
        for rec in self:
            if rec.check_in_date and rec.check_out_date:
                delta = rec.check_out_date - rec.check_in_date
                total_minutes = int(delta.total_seconds() // 60)
                hours = total_minutes // 60
                minutes = total_minutes % 60
                rec.duration = '%dh %dm' % (hours, minutes)
            elif rec.check_in_date and not rec.check_out_date:
                rec.duration = 'In Progress'
            else:
                rec.duration = '-'

    @api.onchange('visitor_id')
    def _onchange_visitor_id(self):
        """Selecting the"""
        if self.visitor_id:
            if self.visitor_id.phone:
                self.phone = self.visitor_id.phone
            if self.visitor_id.email:
                self.email = self.visitor_id.email

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.department_id = self.employee_id.department_id


class VisitPurpose(models.Model):
    _name = 'fo.purpose'
    _description = 'Visit Purpose'

    name = fields.Char(string='Purpose', required=True,
                       help='Meeting purpose in short term.eg:Meeting.')
    description = fields.Text(string='Description Of Purpose',
                              help='Description for the Purpose.')
