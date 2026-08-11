from odoo import fields, models, api, _, exceptions
from odoo.exceptions import ValidationError
import datetime
from datetime import datetime, timedelta
from itertools import groupby
import pytz
import xlsxwriter

import base64
from io import BytesIO


def get_years():
    year_list = []
    crn_year = datetime.now().year
    for i in range(2022, crn_year + 5):
        year_list.append((str(i), str(i)))
    return year_list


class AttendanceSummaryReportWizard(models.TransientModel):
    _name = "attendance.summary.report.wizard"
    _description = "Attendance Summary Report Wizard"

    file_data = fields.Binary("Attendance Summary Report Wizard")
    start_date = fields.Date(string="Start Date", default=fields.Date.context_today)
    end_date = fields.Date(string="End Date", default=fields.Date.context_today)
    # year = fields.Selection(get_years(), string='Year', dafault='10', required=True)
    department_id = fields.Many2one("hr.department", string="Department")
    user_work_location_id = fields.Many2one(
        "stock.location",
        string="Work/Job Location",
        default=lambda self: self._get_work_loc(),
        domain=lambda self: self._set_domain_work_loc(),
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    # month = fields.Selection([
    #     ('01', 'January'),
    #     ('02', 'February'),
    #     ('03', 'March'),
    #     ('04', 'April'),
    #     ('05', 'May'),
    #     ('06', 'June'),
    #     ('07', 'July'),
    #     ('08', 'August'),
    #     ('09', 'September'),
    #     ('10', 'October'),
    #     ('11', 'November'),
    #     ('12', 'December'),
    # ], string='Month', required=True)

    category_ids = fields.Many2many(
        "hr.employee.category",
        "attendance_summary_employee_category_rel",
        "selected_id",
        "category_id",
        string="Tags",
    )

    sbu_unit_id = fields.Many2one("hr.sbu.unit", string="Office/Business Unit")

    @api.constrains("start_date", "end_date")
    def date_constrains(self):
        for rec in self:
            if rec.end_date < rec.start_date:
                raise ValidationError(
                    _("Start date cannot be greater than the end date.")
                )

    @api.model
    def _set_domain_work_loc(self):
        if self.env.user.user_work_location_id:
            return [
                ("is_work_loc", "=", True),
                ("state", "=", "done"),
                ("id", "=", self.env.user.user_work_location_id.id),
            ]
        else:
            return [("is_work_loc", "=", True), ("state", "=", "done")]

    @api.model
    def _get_work_loc(self):
        if self.env.user.user_work_location_id:
            return self.env.user.user_work_location_id.id

    @api.constrains("start_date", "end_date")
    def date_constrains(self):
        for rec in self:
            if rec.end_date < rec.start_date:
                raise ValidationError(
                    _("Start date cannot be greater than the end date.")
                )

    def attendance_summary_report_excel(self):
        start_date = self.start_date
        end_date = self.end_date
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id

        # get data from sql
        data = self.attendance_summary_report_sql(
            start_date, end_date, department_id, user_work_location_id
        )

        start_date = datetime.strptime(
            str(data["form"]["start_date"]), "%Y-%m-%d"
        ).strftime("%d-%b-%Y")
        end_date = datetime.strptime(
            str(data["form"]["end_date"]), "%Y-%m-%d"
        ).strftime("%d-%b-%Y")

        file_name = "Attendance Summary Report (%s - %s).xlsx" % (start_date, end_date)
        file_pointer = BytesIO()

        workbook = xlsxwriter.Workbook(file_pointer)

        # main header formatting
        format0 = workbook.add_format(
            {"font_size": 14, "align": "vcenter", "bold": True}
        )
        format0.set_align("center")
        format0.set_border()

        # column header formatting
        format1 = workbook.add_format(
            {"font_size": 10, "align": "vcenter", "bold": True}
        )
        format1.set_align("left")
        format1.set_border()
        format2 = workbook.add_format(
            {"font_size": 10, "align": "vcenter", "bold": True}
        )
        format2.set_align("center")
        format2.set_border()
        format3 = workbook.add_format(
            {"font_size": 10, "align": "vcenter", "bold": True}
        )
        format3.set_align("right")
        format3.set_border()

        # body formatting
        format4 = workbook.add_format({"font_size": 10, "align": "vcenter"})
        format4.set_align("left")
        format4.set_border()
        format5 = workbook.add_format({"font_size": 10, "align": "vcenter"})
        format5.set_align("center")
        format5.set_border()
        format6 = workbook.add_format({"font_size": 10, "align": "vcenter"})
        format6.set_align("right")
        format6.set_border()

        # grand total formatting
        format7 = workbook.add_format({"font_size": 10, "align": "right", "bold": True})
        format7.set_border()
        format8 = workbook.add_format({"font_size": 10, "align": "left", "bold": True})
        format8.set_border()
        format9 = workbook.add_format(
            {"font_size": 10, "align": "center", "bold": True}
        )
        format9.set_border()

        if data["work_loc_name"] == "All":
            summary_sheet = workbook.add_worksheet("Branch Summary")

            summary_sheet.merge_range(
                0, 0, 0, 11, "{0}".format(data["form"]["company_id"][1]), format0
            )
            summary_sheet.merge_range(1, 0, 1, 11, "Attendance Summary Report", format0)
            summary_sheet.merge_range(
                2, 0, 2, 5, "From Date: {0}".format(start_date), format1
            )
            summary_sheet.merge_range(
                2, 6, 2, 11, "Branch: {0}".format(data["work_loc_name"]), format1
            )
            summary_sheet.merge_range(
                3, 0, 3, 5, "To Date: {0}".format(end_date), format1
            )
            summary_sheet.merge_range(
                3, 6, 3, 11, "Department: {0}".format(data["dept_name"]), format1
            )
            summary_sheet.merge_range(
                4,
                0,
                4,
                5,
                (
                    "Office/Buisness Unit: {0}".format(self.sbu_unit_id.display_name)
                    if self.sbu_unit_id
                    else "Office/Buisness Unit: All"
                ),
                format1,
            )
            summary_sheet.merge_range(
                4,
                6,
                4,
                11,
                (
                    "Tags: {0}".format(
                        ",".join(self.category_ids.mapped("display_name"))
                    )
                    if self.sbu_unit_id
                    else "Tags: No Tags Selected"
                ),
                format1,
            )

            summary_sheet.write(5, 0, "Sl.", format2)
            summary_sheet.write(5, 1, "Branch", format2)
            summary_sheet.write(5, 2, "Total Employee", format2)
            summary_sheet.write(5, 3, "Present", format2)
            summary_sheet.write(5, 4, "Absent", format2)
            summary_sheet.write(5, 5, "Weekend", format2)
            summary_sheet.write(5, 6, "Late", format2)
            summary_sheet.write(5, 7, "Early", format2)
            summary_sheet.write(5, 8, "Leave", format2)
            summary_sheet.write(5, 9, "Overtime", format2)
            summary_sheet.write(5, 10, "Manual Att.", format2)
            summary_sheet.write(5, 11, "Remarks", format2)

            sum_sl_no = 1
            total_emp = 0
            total_present_days = 0
            total_absent_days = 0
            total_weekend_days = 0
            total_late_days = 0
            total_early_out = 0
            total_leave_days = 0
            total_ovetime_days = 0
            total_manual_att = 0

            summary_row = 6
            summary_col = 0

            for line in data["csr"]:
                for line2 in line:
                    loc_id = line[line2][0]["user_work_location_id"]

                    summary_sheet.write(summary_row, 0, sum_sl_no, format1)
                    summary_sheet.write(
                        summary_row,
                        summary_col + 1,
                        line[line2][0]["loc_name"],
                        format1,
                    )
                    summary_sheet.write(
                        summary_row, summary_col + 2, len(line[line2]), format2
                    )
                    total_emp = total_emp + len(line[line2])
                    summary_sheet.write(
                        summary_row,
                        summary_col + 3,
                        sum(
                            x["present_day"]
                            for x in line[line2]
                            if x["user_work_location_id"] == loc_id
                        ),
                        format2,
                    )
                    total_present_days = total_present_days + sum(
                        x["present_day"]
                        for x in line[line2]
                        if x["user_work_location_id"] == loc_id
                    )
                    summary_sheet.write(
                        summary_row,
                        summary_col + 4,
                        sum(
                            x["absent_day"]
                            for x in line[line2]
                            if x["user_work_location_id"] == loc_id
                        ),
                        format2,
                    )
                    total_absent_days = total_absent_days + sum(
                        x["absent_day"]
                        for x in line[line2]
                        if x["user_work_location_id"] == loc_id
                    )
                    summary_sheet.write(
                        summary_row,
                        summary_col + 5,
                        sum(
                            x["weekend"]
                            for x in line[line2]
                            if x["user_work_location_id"] == loc_id
                        ),
                        format2,
                    )
                    total_weekend_days = total_weekend_days + sum(
                        x["weekend"]
                        for x in line[line2]
                        if x["user_work_location_id"] == loc_id
                    )
                    summary_sheet.write(
                        summary_row,
                        summary_col + 6,
                        sum(
                            x["late_day"]
                            for x in line[line2]
                            if x["user_work_location_id"] == loc_id
                        ),
                        format2,
                    )
                    total_late_days = total_late_days + sum(
                        x["late_day"]
                        for x in line[line2]
                        if x["user_work_location_id"] == loc_id
                    )
                    summary_sheet.write(
                        summary_row,
                        summary_col + 7,
                        sum(
                            x["early_out"]
                            for x in line[line2]
                            if x["user_work_location_id"] == loc_id
                        ),
                        format2,
                    )
                    total_early_out = total_early_out + sum(
                        x["early_out"]
                        for x in line[line2]
                        if x["user_work_location_id"] == loc_id
                    )
                    summary_sheet.write(
                        summary_row,
                        summary_col + 8,
                        sum(
                            x["leave_days"]
                            for x in line[line2]
                            if x["user_work_location_id"] == loc_id
                        ),
                        format2,
                    )
                    total_leave_days = total_leave_days + sum(
                        x["leave_days"]
                        for x in line[line2]
                        if x["user_work_location_id"] == loc_id
                    )
                    summary_sheet.write(
                        summary_row,
                        summary_col + 9,
                        sum(
                            x["ot_days"]
                            for x in line[line2]
                            if x["user_work_location_id"] == loc_id
                        ),
                        format2,
                    )
                    total_ovetime_days = total_ovetime_days + sum(
                        x["ot_days"]
                        for x in line[line2]
                        if x["user_work_location_id"] == loc_id
                    )
                    summary_sheet.write(
                        summary_row,
                        summary_col + 10,
                        sum(
                            x["manual_att"]
                            for x in line[line2]
                            if x["user_work_location_id"] == loc_id
                        ),
                        format2,
                    )
                    total_manual_att = total_manual_att + sum(
                        x["manual_att"]
                        for x in line[line2]
                        if x["user_work_location_id"] == loc_id
                    )
                    summary_sheet.write(summary_row, summary_col + 11, "", format2)

                    sum_sl_no = sum_sl_no + 1
                    summary_row = summary_row + 1

            summary_final_row = summary_row
            summary_final_col = 0
            summary_sheet.merge_range(
                summary_final_row,
                summary_final_col,
                summary_final_row,
                summary_final_col + 1,
                "Total",
                format7,
            )
            summary_sheet.write(
                summary_final_row, summary_final_col + 2, total_emp, format9
            )
            summary_sheet.write(
                summary_final_row, summary_final_col + 3, total_present_days, format9
            )
            summary_sheet.write(
                summary_final_row, summary_final_col + 4, total_absent_days, format9
            )
            summary_sheet.write(
                summary_final_row, summary_final_col + 5, total_weekend_days, format9
            )
            summary_sheet.write(
                summary_final_row, summary_final_col + 6, total_late_days, format9
            )
            summary_sheet.write(
                summary_final_row, summary_final_col + 7, total_early_out, format9
            )
            summary_sheet.write(
                summary_final_row, summary_final_col + 8, total_leave_days, format9
            )
            summary_sheet.write(
                summary_final_row, summary_final_col + 9, total_ovetime_days, format9
            )
            summary_sheet.write(
                summary_final_row, summary_final_col + 10, total_manual_att, format9
            )
            summary_sheet.write(
                summary_final_row, summary_final_col + 11, None, format9
            )

        for line in data["csr"]:
            for line2 in line:
                sheet = workbook.add_worksheet(line[line2][0]["loc_name"])
                sheet.merge_range(
                    0, 0, 0, 12, "{0}".format(data["form"]["company_id"][1]), format0
                )
                sheet.merge_range(
                    1,
                    0,
                    2,
                    12,
                    "Attendance Summary Report (%s - %s)" % (start_date, end_date),
                    format0,
                )

                sheet.merge_range(
                    3,
                    0,
                    3,
                    3,
                    "Branch: {0}".format(line[line2][0]["loc_name"]),
                    format1,
                )
                sheet.merge_range(
                    3,
                    4,
                    3,
                    7,
                    "Department Name: {0}".format(data["dept_name"]),
                    format1,
                )
                sheet.merge_range(
                    3,
                    8,
                    3,
                    10,
                    (
                        "Office/Buisness Unit: {0}".format(
                            self.sbu_unit_id.display_name
                        )
                        if self.sbu_unit_id
                        else "Office/Buisness Unit: All"
                    ),
                    format1,
                )
                sheet.merge_range(
                    3,
                    11,
                    3,
                    12,
                    (
                        "Tags: {0}".format(
                            ",".join(self.category_ids.mapped("display_name"))
                        )
                        if self.sbu_unit_id
                        else "Tags: No Tags Selected"
                    ),
                    format1,
                )

                sheet.merge_range(4, 0, 4, 1, "Total Employee", format2)
                sheet.merge_range(4, 2, 4, 3, "Total Present", format2)
                sheet.merge_range(4, 4, 4, 5, "Total Absent", format2)
                sheet.write(4, 6, "Total Weekend", format2)
                sheet.write(4, 7, "Total Late", format2)
                sheet.write(4, 8, "Total Early Out", format2)
                sheet.write(4, 9, "Total Leave", format2)
                sheet.write(4, 10, "Total Overtime", format2)
                sheet.write(4, 11, "Total Manual Att.", format2)
                sheet.write(4, 12, "Remarks", format2)

                loc_id = line[line2][0]["user_work_location_id"]

                sheet.merge_range(5, 0, 5, 1, len(line[line2]), format2)
                sheet.merge_range(
                    5,
                    2,
                    5,
                    3,
                    sum(
                        x["present_day"]
                        for x in line[line2]
                        if x["user_work_location_id"] == loc_id
                    ),
                    format2,
                )
                sheet.merge_range(
                    5,
                    4,
                    5,
                    5,
                    sum(
                        x["absent_day"]
                        for x in line[line2]
                        if x["user_work_location_id"] == loc_id
                    ),
                    format2,
                )
                sheet.write(
                    5,
                    6,
                    sum(
                        x["weekend"]
                        for x in line[line2]
                        if x["user_work_location_id"] == loc_id
                    ),
                    format2,
                )
                sheet.write(
                    5,
                    7,
                    sum(
                        x["late_day"]
                        for x in line[line2]
                        if x["user_work_location_id"] == loc_id
                    ),
                    format2,
                )
                sheet.write(
                    5,
                    8,
                    sum(
                        x["early_out"]
                        for x in line[line2]
                        if x["user_work_location_id"] == loc_id
                    ),
                    format2,
                )
                sheet.write(
                    5,
                    9,
                    sum(
                        x["leave_days"]
                        for x in line[line2]
                        if x["user_work_location_id"] == loc_id
                    ),
                    format2,
                )
                sheet.write(
                    5,
                    10,
                    sum(
                        x["ot_days"]
                        for x in line[line2]
                        if x["user_work_location_id"] == loc_id
                    ),
                    format2,
                )
                sheet.write(
                    5,
                    11,
                    sum(
                        x["manual_att"]
                        for x in line[line2]
                        if x["user_work_location_id"] == loc_id
                    ),
                    format2,
                )
                sheet.write(5, 12, "", format2)

                sheet.write(7, 0, "Employee ID", format2)
                sheet.write(7, 1, "Employee Name", format2)
                sheet.write(7, 2, "Department", format2)
                sheet.write(7, 3, "Designation", format2)
                sheet.write(7, 4, "Present", format2)
                sheet.write(7, 5, "Absent", format2)
                sheet.write(7, 6, "Weekend", format2)
                sheet.write(7, 7, "Late", format2)
                sheet.write(7, 8, "Early Out", format2)
                sheet.write(7, 9, "Leave", format2)
                sheet.write(7, 10, "Overtime", format2)
                sheet.write(7, 11, "Manual Att.", format2)
                sheet.write(7, 12, "Remarks", format2)

                row = 8
                col = 0

                for line3 in line[line2]:
                    sheet.write(row, col, line3["emp_id_card"], format5)
                    sheet.write(row, col + 1, line3["employee_name"], format5)
                    sheet.write(row, col + 2, line3["dept_name"], format5)
                    sheet.write(row, col + 3, line3["designation"], format5)
                    sheet.write(row, col + 4, line3["present_day"], format5)
                    sheet.write(row, col + 5, line3["absent_day"], format5)
                    sheet.write(row, col + 6, line3["weekend"], format5)
                    sheet.write(row, col + 7, line3["late_day"], format5)
                    sheet.write(row, col + 8, line3["early_out"], format5)
                    sheet.write(row, col + 9, line3["leave_days"], format5)
                    sheet.write(row, col + 10, line3["ot_days"], format5)
                    sheet.write(row, col + 11, line3["manual_att"], format5)
                    sheet.write(row, col + 12, "", format5)

                    row = row + 1

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({"file_data": file_data})
        file_pointer.close()

        return {
            "name": "Attendance Summary Report",
            "type": "ir.actions.act_url",
            "url": "/web/content?model=attendance.summary.report.wizard&field=file_data&id=%s&filename=%s"
            % (self.id, file_name),
            "target": "self",
        }

    def attendance_summary_report_pdf(self):
        start_date = self.start_date
        end_date = self.end_date
        department_id = self.department_id
        user_work_location_id = self.user_work_location_id

        # get data from sql
        data = self.attendance_summary_report_sql(
            start_date, end_date, department_id, user_work_location_id
        )

        return (
            self.env.ref("custom_hr_report.employee_attendance_summary_report_tmpl")
            .with_context(landscape=True)
            .report_action(self, data=data)
        )

    def attendance_summary_report_sql(
        self, start_date, end_date, department_id, user_work_location_id
    ):
        dept_filter = ""
        work_loc_filter = ""
        dept_name = "All"
        work_location_name = "All"
        tags_filter = ""
        business_unit_filter = ""
        tag_filter_join = "LEFT"
        domain = []
        order_by = "hre.name"

        # order_by check
        order_by_flag = self.env["custom.common.settings"].search(
            [("key", "=", "hr_reports_order_by_employee_id")], limit=1
        )

        if order_by_flag.value:
            order_by = "hre.id_card_no"
        # print(order_by)

        if department_id:
            dept_filter = "AND hre.department_id = %s" % department_id.id
            # domain += [('department_id', '=', department_id.id)]
            dept_name = department_id.display_name

        if user_work_location_id:
            work_loc_filter = (
                "AND hre.user_work_location_id = %s" % user_work_location_id.id
            )
            # domain += [('user_work_location_id', '=', user_work_location_id.id)]
            work_location_name = user_work_location_id.display_name

        # emp_ids = self.env['hr.employee'].sudo().search(domain)

        if self.category_ids:
            tag_filter_join = ""
            if len(self.category_ids) > 1:
                tags_filter = "WHERE etag.id IN {0}".format(
                    tuple(self.category_ids.ids)
                )

            else:
                tags_filter = "WHERE etag.id = {0}".format(self.category_ids.ids[0])

        if self.sbu_unit_id:
            business_unit_filter = "AND hre.sbu_unit_id = {0}".format(
                self.sbu_unit_id.id
            )

        data_sql = """
                    SELECT hre.id AS emp_id, hre.name AS employee_name, COALESCE(hre.id_card_no, '') AS emp_id_card, hre.department_id AS department_id, hd.name->>'en_US' AS dept_name, 
                    hre.job_id AS job_id,hj.name->>'en_US' AS designation, COALESCE(hre.user_work_location_id, 100000) AS user_work_location_id, COALESCE(sl.name, '') AS loc_name, hc.att_policy_id,
                    
                    COALESCE(SUM(CASE WHEN (easl.pl_sign_in > 0 AND easl.status IS NULL) OR (easl.status ='weekend' AND easl.worked_hours > 0 AND hap.work_day_without_week_ph = False)  OR (easl.status = 'ph' AND easl.worked_hours > 0 AND hap.work_day_without_ph = False) THEN 1 ELSE 0 END), 0) AS present_day,
                    
                    COALESCE(SUM(CASE WHEN easl.status = 'ab' THEN 1 ELSE 0 END), 0) AS absent_day,
                    COALESCE(SUM(CASE WHEN easl.late_in > 0 THEN 1 ELSE 0 END), 0) AS late_day,
                    COALESCE(SUM(CASE WHEN easl.late_in_abs > 0 THEN 1 ELSE 0 END), 0) AS late_day_abs,
                    COALESCE(SUM(CASE WHEN easl.diff_time > 0 AND (easl.status IS NULL OR easl.status IN ('weekend', 'ph', 'leave')) THEN 1 ELSE 0 END), 0) AS early_out,
                    COALESCE(SUM(CASE WHEN easl.status = 'leave' THEN 1 ELSE 0 END), 0) AS leave_days,
                    COALESCE(SUM(CASE WHEN easl.status = 'weekend' AND (easl.worked_hours = 0 OR easl.worked_hours IS NULL) THEN 1 ELSE 0 END), 0) AS weekend,
                    COALESCE(SUM(CASE WHEN easl.status = 'ph' AND (easl.worked_hours = 0 OR easl.worked_hours IS NULL) THEN 1 ELSE 0 END), 0) AS ph,
                    COALESCE(SUM(CASE WHEN easl.manual_flag = '1' THEN 1 ELSE 0 END), 0) AS manual_att,
                    COALESCE(SUM(CASE WHEN easl.status in ('ab', 'leave') OR easl.status IS NULL THEN 1 ELSE 0 END), 0) AS total_working_days,
                    COALESCE(SUM(CASE WHEN easl.status in ('ab', 'leave', 'weekend', 'ph') OR easl.status IS NULL THEN 1 ELSE 0 END), 0) AS no_of_days_w,
                    
                    COALESCE(SUM(CASE WHEN (easl.status ='weekend' AND easl.worked_hours > 0 AND hap.work_day_without_week_ph = True) OR (easl.status = 'ph' AND easl.worked_hours > 0 AND hap.work_day_without_ph = True) THEN 1 ELSE 0 END), 0) AS ot_days
                    
                    FROM employee_attendance_sheet_line easl
                    LEFT JOIN hr_employee hre ON hre.id = easl.employee_id
                    LEFT JOIN hr_contract hc ON hc.employee_id = hre.id
                    LEFT JOIN hr_department hd ON hd.id = hre.department_id
                    LEFT JOIN hr_job hj ON hj.id = hre.job_id
                    LEFT JOIN stock_location sl ON sl.id = hre.user_work_location_id
                    LEFT JOIN hr_attendance_policy hap ON hap.id = hc.att_policy_id
                    {6} JOIN (
                            SELECT emp_id,string_agg(name, ', ') as tag_name from employee_category_rel ecr
                            JOIN hr_employee_category etag on etag.id=ecr.category_id
                            {5}
                            GROUP BY emp_id
                        ) emp_tag ON emp_tag.emp_id = hre.id
                    WHERE hc.state = 'open' AND hre.active = true
                    AND DATE(easl.date) BETWEEN '{0}' AND '{1}' {2} {3} {4}
                    GROUP BY hre.id, hc.att_policy_id, hd.name, hj.name, sl.name
                    ORDER BY {7}
                    """.format(
            start_date,
            end_date,
            work_loc_filter,
            dept_filter,
            business_unit_filter,
            tags_filter,
            tag_filter_join,
            order_by,
        )
        self.env.cr.execute(data_sql)

        data_res = self.env.cr.dictfetchall()

        # print("data_res", data_res)

        # data_res = []

        # define a fuction for key
        def key_func(k):
            return k["user_work_location_id"]

        data_res = sorted(data_res, key=key_func)

        data_res = sorted(data_res, key=lambda k: (k["loc_name"], k["emp_id_card"]))

        data_list = []

        for key, value in groupby(data_res, key_func):
            vals = {key: list(value)}
            data_list.append(vals)

        data = {
            "model": "attendance.summary.report.wizard",
            "form": self.read()[0],
            "csr": data_list,
            "work_loc_name": work_location_name,
            "dept_name": dept_name,
            "buisness_unit": self.sbu_unit_id.display_name,
            "tag_names_list": ",".join(self.category_ids.mapped("display_name")),
        }
        return data
