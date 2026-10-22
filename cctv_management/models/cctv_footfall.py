# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CctvFootfallCount(models.Model):
    """People-counting rollup: one row per camera per counting interval
    (the AI service pushes one of these every N minutes, e.g. every 5 min,
    via POST /cctv/api/people_count). Powers the entry/exit customer count
    feature for showrooms/retail branches."""
    _name = 'cctv.footfall.count'
    _description = 'Footfall / People Count (Entry-Exit)'
    _order = 'interval_start desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)
    camera_id = fields.Many2one('cctv.camera', required=True, ondelete='cascade')
    office_id = fields.Many2one(related='camera_id.office_id', store=True)
    department_id = fields.Many2one(related='camera_id.department_id', store=True)
    interval_start = fields.Datetime(required=True, index=True)
    interval_end = fields.Datetime(required=True)
    entry_count = fields.Integer(string='Entries (In)', default=0)
    exit_count = fields.Integer(string='Exits (Out)', default=0)
    net_inside = fields.Integer(string='Net Inside (running total)', default=0,
                                 help='Running occupancy total at the end of this interval, '
                                      'as computed by the AI service line-crossing counter.')
    source_service = fields.Char(default='cctv-ai-service')

    @api.depends('camera_id', 'interval_start', 'entry_count', 'exit_count')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.camera_id.name or ''}] IN {rec.entry_count} / OUT {rec.exit_count} " \
                                f"({rec.interval_start or ''})"

    @api.model
    def get_today_totals(self, office_id=False):
        domain = [('interval_start', '>=', fields.Datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0))]
        if office_id:
            domain.append(('office_id', '=', office_id))
        records = self.search(domain)
        return {
            'entries': sum(records.mapped('entry_count')),
            'exits': sum(records.mapped('exit_count')),
            'inside_now': (sum(records.mapped('entry_count')) - sum(records.mapped('exit_count'))),
        }
