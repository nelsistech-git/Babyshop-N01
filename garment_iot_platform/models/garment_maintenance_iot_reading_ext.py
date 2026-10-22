# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Bridge extension onto garment_maintenance's existing
``garment.maintenance.iot.reading`` model — this is the concrete answer to
"link to/extend that existing model rather than re-creating it": a Machine
Sensor reading ingested through THIS module's generic
``garment.iot.reading`` log can be relayed into a real maintenance-side
condition reading (which already carries the CMMS threshold/alert/
breakdown-Work-Order logic) via one model method, instead of
garment_iot_platform re-implementing machine-condition alerting itself.

Intended usage: a ``garment.iot.alert.rule`` with Action = "Call Method",
Target Model = garment.maintenance.iot.reading, Method Name =
create_from_iot_platform_reading — see the seeded example rule in
data/garment_iot_platform_data.xml."""

from odoo import api, models


class GarmentMaintenanceIotReadingIotPlatformExt(models.Model):
    _inherit = 'garment.maintenance.iot.reading'

    @api.model
    def create_from_iot_platform_reading(self, iot_reading):
        """Called as env['garment.maintenance.iot.reading'].sudo()
        .create_from_iot_platform_reading(reading) by the alert-rule "Call
        Method" action in garment_iot_platform. ``iot_reading`` is the
        triggering garment.iot.reading record. Maps its generic
        reading_type/value onto this model's machine-condition fields and
        creates a row here — reusing all of this model's existing
        create()-time critical-condition -> breakdown Work Order logic
        rather than duplicating it. No-ops (returns an empty recordset)
        when the source reading is not linked to a production machine."""
        if not iot_reading.machine_id:
            return self.browse()

        vals = {
            'equipment_type': 'machine',
            'machine_id': iot_reading.machine_id.id,
            'reading_datetime': iot_reading.timestamp,
        }
        if iot_reading.reading_type == 'temperature':
            vals['temperature'] = iot_reading.value
        elif iot_reading.reading_type == 'vibration':
            vals['vibration'] = iot_reading.value
        elif iot_reading.reading_type == 'speed':
            vals['speed'] = iot_reading.value
        elif iot_reading.reading_type == 'energy':
            vals['power_consumption'] = iot_reading.value
        elif iot_reading.reading_type == 'status' and iot_reading.text_value in (
                'running', 'idle', 'stopped', 'error'):
            vals['running_status'] = iot_reading.text_value

        return self.create(vals)
