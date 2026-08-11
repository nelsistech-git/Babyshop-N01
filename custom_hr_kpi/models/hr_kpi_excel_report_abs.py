from odoo import models
from datetime import datetime

class HrKpiExcelReport(models.AbstractModel):
    _name = "report.hr_kpi.report_hr_kpi_excel"
    _inherit = "report.report_xlsx.abstract"

    def _define_formats(self, workbook):
        formats = {}

        colors = {
            "primary": "#2C5F9E",           
            "primary_light": "#E6F0FF",     
            "accent": "#FF8C42",            
            "secondary": "#5B8C85",         
            "total_bg": "#F8F9FA",          
            "highlight_good": "#DFF2D8",    
            "highlight_medium": "#FFECB3",  
            "highlight_bad": "#FFCDD2",     
            "font_light": "#FFFFFF",
            "font_dark": "#2C3E50",         
            "border": "#D3D3D3",            
            "header_gradient": "#3A71B8",   
        }

        base_format = {"font_name": "Calibri", "font_size": 11}
        border_light = {"border": 1, "border_color": colors["border"]}
        border_bottom = {"bottom": 1, "bottom_color": colors["border"]}

        formats["title"] = workbook.add_format({
            **base_format,
            "bold": True,
            "font_size": 16,
            "align": "left",
            "valign": "vcenter",
            "font_color": colors["primary"],
            "bottom": 2,
            "bottom_color": colors["primary"],
        })
        
        formats["sheet_title"] = workbook.add_format({
            **base_format,
            "bold": True,
            "font_size": 14,
            "align": "center",
            "valign": "vcenter",
            "font_color": colors["font_light"],
            "bg_color": colors["primary"],
            "text_wrap": True,
            "border": 1,
            "border_color": colors["primary"],
        })
        
        formats["main_header"] = workbook.add_format({
            **base_format,
            "bold": True,
            "font_size": 11,
            "align": "center",
            "valign": "vcenter",
            "bg_color": colors["primary"],
            "font_color": colors["font_light"],
            "text_wrap": True,
            **border_light,
        })
        
        formats["section_header"] = workbook.add_format({
            **base_format,
            "bold": True,
            "font_size": 12,
            "align": "left",
            "valign": "vcenter",
            "font_color": colors["primary"],
            "bg_color": colors["primary_light"],
            "text_wrap": True,
            "border": 1,
            "border_color": colors["border"],
        })

        formats["data_text_left"] = workbook.add_format({
            **base_format,
            "align": "left",
            "valign": "top",
            "text_wrap": True,
            **border_light,
        })
        
        formats["data_text_center"] = workbook.add_format({
            **base_format,
            "align": "center",
            "valign": "top",
            "text_wrap": True,
            **border_light,
        })
        
        formats["data_number"] = workbook.add_format({
            **base_format,
            "align": "right",
            "valign": "top",
            "num_format": "#,##0.00",
            **border_light,
        })
        
        formats["data_integer"] = workbook.add_format({
            **base_format,
            "align": "right",
            "valign": "top",
            "num_format": "0",
            **border_light,
        })
        
        formats["data_percentage"] = workbook.add_format({
            **base_format,
            "align": "right",
            "valign": "top",
            "num_format": "0.00%",
            **border_light,
        })

        formats["key_label"] = workbook.add_format({
            **base_format,
            "bold": True,
            "align": "left",
            "font_color": colors["primary"],
        })
        
        formats["key_value"] = workbook.add_format({
            **base_format,
            "align": "left",
            **border_bottom,
        })
        
        formats["total_label"] = workbook.add_format({
            **base_format,
            "bold": True,
            "align": "right",
            "bg_color": colors["total_bg"],
            "font_color": colors["primary"],
            **border_light,
        })
        
        formats["total_value"] = workbook.add_format({
            **base_format,
            "bold": True,
            "align": "right",
            "num_format": "#,##0.00",
            "bg_color": colors["total_bg"],
            "font_color": colors["primary"],
            **border_light,
        })
        
        formats["final_rating"] = workbook.add_format({
            **base_format,
            "bold": True,
            "font_size": 12,
            "align": "center",
            "valign": "vcenter",
            "num_format": "0.00",
            "bg_color": colors["primary"],
            "font_color": colors["font_light"],
            "border": 1,
            "border_color": colors["primary"],
        })

        formats["highlight_good"] = workbook.add_format({
            "bg_color": colors["highlight_good"],
            **border_light,
        })
        
        formats["highlight_medium"] = workbook.add_format({
            "bg_color": colors["highlight_medium"],
            **border_light,
        })
        
        formats["highlight_bad"] = workbook.add_format({
            "bg_color": colors["highlight_bad"],
            **border_light,
        })
        
        formats["wrap_text_section"] = workbook.add_format({
            **base_format,
            "align": "left",
            "valign": "top",
            "text_wrap": True,
            "bg_color": colors["primary_light"],
            "border": 1,
            "border_color": colors["border"],
        })
        
        formats["note"] = workbook.add_format({
            **base_format,
            "italic": True,
            "font_color": "#7F8C8D",
            "font_size": 9,
        })

        return formats

    def _write_common_header(self, sheet, obj, formats, title, row_height=20):
        sheet.hide_gridlines(2)
        sheet.set_default_row(row_height)

        sheet.merge_range("B2:H2", title, formats["title"])
        sheet.set_row(1, 25)  

        row, col = 4, 1
        
        sheet.merge_range(f"B{row}:H{row}", "EMPLOYEE INFORMATION", formats["section_header"])
        sheet.set_row(row-1, 22)
        row += 1
        
        details = [
            ("Employee:", obj.employee_id.name or ""),
            ("Position:", obj.job_id.name or ""),
            ("Period:", f"{obj.period_start} to {obj.period_end}" if obj.period_start and obj.period_end else ""),
            ("Supervisor:", obj.supervisor_id.name or ""),
            ("Next Level Supervisor:", obj.next_level_supervisor_id.name or ""),
        ]
        
        details2 = [
            ("Staff ID:", obj.staff_id or ""),
            ("Department:", obj.department_id.name or ""),
            ("", ""),
            ("Supervisor Position:", obj.supervisor_position or ""),
            ("Next Level Position:", obj.next_level_supervisor_position or ""),
        ]
        
        for i, (label, value) in enumerate(details):
            sheet.write(row, col, label, formats["key_label"])
            sheet.write(row, col+1, value, formats["key_value"])
            if i < len(details2) and details2[i][0]:
                sheet.write(row, col+3, details2[i][0], formats["key_label"])
                sheet.write(row, col+4, details2[i][1], formats["key_value"])
            row += 1

        row += 1  
        return row

    def _write_performance_lines(self, sheet, start_row, lines, formats, title):
        headers = [
            "KPI Type",
            "KPI Name",
            "Description",
            "Weight",
            "Timeframe",
            "Target L1",
            "L2",
            "L3",
            "L4",
            "L5",
            "Achieved",
            "Level",
            "Incentive Payout (KPI)",
            "Performance Rating (KPI)",
            "Incentive Payout (Achievement)",
            "Performance Rating (Achievement)",
        ]
        col_widths = [12, 20, 30, 8, 12, 10, 10, 10, 10, 10, 10, 8, 15, 15, 15, 15]
        
        for i, width in enumerate(col_widths):
            sheet.set_column(i, i, width)

        sheet.merge_range(
            start_row, 0, start_row, len(headers)-1, 
            title, formats["section_header"]
        )
        sheet.set_row(start_row, 22)
        start_row += 1

        for col, header in enumerate(headers):
            sheet.write(start_row, col, header, formats["main_header"])
        sheet.set_row(start_row, 25)
        start_row += 1
        
        for line in lines:
            sheet.write(start_row, 0, line.kpi_type_id.name or "", formats["data_text_left"])
            sheet.write(start_row, 1, line.kpi_name_id.name or "", formats["data_text_left"])
            sheet.write(start_row, 2, line.kpi_name_description or "", formats["data_text_left"])
            sheet.write(start_row, 3, line.kpi_name_weight or 0, formats["data_number"])
            sheet.write(start_row, 4, line.kpi_name_timeframe or "", formats["data_text_center"])
            sheet.write(start_row, 5, line.target_l1 or 0, formats["data_number"])
            sheet.write(start_row, 6, line.target_l2 or 0, formats["data_number"])
            sheet.write(start_row, 7, line.target_l3 or 0, formats["data_number"])
            sheet.write(start_row, 8, line.target_l4 or 0, formats["data_number"])
            sheet.write(start_row, 9, line.target_l5 or 0, formats["data_number"])
            sheet.write(start_row, 10, line.achieved_value or 0, formats["data_number"])
            sheet.write(start_row, 11, line.achieved_level or 0, formats["data_integer"])
            sheet.write(start_row, 12, line.kpi_weightage_incentive_payout or 0, formats["data_number"])
            sheet.write(start_row, 13, line.kpi_weightage_performace_rating or 0, formats["data_number"])
            sheet.write(start_row, 14, line.weighted_achivement_incentive_payout or 0, formats["data_number"])
            sheet.write(start_row, 15, line.weighted_achivement_performace_rating or 0, formats["data_number"])
            start_row += 1

        sheet.merge_range(start_row, 0, start_row, 11, "Totals", formats["total_label"])
        sheet.write(start_row, 12, sum(line.kpi_weightage_incentive_payout for line in lines) or 0, formats["total_value"])
        sheet.write(start_row, 13, sum(line.kpi_weightage_performace_rating for line in lines) or 0, formats["total_value"])
        sheet.write(start_row, 14, sum(line.weighted_achivement_incentive_payout for line in lines) or 0, formats["total_value"])
        sheet.write(start_row, 15, sum(line.weighted_achivement_performace_rating for line in lines) or 0, formats["total_value"])
        
        if lines:
            sheet.conditional_format(
                f"L{start_row - len(lines)}:L{start_row - 1}",
                {
                    "type": "cell",
                    "criteria": ">=",
                    "value": 4,
                    "format": formats["highlight_good"],
                },
            )
            sheet.conditional_format(
                f"L{start_row - len(lines)}:L{start_row - 1}",
                {
                    "type": "cell",
                    "criteria": "=",
                    "value": 3,
                    "format": formats["highlight_medium"],
                },
            )
            sheet.conditional_format(
                f"L{start_row - len(lines)}:L{start_row - 1}",
                {
                    "type": "cell",
                    "criteria": "<=",
                    "value": 2,
                    "format": formats["highlight_bad"],
                },
            )

        return start_row + 2  

    def _write_summary_table(self, sheet, row, col, title, headers, data, formats, width=3):
        """Helper function to write consistent summary tables"""
        sheet.merge_range(row, col, row, col+width-1, title, formats["section_header"])
        sheet.set_row(row, 22)
        row += 1
        
        for i, header in enumerate(headers):
            sheet.write(row, col+i, header, formats["main_header"])
        sheet.set_row(row, 25)
        row += 1
        
        for data_row in data:
            for i, value in enumerate(data_row):
                if i == 0:  
                    sheet.write(row, col+i, value, formats["data_text_left"])
                else:  
                    sheet.write(row, col+i, value, formats["data_number"])
            row += 1
            
        return row + 1  

    def generate_xlsx_report(self, workbook, data, objects):
        formats = self._define_formats(workbook)
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        for obj in objects:
            sheet_corp = workbook.add_worksheet("Corporate Performance")
            sheet_corp.set_tab_color("#2C5F9E") 
            
            row = self._write_common_header(
                sheet_corp, obj, formats, "Corporate Performance Report"
            )
            
            row = self._write_performance_lines(
                sheet_corp, row, obj.corporate_performance_ids, formats, 
                "CORPORATE PERFORMANCE KPIs"
            )
            
            sheet_corp.write(row, 0, f"Report generated on: {report_date}", formats["note"])
            
            sheet_indiv = workbook.add_worksheet("Individual Performance")
            sheet_indiv.set_tab_color("#5B8C85")  
            
            row = self._write_common_header(
                sheet_indiv, obj, formats, "Individual Performance Report"
            )
            
            row = self._write_performance_lines(
                sheet_indiv, row, obj.individual_performance_ids, formats, 
                "INDIVIDUAL PERFORMANCE KPIs"
            )
            
            sheet_indiv.write(row, 0, f"Report generated on: {report_date}", formats["note"])

            sheet_summary = workbook.add_worksheet("Performance Summary")
            sheet_summary.set_tab_color("#FF8C42")  
            sheet_summary.hide_gridlines(2)
            # sheet_summary.set_default_row(20)
            sheet_summary.set_default_row(16)

            
            sheet_summary.set_column("A:A", 5) 
            # sheet_summary.set_column("B:C", 25)
            # sheet_summary.set_column("D:E", 18)
            sheet_summary.set_column("B:C", 20)  # Reduced from 25
            sheet_summary.set_column("D:E", 15) 
            sheet_summary.set_column("F:G", 15)
            
            sheet_summary.merge_range(
                "B2:G2", 
                f"PERFORMANCE SUMMARY: {obj.employee_id.name.upper()}", 
                formats["sheet_title"]
            )
            sheet_summary.set_row(1, 28)
            
            row = 4
            info_data = [
                ["Employee", obj.employee_id.name or ""],
                ["Position", obj.job_id.name or ""],
                ["Department", obj.department_id.name or ""],
                ["Review Period", f"{obj.period_start} to {obj.period_end}" if obj.period_start and obj.period_end else ""],
            ]
            
            for i, (label, value) in enumerate(info_data):
                sheet_summary.write(row, 1, label, formats["key_label"])
                sheet_summary.write(row, 2, value, formats["key_value"])
                if i % 2 == 0 and i < len(info_data) - 1:
                    sheet_summary.write(row, 4, info_data[i+1][0], formats["key_label"])
                    sheet_summary.write(row, 5, info_data[i+1][1], formats["key_value"])
                row += 1 if i % 2 == 0 else 0
                
            row += 2
            
            summary_headers = ["Area", "Incentive Payout", "Performance Rating"]
            summary_data = [
                [
                    "Company Performance Score", 
                    obj.mapped_weighted_achievement_incentive_payout or 0, 
                    obj.total_weighted_achivement_performace_rating or 0
                ],
                [
                    "Individual Performance Score", 
                    obj.mapped_weighted_achievement_incentive_payout_individuals or 0, 
                    obj.total_weighted_achivement_performace_rating_individuals or 0
                ],
                [
                    "Aligned Performance Score", 
                    "N/A", 
                    obj.individual_performance_score_after_alignment or 0
                ],
            ]
            
            row = self._write_summary_table(
                sheet_summary, row, 1, "PERFORMANCE SCORES SUMMARY", 
                summary_headers, summary_data, formats, 3
            )
            
            sheet_summary.merge_range(
                row, 1, row, 2, "Final Individual Performance Rating:", formats["total_label"]
            )
            sheet_summary.write(
                row, 3, obj.final_individual_performance_rating or 0, formats["final_rating"]
            )
            row += 2
            
            chart = workbook.add_chart({"type": "column"})
            chart.set_title({"name": "Performance Score Overview"})
            chart.set_legend({"position": "top"})
            chart.set_y_axis({"major_gridlines": {"visible": False}})
            
            chart.add_series({
                "name": "Incentive Payout",
                "categories": "='Performance Summary'!$B$" + str(row-6) + ":$B$" + str(row-4),
                "values": "='Performance Summary'!$C$" + str(row-6) + ":$C$" + str(row-4),
                "fill": {"color": "#2C5F9E"},
            })
            
            chart.add_series({
                "name": "Performance Rating",
                "categories": "='Performance Summary'!$B$" + str(row-6) + ":$B$" + str(row-4),
                "values": "='Performance Summary'!$D$" + str(row-6) + ":$D$" + str(row-4),
                "fill": {"color": "#FF8C42"},
            })
            
            sheet_summary.insert_chart(f"B{row}", chart, {"x_offset": 0, "y_offset": 0})
            row += 15  
            
            eval_headers = ["Evaluation Area", "Code", "Rating", "Weight", "Weighted Rating"]
            eval_data = []
            for line in obj.evaluation_line_ids:
                eval_data.append([
                    line.evaluation_area or "",
                    line.code or "",
                    line.rating or 0,
                    line.weight or 0,
                    line.weighted_rating or 0
                ])
                
            row = self._write_summary_table(
                sheet_summary, row, 1, "CONSOLIDATED PERFORMANCE RATING", 
                eval_headers, eval_data, formats, 5
            )
            
            dev_headers = ["Objectives", "Initiatives", "Description", "Priority", "Due Date"]
            dev_data = []
            for line in obj.development_plan_ids:
                dev_data.append([
                    line.development_objectives or "",
                    line.development_initiatives or "",
                    line.development_initiative_description or "",
                    line.priority or "",
                    str(line.due_date) if line.due_date else ""
                ])
                
            row = self._write_summary_table(
                sheet_summary, row, 1, "DEVELOPMENT PLANS", 
                dev_headers, dev_data, formats, 5
            )
            
            row += 1
            sheet_summary.merge_range(
                row, 1, row, 5, "CAREER ASPIRATIONS", formats["section_header"]
            )
            sheet_summary.set_row(row, 22)
            row += 1
            
            career_sections = [
                ("5.a - Where would you like to be in 1-3 years:", obj.five_a_career_1_3yrs or "N/A"),
                ("5.b - What support will you require from the organization:", obj.five_b_org_support or "N/A"),
                ("5.c - Expected Job Position in 1-3 years:", obj.five_c_expected_job or "N/A"),
                ("5.d - International Mobility (Willing to relocate?):", obj.five_d_international_mobility or "N/A"),
            ]
            
            for label, value in career_sections:
                sheet_summary.write(row, 1, label, formats["key_label"])
                sheet_summary.merge_range(
                    row, 2, row, 5, value, formats["wrap_text_section"]
                )
                sheet_summary.set_row(row, 60) 
                row += 1
                
                if label.startswith("5.c") and obj.five_c_expected_job == "other":
                    sheet_summary.write(row, 1, "5.c - Specify:", formats["key_label"])
                    sheet_summary.merge_range(
                        row, 2, row, 5, obj.five_c_expected_job_specify or "N/A", formats["wrap_text_section"]
                    )
                    sheet_summary.set_row(row, 40)
                    row += 1
            
            sheet_summary.write(row, 1, f"Report generated on: {report_date}", formats["note"])
            
            sheet_summary.set_landscape()
            sheet_summary.fit_to_pages(1, 0)
            
            sheet_summary.repeat_rows(0, 3)