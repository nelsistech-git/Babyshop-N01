from odoo import models


class HrKpiExcelReport(models.AbstractModel):
    """
    An enhanced Excel report for HR KPIs with a focus on improved UI/UX.
    This report provides a clear, visually appealing, and easy-to-navigate
    summary of corporate and individual performance.
    """

    _name = "report.hr_kpi.report_hr_kpi_excel"
    _inherit = "report.report_xlsx.abstract"

    def _define_formats(self, workbook):
        """
        Defines all the cell formats used in the report for a consistent and
        professional look. This centralizes styling for easy maintenance.
        """
        formats = {}

        # === Color Palette - Enhanced for better accessibility and visual hierarchy ===
        colors = {
            "primary": "#1A3F6B",           
            "primary_light": "#D9E2F3",
            "primary_extra_light": "#EDF2FA",
            "accent": "#3A6EA5",
            "accent_dark": "#2A4F7A",
            "total_bg": "#F5F7FA",
            "highlight_good": "#C6EFCE",
            "highlight_middle": "#FFEB9C",  
            "highlight_bad": "#FFC7CE",
            "font_light": "#FFFFFF",
            "font_dark": "#333333",  
            "border": "#D0D0D0",  
            "section_divider": "#A0A0A0",
        }

        # === Base Formats ===
        base_format = {"font_name": "Calibri", "font_size": 11}
        border_light = {"border": 1, "border_color": colors["border"]}
        border_medium = {"bottom": 2, "bottom_color": colors["section_divider"]}

        # === Title and Header Formats - Enhanced spacing and visual hierarchy ===
        formats["title"] = workbook.add_format(
            {
                **base_format,
                "bold": True,
                "font_size": 22,
                "align": "left",
                "valign": "vcenter",
                "font_color": colors["primary"],
                "bottom": 1,
                "bottom_color": colors["primary_light"],
                "text_v_align": 1,  # Add slight padding
            }
        )
        formats["main_header"] = workbook.add_format(
            {
                **base_format,
                "bold": True,
                "font_size": 11,
                "align": "center",
                "valign": "vcenter",
                "bg_color": colors["primary"],
                "font_color": colors["font_light"],
                "text_wrap": True,
                **border_light,
                "text_v_align": 2,  # Add vertical padding
            }
        )
        formats["section_header"] = workbook.add_format(
            {
                **base_format,
                "bold": True,
                "font_size": 14,
                "align": "left",
                "valign": "vcenter",
                "font_color": colors["primary"],
                **border_medium,
                "text_v_align": 2,
            }
        )
        formats["subsection_header"] = workbook.add_format(
            {
                **base_format,
                "bold": True,
                "font_size": 12,
                "align": "left",
                "valign": "vcenter",
                "font_color": colors["accent_dark"],
                "bg_color": colors["primary_extra_light"],
                **border_light,
                "text_v_align": 2,
            }
        )

        # === Data Cell Formats - Improved readability ===
        formats["data_text_left"] = workbook.add_format(
            {
                **base_format,
                "align": "left",
                "valign": "top",
                "text_wrap": True,
                **border_light,
                "text_v_align": 2,
            }
        )
        formats["data_text_center"] = workbook.add_format(
            {
                **base_format,
                "align": "center",
                "valign": "top",
                "text_wrap": True,
                **border_light,
                "text_v_align": 2,
            }
        )
        formats["data_number"] = workbook.add_format(
            {
                **base_format,
                "align": "right",
                "valign": "top",
                "num_format": "#,##0.00",
                **border_light,
                "text_v_align": 2,
            }
        )
        formats["data_integer"] = workbook.add_format(
            {
                **base_format,
                "align": "right",
                "valign": "top",
                "num_format": "0",
                **border_light,
                "text_v_align": 2,
            }
        )
        formats["data_highlight"] = workbook.add_format(
            {
                **base_format,
                "bold": True,
                "align": "right",
                "valign": "top",
                "num_format": "#,##0.00",
                "bg_color": colors["primary_extra_light"],
                **border_light,
                "text_v_align": 2,
            }
        )

        # === Key Info & Total Formats - Enhanced visual hierarchy ===
        formats["key_label"] = workbook.add_format(
            {**base_format, "bold": True, "align": "left", "font_color": colors["accent_dark"]}
        )
        formats["key_value"] = workbook.add_format(
            {**base_format, "align": "left", "font_color": colors["font_dark"]}
        )
        formats["total_label"] = workbook.add_format(
            {
                **base_format,
                "bold": True,
                "align": "right",
                "bg_color": colors["total_bg"],
                **border_light,
                "font_color": colors["font_dark"],
            }
        )
        formats["total_value"] = workbook.add_format(
            {
                **base_format,
                "bold": True,
                "align": "right",
                "num_format": "#,##0.00",
                "bg_color": colors["total_bg"],
                **border_light,
                "font_color": colors["font_dark"],
            }
        )
        formats["final_rating"] = workbook.add_format(
            {
                **base_format,
                "bold": True,
                "font_size": 16,
                "align": "center",
                "valign": "vcenter",
                "num_format": "0.00",
                "bg_color": colors["accent"],
                "font_color": colors["font_light"],
                "border": 1,
                "border_color": colors["accent_dark"],
            }
        )
        formats["summary_header"] = workbook.add_format(
            {
                **base_format,
                "bold": True,
                "font_size": 12,
                "align": "center",
                "valign": "vcenter",
                "bg_color": colors["primary"],
                "font_color": colors["font_light"],
                "text_wrap": True,
                **border_light,
            }
        )

        # === Conditional & Utility Formats ===
        formats["highlight_good"] = workbook.add_format(
            {"bg_color": colors["highlight_good"], **border_light}
        )
        formats["highlight_middle"] = workbook.add_format(
            {"bg_color": colors["highlight_middle"], **border_light}
        )
        formats["highlight_bad"] = workbook.add_format(
            {"bg_color": colors["highlight_bad"], **border_light}
        )
        formats["wrap_text_section"] = workbook.add_format(
            {
                **base_format,
                "align": "left",
                "valign": "top",
                "text_wrap": True,
                "bg_color": colors["primary_extra_light"],
                **border_light,
                "text_v_align": 2,
            }
        )
        formats["chart_title"] = workbook.add_format(
            {
                **base_format,
                "bold": True,
                "font_size": 13,
                "align": "center",
                "font_color": colors["primary"],
            }
        )

        return formats

    def _write_common_header(self, sheet, obj, formats, title):
        """
        Writes a compact and clean header section with employee details.
        Enhanced with better spacing, visual separation, and consistent alignment.
        """
        sheet.hide_gridlines(2)
        sheet.set_default_row(22)  # Increased row height for better readability

        colors = {
            "primary": "#1A3F6B",           
            "primary_light": "#D9E2F3",
            "primary_extra_light": "#EDF2FA",
            "accent": "#3A6EA5",
            "accent_dark": "#2A4F7A",
            "total_bg": "#F5F7FA",
            "highlight_good": "#C6EFCE",
            "highlight_middle": "#FFEB9C",  
            "highlight_bad": "#FFC7CE",
            "font_light": "#FFFFFF",
            "font_dark": "#333333",  
            "border": "#D0D0D0",  
            "section_divider": "#A0A0A0",
        }
        # Add subtle background for header section
        sheet.set_row(3, 22, formats["primary_extra_light"])
        sheet.set_row(4, 22, formats["primary_extra_light"])
        sheet.set_row(5, 22, formats["primary_extra_light"])
        sheet.set_row(6, 22, formats["primary_extra_light"])
        sheet.set_row(7, 22, formats["primary_extra_light"])

        # Add spacing column between detail sections
        sheet.set_column("C:C", 3)  # Space between left and right columns
        sheet.set_column("F:F", 5)  # Right margin space

        # Main Title with enhanced styling
        sheet.merge_range("B2:E2", title, formats["title"])

        # Employee Details Section with improved layout
        row, col = 3, 0
        sheet.merge_range(row, col, row, 2, "Employee Information", formats["subsection_header"])
        row += 1
        
        sheet.write(row, col, "Employee:", formats["key_label"])
        sheet.write(row, col + 1, obj.employee_id.name or "", formats["key_value"])
        sheet.write(row, col + 3, "Staff ID:", formats["key_label"])
        sheet.write(row, col + 4, obj.staff_id or "", formats["key_value"])
        row += 1
        sheet.write(row, col, "Position:", formats["key_label"])
        sheet.write(row, col + 1, obj.job_id.name or "", formats["key_value"])
        sheet.write(row, col + 3, "Department:", formats["key_label"])
        sheet.write(row, col + 4, obj.department_id.name or "", formats["key_value"])
        row += 1
        sheet.write(row, col, "Period:", formats["key_label"])
        sheet.write(
            row,
            col + 1,
            (
                f"{obj.period_start} to {obj.period_end}"
                if obj.period_start and obj.period_end
                else ""
            ),
            formats["key_value"],
        )
        row += 2
        
        sheet.merge_range(row, col, row, 2, "Supervisor Information", formats["subsection_header"])
        row += 1
        sheet.write(row, col, "Supervisor:", formats["key_label"])
        sheet.write(row, col + 1, obj.supervisor_id.name or "", formats["key_value"])
        sheet.write(row, col + 3, "Supervisor Position:", formats["key_label"])
        sheet.write(row, col + 4, obj.supervisor_position or "", formats["key_value"])
        row += 1
        sheet.write(row, col, "Next Level Supervisor:", formats["key_label"])
        sheet.write(
            row, col + 1, obj.next_level_supervisor_id.name or "", formats["key_value"]
        )
        sheet.write(row, col + 3, "Next Level Position:", formats["key_label"])
        sheet.write(
            row, col + 4, obj.next_level_supervisor_position or "", formats["key_value"]
        )
        row += 2
        return row

    def _write_performance_lines(self, sheet, start_row, lines, formats, workbook):
        """
        A reusable function to write performance data tables with enhanced UI/UX.
        Improvements include better spacing, visual hierarchy, and conditional formatting.
        """
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
        col_widths = [16, 26, 45, 9, 13, 11, 11, 11, 11, 11, 11, 9, 14, 14, 14, 14]
        colors = {
            "primary": "#1A3F6B",
            "primary_light": "#D9E2F3",
            "primary_extra_light": "#EDF2FA",
            "accent": "#3A6EA5",
            "accent_dark": "#2A4F7A",
            "total_bg": "#F5F7FA",
            "highlight_good": "#C6EFCE",
            "highlight_middle": "#FFEB9C",
            "highlight_bad": "#FFC7CE",
            "font_light": "#FFFFFF",
            "font_dark": "#333333",
            "border": "#D0D0D0",
            "section_divider": "#A0A0A0",
        }

        # Set column widths with more breathing room
        for i, width in enumerate(col_widths):
            sheet.set_column(i, i, width)

        # Write headers with enhanced styling
        for col, header in enumerate(headers):
            sheet.write(start_row, col, header, formats["main_header"])

        start_row += 1
        row = start_row
        
        # Add alternating row colors for better readability
        row_format = formats["data_text_left"]
        
        for line in lines:
            # Apply zebra striping
            if (row - start_row) % 2 == 0:
                bg_format = formats["primary_extra_light"]
                row_format = {
                    k: {**v, **bg_format} if isinstance(v, dict) else v 
                    for k, v in formats.items()
                }
            else:
                row_format = formats
            
            sheet.write(row, 0, line.kpi_type_id.name or "", row_format["data_text_left"])
            sheet.write(row, 1, line.kpi_name_id.name or "", row_format["data_text_left"])
            sheet.write(
                row, 2, line.kpi_name_description or "", row_format["data_text_left"]
            )
            sheet.write(row, 3, line.kpi_name_weight or 0, row_format["data_number"])
            sheet.write(
                row, 4, line.kpi_name_timeframe or "", row_format["data_text_center"]
            )
            sheet.write(row, 5, line.target_l1 or 0, row_format["data_number"])
            sheet.write(row, 6, line.target_l2 or 0, row_format["data_number"])
            sheet.write(row, 7, line.target_l3 or 0, row_format["data_number"])
            sheet.write(row, 8, line.target_l4 or 0, row_format["data_number"])
            sheet.write(row, 9, line.target_l5 or 0, row_format["data_number"])
            sheet.write(row, 10, line.achieved_value or 0, row_format["data_number"])
            sheet.write(row, 11, line.achieved_level or 0, row_format["data_integer"])
            sheet.write(
                row,
                12,
                line.kpi_weightage_incentive_payout or 0,
                row_format["data_number"],
            )
            sheet.write(
                row,
                13,
                line.kpi_weightage_performace_rating or 0,
                row_format["data_number"],
            )
            sheet.write(
                row,
                14,
                line.weighted_achivement_incentive_payout or 0,
                row_format["data_number"],
            )
            sheet.write(
                row,
                15,
                line.weighted_achivement_performace_rating or 0,
                row_format["data_number"],
            )
            row += 1

        # Add total row with enhanced styling
        sheet.merge_range(row, 0, row, 11, "Totals", formats["total_label"])
        sheet.write(
            row,
            12,
            sum(line.kpi_weightage_incentive_payout for line in lines) or 0,
            formats["total_value"],
        )
        sheet.write(
            row,
            13,
            sum(line.kpi_weightage_performace_rating for line in lines) or 0,
            formats["total_value"],
        )
        sheet.write(
            row,
            14,
            sum(line.weighted_achivement_incentive_payout for line in lines) or 0,
            formats["total_value"],
        )
        sheet.write(
            row,
            15,
            sum(line.weighted_achivement_performace_rating for line in lines) or 0,
            formats["total_value"],
        )

        # Enhanced conditional formatting with three-tier system
        if lines:
            # Good performance (4-5)
            sheet.conditional_format(
                f"L{start_row + 1}:L{row}",
                {
                    "type": "cell",
                    "criteria": ">=",
                    "value": 4,
                    "format": formats["highlight_good"],
                },
            )
            # Neutral performance (3)
            sheet.conditional_format(
                f"L{start_row + 1}:L{row}",
                {
                    "type": "cell",
                    "criteria": "==",
                    "value": 3,
                    "format": formats["highlight_middle"],
                },
            )
            # Poor performance (1-2)
            sheet.conditional_format(
                f"L{start_row + 1}:L{row}",
                {
                    "type": "cell",
                    "criteria": "<=",
                    "value": 2,
                    "format": formats["highlight_bad"],
                },
            )

        return row + 2  # Extra space after table for visual separation

    def generate_xlsx_report(self, workbook, data, objects):
        """
        Main function to generate the entire multi-sheet Excel report.
        Enhanced with improved layout, visual hierarchy, and professional styling.
        """
        formats = self._define_formats(workbook)
        colors = {
            "primary": "#1A3F6B",
            "primary_light": "#D9E2F3",
            "primary_extra_light": "#EDF2FA",
            "accent": "#3A6EA5",
            "accent_dark": "#2A4F7A",
            "total_bg": "#F5F7FA",
            "highlight_good": "#C6EFCE",
            "highlight_middle": "#FFEB9C",
            "highlight_bad": "#FFC7CE",
            "font_light": "#FFFFFF",
            "font_dark": "#333333",
            "border": "#D0D0D0",
            "section_divider": "#A0A0A0",
        }

        for obj in objects:
            # === Sheet 1: Corporate Performance ===
            sheet_corp = workbook.add_worksheet("Corporate Performance")
            sheet_corp.set_landscape()
            sheet_corp.fit_to_pages(1, 0)  # Fit to 1 page wide
            sheet_corp.set_margins(left=0.5, right=0.5, top=0.75, bottom=0.75)
            
            row = self._write_common_header(
                sheet_corp, obj, formats, "Corporate Performance Report"
            )
            
            # Add visual separation before KPIs
            sheet_corp.merge_range(
                row, 0, row, 15, "Corporate Performance KPIs", formats["section_header"]
            )
            row += 1
            sheet_corp.set_row(row, 10)  # Small spacer row
            row += 1
            
            row = self._write_performance_lines(
                sheet_corp, row, obj.corporate_performance_ids, formats, workbook
            )
            
            # Add report metadata footer
            sheet_corp.write(row + 1, 0, f"Report generated on: {fields.Date.today()}", formats["key_value"])
            sheet_corp.write(row + 1, 15, f"Page 1 of 3", formats["key_value"])

            # === Sheet 2: Individual Performance ===
            sheet_indiv = workbook.add_worksheet("Individual Performance")
            sheet_indiv.set_landscape()
            sheet_indiv.fit_to_pages(1, 0)
            sheet_indiv.set_margins(left=0.5, right=0.5, top=0.75, bottom=0.75)
            
            row = self._write_common_header(
                sheet_indiv, obj, formats, "Individual Performance Report"
            )
            
            sheet_indiv.merge_range(
                row,
                0,
                row,
                15,
                "Individual Performance KPIs",
                formats["section_header"],
            )
            row += 1
            sheet_indiv.set_row(row, 10)
            row += 1
            
            row = self._write_performance_lines(
                sheet_indiv, row, obj.individual_performance_ids, formats, workbook
            )
            
            sheet_indiv.write(row + 1, 0, f"Report generated on: {fields.Date.today()}", formats["key_value"])
            sheet_indiv.write(row + 1, 15, f"Page 2 of 3", formats["key_value"])

            # === Sheet 3: Performance Summary (Dashboard Style) ===
            sheet_summary = workbook.add_worksheet("Performance Summary")
            sheet_summary.set_portrait()
            sheet_summary.fit_to_pages(1, 0)
            sheet_summary.set_margins(left=0.75, right=0.75, top=0.75, bottom=0.75)

            # Configure layout with proper spacing
            sheet_summary.hide_gridlines(2)
            sheet_summary.set_default_row(20)
            sheet_summary.set_column("A:A", 1)  # Left margin
            sheet_summary.set_column("B:B", 35)
            sheet_summary.set_column("C:C", 25)
            sheet_summary.set_column("D:D", 25)
            sheet_summary.set_column("E:E", 2)
            sheet_summary.set_column("F:F", 25)
            sheet_summary.set_column("G:G", 1)  # Right margin

            # Header with enhanced styling
            sheet_summary.merge_range(
                "B2:F2",
                f"Performance Summary: {obj.employee_id.name}",
                formats["title"],
            )
            sheet_summary.write("G2", "Period:", formats["key_label"])
            sheet_summary.write(
                "G3", 
                f"{obj.period_start} to {obj.period_end}" if obj.period_start and obj.period_end else "",
                formats["key_value"]
            )

            # Summary of Performance - Enhanced layout
            row = 5
            sheet_summary.merge_range(
                row, 1, row, 3, "Performance Scorecard", formats["section_header"]
            )
            row += 2
            
            # Create a clean, card-like layout for summary
            sheet_summary.merge_range(
                row, 1, row, 3, "", formats["primary_extra_light"]
            )
            sheet_summary.set_row(row, 15)
            row += 1
            
            # Summary headers with improved alignment
            summary_headers = [
                "",
                "Weighted Achievement for Incentive Payout",
                "Weighted Achievement for Performance Appraisal",
            ]
            for col, header in enumerate(summary_headers):
                sheet_summary.write(row, col + 1, header, formats["summary_header"])
            row += 1
            
            # Company Performance Score
            sheet_summary.write(
                row, 1, "Company Performance Score", formats["key_label"]
            )
            sheet_summary.write(
                row,
                2,
                obj.mapped_weighted_achievement_incentive_payout or 0,
                formats["data_highlight"],
            )
            sheet_summary.write(
                row,
                3,
                obj.total_weighted_achivement_performace_rating or 0,
                formats["data_highlight"],
            )
            row += 2
            
            # Individual Performance Score
            sheet_summary.write(
                row, 1, "Individual Performance Score", formats["key_label"]
            )
            sheet_summary.write(
                row,
                2,
                obj.mapped_weighted_achievement_incentive_payout_individuals or 0,
                formats["data_highlight"],
            )
            sheet_summary.write(
                row,
                3,
                obj.total_weighted_achivement_performace_rating_individuals or 0,
                formats["data_highlight"],
            )
            row += 2
            
            # Aligned Performance Score
            sheet_summary.write(
                row,
                1,
                "Individual Score after Company Alignment",
                formats["key_label"],
            )
            sheet_summary.write(
                row,
                2,
                "N/A",
                formats["data_text_center"],
            )
            sheet_summary.write(
                row,
                3,
                obj.individual_performance_score_after_alignment or 0,
                formats["data_highlight"],
            )
            row += 3
            
            # Final Rating - Made more prominent
            sheet_summary.merge_range(
                row,
                1,
                row,
                3,
                "Final Individual Performance Rating",
                formats["section_header"],
            )
            row += 1
            sheet_summary.merge_range(
                row,
                1,
                row,
                3,
                "",
                formats["primary_extra_light"],
            )
            sheet_summary.set_row(row, 35)  # Extra height for rating display
            sheet_summary.write(
                row,
                1,
                "Rating:",
                formats["key_label"],
            )
            sheet_summary.merge_range(
                row,
                2,
                row,
                3,
                obj.final_individual_performance_rating or 0,
                formats["final_rating"],
            )
            row += 3

            # Performance Chart - Enhanced with better positioning and styling
            chart = workbook.add_chart({"type": "column", "style": 12})
            chart.add_series(
                {
                    "name": "Incentive Payout Score",
                    "categories": ["'Performance Summary'", row - 10, 1, row - 8, 1],
                    "values": ["'Performance Summary'", row - 10, 2, row - 8, 2],
                    "fill": {"color": colors["primary"]},
                    "border": {"color": colors["primary"]},
                }
            )
            chart.add_series(
                {
                    "name": "Performance Appraisal Score",
                    "categories": ["'Performance Summary'", row - 10, 1, row - 8, 1],
                    "values": ["'Performance Summary'", row - 10, 3, row - 8, 3],
                    "fill": {"color": colors["accent"]},
                    "border": {"color": colors["accent"]},
                }
            )
            chart.set_title({"name": "Performance Score Comparison", "name_font": {"size": 12, "bold": True}})
            chart.set_legend({"position": "bottom"})
            chart.set_y_axis({"major_gridlines": {"visible": False}, "min": 0})
            chart.set_size({"width": 350, "height": 200})
            chart.set_style(10)
            
            # Position chart next to the summary table
            sheet_summary.insert_chart("F6", chart)

            # Consolidated Performance Rating - Improved layout
            row += 2
            sheet_summary.merge_range(
                row,
                1,
                row,
                3,
                "Consolidated Performance Rating",
                formats["section_header"],
            )
            row += 2
            
            eval_headers = [
                "Evaluation Area",
                "Rating",
                "Weight",
                "Weighted Rating",
            ]
            # Header row
            for col, header in enumerate(eval_headers):
                sheet_summary.write(row, col + 1, header, formats["main_header"])
            row += 1
            
            # Data rows with alternating colors
            for i, line in enumerate(obj.evaluation_line_ids):
                row_format = formats["data_text_left"] if i % 2 == 0 else formats["wrap_text_section"]
                
                sheet_summary.write(
                    row, 1, line.evaluation_area or "", row_format
                )
                sheet_summary.write(
                    row, 2, line.rating or 0, formats["data_number"]
                )
                sheet_summary.write(
                    row, 3, line.weight or 0, formats["data_number"]
                )
                sheet_summary.write(
                    row, 4, line.weighted_rating or 0, formats["data_number"]
                )
                row += 1
            row += 2

            # Summary of Achievements - Card layout
            sheet_summary.merge_range(
                row, 1, row, 3, "Key Performance Highlights", formats["section_header"]
            )
            row += 2
            
            # Create a visually distinct card
            sheet_summary.merge_range(row, 1, row + 3, 3, "", formats["primary_extra_light"])
            sheet_summary.set_row(row, 15)
            
            sheet_summary.write(row, 1, "Company Score for Incentive:", formats["key_label"])
            sheet_summary.write(
                row,
                2,
                obj.mapped_weighted_achievement_incentive_payout or 0,
                formats["data_highlight"],
            )
            row += 1
            
            sheet_summary.write(row, 1, "Individual Score for Incentive:", formats["key_label"])
            sheet_summary.write(
                row,
                2,
                obj.mapped_weighted_achievement_incentive_payout_individuals or 0,
                formats["data_highlight"],
            )
            row += 1
            
            sheet_summary.write(row, 1, "Final Performance Rating:", formats["key_label"])
            sheet_summary.write(
                row,
                2,
                obj.final_individual_performance_rating or 0,
                formats["data_highlight"],
            )
            row += 3

            # Development Plans - Improved layout with priority indicators
            sheet_summary.merge_range(
                row, 1, row, 3, "Development Plans", formats["section_header"]
            )
            row += 2
            
            dev_headers = [
                "Priority",
                "Objectives",
                "Initiatives",
            ]
            for col, header in enumerate(dev_headers):
                sheet_summary.write(row, col + 1, header, formats["main_header"])
            row += 1
            
            for line in obj.development_plan_ids:
                # Priority indicator with color coding
                priority_format = formats["data_text_center"]
                if line.priority == "high":
                    priority_format = workbook.add_format({
                        **formats["data_text_center"],
                        "bg_color": colors["highlight_bad"],
                        "bold": True
                    })
                elif line.priority == "medium":
                    priority_format = workbook.add_format({
                        **formats["data_text_center"],
                        "bg_color": colors["highlight_middle"]
                    })
                elif line.priority == "low":
                    priority_format = workbook.add_format({
                        **formats["data_text_center"],
                        "bg_color": colors["highlight_good"]
                    })
                
                sheet_summary.write(
                    row, 1, line.priority or "", priority_format
                )
                sheet_summary.write(
                    row, 2, line.development_objectives or "", formats["data_text_left"]
                )
                sheet_summary.write(
                    row,
                    3,
                    line.development_initiatives or "",
                    formats["data_text_left"],
                )
                row += 1
            row += 2

            # Career Aspirations - Enhanced with better structure
            sheet_summary.merge_range(
                row,
                1,
                row,
                3,
                "Career Development Plan",
                formats["section_header"],
            )
            row += 2
            
            # 5.a
            sheet_summary.write(
                row,
                1,
                "Where would you like to be in 1-3 years:",
                formats["key_label"],
            )
            sheet_summary.merge_range(
                row + 1,
                1,
                row + 2,
                3,
                obj.five_a_career_1_3yrs or "Not specified",
                formats["wrap_text_section"],
            )
            row += 4
            
            # 5.b
            sheet_summary.write(
                row,
                1,
                "Support required from organization:",
                formats["key_label"],
            )
            sheet_summary.merge_range(
                row + 1,
                1,
                row + 2,
                3,
                obj.five_b_org_support or "Not specified",
                formats["wrap_text_section"],
            )
            row += 4
            
            # 5.c
            sheet_summary.write(
                row,
                1,
                "Expected Job Position in 1-3 years:",
                formats["key_label"],
            )
            sheet_summary.merge_range(
                row + 1,
                1,
                row + 2,
                3,
                obj.five_c_expected_job or "Not specified",
                formats["wrap_text_section"],
            )
            row += 4
            
            if obj.five_c_expected_job == "other":
                sheet_summary.write(row, 1, "Specify:", formats["key_label"])
                sheet_summary.merge_range(
                    row + 1,
                    1,
                    row + 2,
                    3,
                    obj.five_c_expected_job_specify or "Not specified",
                    formats["wrap_text_section"],
                )
                row += 4
                
            # 5.d
            sheet_summary.write(
                row,
                1,
                "Willing to relocate internationally:",
                formats["key_label"],
            )
            sheet_summary.merge_range(
                row + 1,
                1,
                row + 2,
                3,
                obj.five_d_international_mobility or "Not specified",
                formats["wrap_text_section"],
            )
            
            # Add professional footer
            row += 6
            sheet_summary.merge_range(
                row, 1, row, 3, 
                "Confidential - HR Department Use Only", 
                workbook.add_format({
                    "font_name": "Calibri",
                    "font_size": 9,
                    "font_color": "#666666",
                    "align": "center"
                })
            )
            sheet_summary.write(row + 1, 3, f"Page 3 of 3", formats["key_value"])
