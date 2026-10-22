# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Extends garment.ai.engine (garment_buyer_crm) with AI Compliance
Intelligence (SRS1 secs. 20, 53-55, SRS2 sec. 69): audit/department risk
prediction from finding/incident/expiry history, and a carbon-reduction
recommendation. Rule-based, transparent, degrades gracefully.
"""
from odoo import models


class GarmentAIEngineComplianceExtension(models.AbstractModel):
    _inherit = 'garment.ai.engine'

    # ------------------------------------------------------------------
    # AI Compliance Risk Prediction (SRS1 sec. 20, SRS2 sec. 69)
    # ------------------------------------------------------------------
    def predict_compliance_risk(self, department):
        score = 0
        reasons = []

        findings = self.env['garment.compliance.finding'].search([
            ('responsible_department_id', '=', department.id), ('status', '!=', 'closed'),
        ])
        critical_findings = findings.filtered(lambda f: f.severity == 'critical')
        if critical_findings:
            score += min(40, len(critical_findings) * 20)
            reasons.append('%d open Critical finding(s).' % len(critical_findings))
        elif findings:
            score += min(20, len(findings) * 5)
            reasons.append('%d open finding(s) (Major/Minor).' % len(findings))

        incidents = self.env['garment.compliance.incident'].search([
            ('department_id', '=', department.id), ('status', '!=', 'closed'),
        ])
        if incidents:
            score += min(30, len(incidents) * 10)
            reasons.append('%d open safety incident(s).' % len(incidents))

        expired_certs = self.env['garment.compliance.certificate'].search([('status', '=', 'expired')])
        if expired_certs:
            score += min(30, len(expired_certs) * 10)
            reasons.append('%d expired certificate(s)/license(s) factory-wide.' % len(expired_certs))

        score = max(0, min(100, score))
        level = 'CRITICAL' if score >= 70 else 'HIGH' if score >= 45 else 'MEDIUM' if score >= 20 else 'LOW'
        note = 'Predicted Compliance Risk for %s: %s (score %d/100).' % (department.name, level, score)
        if reasons:
            note += '\n' + '\n'.join('- %s' % r for r in reasons)
        else:
            note += '\nNo significant risk indicators found.'
        return note

    # ------------------------------------------------------------------
    # AI Sustainability / Carbon Reduction Recommendation (SRS1 secs.
    # 53, 55)
    # ------------------------------------------------------------------
    def recommend_carbon_reduction(self, months=3):
        records = self.env['garment.compliance.energy'].search([], order='record_date desc', limit=months)
        if not records:
            return 'No energy records on file yet — cannot generate a recommendation.'

        avg_emission = sum(records.mapped('carbon_emission_ton')) / len(records)
        avg_renewable = sum(records.mapped('renewable_percentage')) / len(records)
        latest = records[0]

        reasons = ['Average monthly carbon emission over last %d record(s): %.1f Ton CO2.' % (len(records), avg_emission)]
        recommendation = 'Monitor consumption; no immediate action required.'
        if latest.electricity_kwh and latest.total_energy_kwh and latest.electricity_kwh / latest.total_energy_kwh > 0.85:
            recommendation = 'High grid-electricity dependency — optimize machine schedules and consider solar expansion.'
            reasons.append('Latest period is %.0f%% grid electricity.' % (latest.electricity_kwh / latest.total_energy_kwh * 100.0))
        elif avg_renewable < 15:
            recommendation = 'Renewable share is low — evaluate a solar installation project.'
            reasons.append('Average renewable share is only %.0f%%.' % avg_renewable)

        note = 'Sustainability Forecast: %s' % recommendation
        note += '\n' + '\n'.join('- %s' % r for r in reasons)
        return note
