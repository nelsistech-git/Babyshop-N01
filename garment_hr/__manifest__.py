# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 14: HR, Payroll & Workforce Management System
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - HR, Payroll & Workforce Management System',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Employee master, recruitment, attendance, leave, Bangladesh garment payroll, training and compliance',
    'description': """
Smart Complete Garment Software — HR, Payroll & Workforce Management System
================================================================================
Module 14 of the Smart Complete Garment Software suite — starts the
Workforce phase, built from the larger of two overlapping HR SRS
documents (Human Resource Management System (HRM) and this Garment HR,
Payroll & Workforce Management System, which is the more detailed one).

Follows the SRS's own two "HR Database Models" tables (17 named models
across both) closely, with pragmatic folding: Worker Profile fields are
folded directly onto the Employee Master (mirroring the Buyer/Supplier
master pattern used throughout this suite) and the ESS Portal is
implemented as record-rule-based self-service access rather than a
placeholder data model, since it owns no data of its own beyond what
Employee/Attendance/Leave/Payroll already hold.

Key Features
------------
* Employee Master (worker profile fields included, plus Gender/DOB/Blood
  Group/Work Location) with Department and Designation configuration,
  Employee Document management with expiry tracking
* Shift Management (General/Morning/Evening/Night/Rotational/Overtime,
  with Grace Period) and Worker Shift Assignment / simplified roster
* Recruitment: Manpower Requirement → Job Requisition → Candidate
  pipeline → Interview → Offer → Joining
* Attendance (Biometric/Face Recognition/RFID/Mobile/Manual sources,
  matching the ZKTeco/Hikvision/Suprema device list) with automatic late/
  early/overtime-minute calculation respecting each shift's Grace Period,
  plus Holiday/Weekly Off statuses
* Leave Management with multi-level approval and running balance
* Wage-Board Salary Structures (Grade-wise Basic/House Rent/Medical/Food/
  Transport) that Payroll pulls from directly, with a Below-Minimum-Wage
  compliance flag
* Payroll with real Bangladesh garment payroll rules: Basic/House Rent/
  Medical/Food/Transport earnings pulled from the wage-board grade,
  Attendance/Festival/Production-Incentive bonuses pulled from their own
  itemised records, OT auto-pulled from Attendance at 2x hourly rate per
  the Bangladesh Labour Act, Provident Fund (employee + employer) and a
  monthly Gratuity accrual, and a full Draft → HR Verified → Approved →
  Processed → Bank Transfer → Paid workflow
* Bonus Management (Festival/Performance/Attendance/Production) and
  Production-Linked Incentive (Extra Production x Rate formula)
* Employee Loan/Advance Management: Request → HR Approval → Finance
  Approval → Disbursement → Monthly Recovery
* Employee Complaint Management: Submit → HR Review → Investigation →
  Resolution
* Employee Exit Management: Notice → HR/Finance/Inventory/IT/Admin
  Clearance → Gratuity-based Final Settlement → Archive
* Skill Matrix, Training, Performance Evaluation (Productivity/Quality/
  Attendance/Discipline/Skill/Teamwork, matching the SRS's five-band
  Excellent/Very Good/Good/Average/Need Improvement rating scale),
  Promotion (incl. Department/Line Transfer), and Discipline (Warning)
  management
* Labor Compliance record-keeping (audit readiness)
* Employee Self-Service — implemented as portal record rules over
  Employee/Attendance/Leave/Payroll/Bonus/Incentive/Loan/Complaint rather
  than a separate data model
* AI Workforce Analytics: employee retention/attrition risk (now also
  weighing open loans and unresolved complaints), skill-gap training
  recommendations, and productivity trend analysis — extends the shared
  Garment AI Engine
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'portal', 'garment_buyer_crm'],
    'data': [
        'security/garment_hr_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/garment_hr_department_data.xml',
        'views/garment_hr_salary_structure_views.xml',
        'views/garment_hr_shift_views.xml',
        'views/garment_hr_designation_views.xml',
        'views/garment_hr_employee_views.xml',
        'views/garment_hr_department_views.xml',
        'views/garment_hr_document_views.xml',
        'views/garment_hr_recruitment_views.xml',
        'views/garment_hr_candidate_views.xml',
        'views/garment_hr_attendance_views.xml',
        'views/garment_hr_leave_views.xml',
        'views/garment_hr_payroll_views.xml',
        'views/garment_hr_bonus_views.xml',
        'views/garment_hr_loan_views.xml',
        'views/garment_hr_training_views.xml',
        'views/garment_hr_skill_matrix_views.xml',
        'views/garment_hr_performance_views.xml',
        'views/garment_hr_promotion_views.xml',
        'views/garment_hr_discipline_views.xml',
        'views/garment_hr_complaint_views.xml',
        'views/garment_hr_compliance_views.xml',
        'views/garment_hr_exit_views.xml',
        'report/garment_hr_payslip_report.xml',
        'views/garment_hr_dashboard_views.xml',
        'views/garment_hr_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
