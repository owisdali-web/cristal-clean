# -*- coding: utf-8 -*-
import html
import io
import os
from datetime import datetime

from odoo import http
from odoo.http import request
from odoo.modules.module import get_module_resource


class CarWashReportExportController(http.Controller):
    def _filters(self, params):
        return {
            'period': params.get('period') or 'today',
            'date_from': params.get('date_from') or '',
            'date_to': params.get('date_to') or '',
            'station_id': params.get('station_id') or 0,
            'service_id': params.get('service_id') or 0,
            'vehicle_size': params.get('vehicle_size') or '',
            'customer_id': params.get('customer_id') or 0,
            'status': params.get('status') or '',
        }

    def _report_data(self, params):
        return request.env['mrp.production'].sudo().get_report_center_data(self._filters(params))

    def _filter_summary(self, data):
        filters = data.get('filters') or {}
        options = data.get('filter_options') or {}

        def option_name(group, value):
            try:
                target = int(value or 0)
            except (TypeError, ValueError):
                target = 0
            for row in options.get(group, []):
                if int(row.get('id') or 0) == target:
                    return row.get('name') or str(value)
            return str(value or '')

        values = [f"Period: {data.get('period_label') or '-'}"]
        if filters.get('station_id'):
            values.append(f"Station: {option_name('stations', filters['station_id'])}")
        if filters.get('service_id'):
            values.append(f"Service: {option_name('services', filters['service_id'])}")
        if filters.get('customer_id'):
            values.append(f"Customer: {option_name('customers', filters['customer_id'])}")
        if filters.get('vehicle_size'):
            values.append(f"Vehicle Size: {str(filters['vehicle_size']).title()}")
        if filters.get('status'):
            values.append(f"Status: {str(filters['status']).replace('_', ' ').title()}")
        return ' | '.join(values)

    def _generated_meta(self, data):
        user = request.env.user
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        return {
            'generated_by': user.display_name,
            'generated_at': now,
            'filters': self._filter_summary(data),
        }

    def _logo_path(self):
        path = get_module_resource('car_wash_dashboard', 'static', 'src', 'img', 'crystal_clean_logo.png')
        return path if path and os.path.exists(path) else False

    def _management_highlights(self, data):
        services = data.get('services') or []
        stations = data.get('stations') or []
        customers = data.get('customers') or []
        supplies = data.get('supplies') or []
        exceptions = data.get('exceptions') or []
        top_service = max(services, key=lambda row: row.get('revenue', 0), default={})
        best_station = max(stations, key=lambda row: row.get('utilization', 0), default={})
        top_customer = max(customers, key=lambda row: row.get('total_spend', 0), default={})
        critical = [row for row in supplies if float(row.get('remaining_percent') or 0) <= 20]
        return {
            'top_service': top_service.get('name') or '-',
            'best_station': best_station.get('name') or '-',
            'top_customer': top_customer.get('name') or '-',
            'critical_supplies': len(critical),
            'exceptions': len(exceptions),
        }

    @http.route('/car_wash_dashboard/reports/xlsx', type='http', auth='user', methods=['GET'], csrf=False)
    def export_xlsx(self, **params):
        import xlsxwriter

        data = self._report_data(params)
        meta = self._generated_meta(data)
        highlights = self._management_highlights(data)
        currency = data.get('currency_code') or 'LYD'
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        workbook.set_properties({
            'title': 'Crystal Clean - Management Report',
            'subject': f"Car wash management report - {data.get('period_label')}",
            'author': meta['generated_by'],
            'company': 'Crystal Clean',
        })

        navy = '#0D2744'
        blue = '#178CF4'
        pale_blue = '#EAF5FF'
        green = '#18A66A'
        orange = '#F4A62A'
        red = '#D64555'
        border = '#D8E4EF'
        text = '#193B5C'
        muted = '#6C829B'
        money_code = f'#,##0.00 "{currency}"'

        title_fmt = workbook.add_format({'bold': True, 'font_size': 22, 'font_color': '#FFFFFF', 'bg_color': navy, 'align': 'left', 'valign': 'vcenter'})
        subtitle_fmt = workbook.add_format({'font_size': 10, 'font_color': '#DCEBFA', 'bg_color': navy, 'align': 'left', 'valign': 'vcenter'})
        meta_label_fmt = workbook.add_format({'bold': True, 'font_color': text, 'bg_color': '#F5F9FD', 'border': 1, 'border_color': border})
        meta_value_fmt = workbook.add_format({'font_color': text, 'bg_color': '#FFFFFF', 'border': 1, 'border_color': border})
        section_fmt = workbook.add_format({'bold': True, 'font_size': 13, 'font_color': '#FFFFFF', 'bg_color': blue, 'align': 'left', 'valign': 'vcenter'})
        header_fmt = workbook.add_format({'bold': True, 'font_color': '#FFFFFF', 'bg_color': navy, 'border': 1, 'border_color': border, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        cell_fmt = workbook.add_format({'font_color': text, 'border': 1, 'border_color': border, 'valign': 'vcenter'})
        center_fmt = workbook.add_format({'font_color': text, 'border': 1, 'border_color': border, 'align': 'center', 'valign': 'vcenter'})
        money_fmt = workbook.add_format({'font_color': text, 'border': 1, 'border_color': border, 'num_format': money_code, 'align': 'right'})
        percent_fmt = workbook.add_format({'font_color': text, 'border': 1, 'border_color': border, 'num_format': '0.0"%"', 'align': 'right'})
        total_fmt = workbook.add_format({'bold': True, 'font_color': navy, 'bg_color': '#EAF5FF', 'border': 1, 'border_color': border})
        total_money_fmt = workbook.add_format({'bold': True, 'font_color': navy, 'bg_color': '#EAF5FF', 'border': 1, 'border_color': border, 'num_format': money_code})
        kpi_label_fmt = workbook.add_format({'bold': True, 'font_color': muted, 'bg_color': '#F6FAFE', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': border})
        kpi_value_fmt = workbook.add_format({'bold': True, 'font_size': 18, 'font_color': navy, 'bg_color': '#FFFFFF', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': border})
        kpi_money_fmt = workbook.add_format({'bold': True, 'font_size': 17, 'font_color': navy, 'bg_color': '#FFFFFF', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': border, 'num_format': money_code})
        note_fmt = workbook.add_format({'font_color': muted, 'italic': True, 'font_size': 9})
        danger_fmt = workbook.add_format({'font_color': red, 'bg_color': '#FFE9EC', 'bold': True})
        warning_fmt = workbook.add_format({'font_color': '#996000', 'bg_color': '#FFF3D7', 'bold': True})
        success_fmt = workbook.add_format({'font_color': '#087447', 'bg_color': '#E4F7EE', 'bold': True})

        def setup_sheet(sheet, landscape=True):
            sheet.hide_gridlines(2)
            sheet.set_landscape() if landscape else sheet.set_portrait()
            sheet.set_paper(9)
            sheet.fit_to_pages(1, 0)
            sheet.set_margins(0.35, 0.35, 0.55, 0.55)
            sheet.set_header('&LCrystal Clean&RManagement Report')
            sheet.set_footer(f'&L{data.get("period_label", "")}&RPage &P of &N')

        def write_report_header(sheet, title, last_col):
            setup_sheet(sheet)
            sheet.set_row(0, 28)
            sheet.set_row(1, 22)
            sheet.merge_range(0, 1, 0, last_col, title, title_fmt)
            sheet.merge_range(1, 1, 1, last_col, f"{data.get('period_label', '')}  |  {meta['filters']}", subtitle_fmt)
            logo = self._logo_path()
            if logo:
                try:
                    sheet.insert_image(0, 0, logo, {'x_scale': 0.09, 'y_scale': 0.09, 'x_offset': 4, 'y_offset': 2, 'object_position': 1})
                except Exception:
                    pass
            sheet.write(2, 0, 'Generated By', meta_label_fmt)
            sheet.write(2, 1, meta['generated_by'], meta_value_fmt)
            sheet.write(2, 2, 'Generated At', meta_label_fmt)
            sheet.write(2, 3, meta['generated_at'], meta_value_fmt)
            if last_col >= 5:
                sheet.write(2, 4, 'Applied Filters', meta_label_fmt)
                if last_col > 5:
                    sheet.merge_range(2, 5, 2, last_col, meta['filters'], meta_value_fmt)
                else:
                    sheet.write(2, 5, meta['filters'], meta_value_fmt)

        def add_table_sheet(name, title, headers, rows, keys, money_keys=(), percent_keys=(), widths=None, conditional=None):
            sheet = workbook.add_worksheet(name[:31])
            last_col = max(1, len(headers) - 1)
            write_report_header(sheet, title, last_col)
            start_row = 5
            sheet.set_row(start_row, 26)
            for col, header in enumerate(headers):
                sheet.write(start_row, col, header, header_fmt)
            for rindex, item in enumerate(rows, start=start_row + 1):
                for col, key in enumerate(keys):
                    value = item.get(key, '')
                    if value is False or value is None:
                        value = ''
                    fmt = money_fmt if key in money_keys else percent_fmt if key in percent_keys else center_fmt if isinstance(value, (int, float)) else cell_fmt
                    sheet.write(rindex, col, value, fmt)
            end_row = start_row + max(1, len(rows))
            sheet.freeze_panes(start_row + 1, 0)
            sheet.autofilter(start_row, 0, end_row, last_col)
            if widths:
                for col, width in enumerate(widths):
                    sheet.set_column(col, col, width)
            else:
                for col in range(len(headers)):
                    sheet.set_column(col, col, 18)
            if conditional:
                conditional(sheet, start_row + 1, end_row)
            return sheet, start_row, end_row

        # Executive Summary
        summary = workbook.add_worksheet('Executive Summary')
        setup_sheet(summary, landscape=True)
        summary.set_column('A:A', 4)
        summary.set_column('B:I', 16)
        summary.set_column('B:B', 24)
        summary.set_column('F:F', 24)
        summary.set_column('J:N', 12)
        summary.merge_range('B1:I2', 'Crystal Clean - Management Report', title_fmt)
        summary.merge_range('B3:I3', f"Executive Summary | {data.get('period_label', '')}", subtitle_fmt)
        logo = self._logo_path()
        if logo:
            try:
                summary.insert_image('A1', logo, {'x_scale': 0.11, 'y_scale': 0.11, 'x_offset': 2, 'y_offset': 2})
            except Exception:
                pass
        summary.write('B5', 'Generated By', meta_label_fmt)
        summary.write('C5', meta['generated_by'], meta_value_fmt)
        summary.write('D5', 'Generated At', meta_label_fmt)
        summary.write('E5', meta['generated_at'], meta_value_fmt)
        summary.write('F5', 'Applied Filters', meta_label_fmt)
        summary.merge_range('G5:I5', meta['filters'], meta_value_fmt)
        kpis = data.get('kpis') or {}
        kpi_specs = [
            ('Total Cars', 'total_cars', False), ('Finished Cars', 'finished_cars', False), ('Waiting Cars', 'waiting_cars', False),
            ('Total Revenue', 'total_revenue', True), ('Average Ticket', 'average_ticket', True), ('Unique Customers', 'unique_customers', False),
        ]
        for idx, (label, key, is_money) in enumerate(kpi_specs):
            col = 1 + (idx % 3) * 3
            row = 7 + (idx // 3) * 3
            summary.merge_range(row, col, row, col + 1, label, kpi_label_fmt)
            summary.merge_range(row + 1, col, row + 2, col + 1, kpis.get(key, 0), kpi_money_fmt if is_money else kpi_value_fmt)
        summary.merge_range('B15:I15', 'Management Highlights', section_fmt)
        highlight_rows = [
            ('Top Service by Revenue', highlights['top_service']), ('Highest Utilization Station', highlights['best_station']),
            ('Top Customer by Spend', highlights['top_customer']), ('Critical Supplies', highlights['critical_supplies']),
            ('Exceptions / Delays', highlights['exceptions']),
        ]
        for ridx, (label, value) in enumerate(highlight_rows, start=15):
            summary.write(ridx, 1, label, meta_label_fmt)
            summary.merge_range(ridx, 2, ridx, 4, value, meta_value_fmt)
        summary.write(21, 1, 'Revenue Trend', section_fmt)
        summary.write(21, 2, 'Revenue', section_fmt)
        for i, row in enumerate(data.get('revenue_trend') or [], start=22):
            summary.write(i, 1, row.get('label'), cell_fmt)
            summary.write(i, 2, row.get('value', 0), money_fmt)
        summary.write(21, 4, 'Payment Method', section_fmt)
        summary.write(21, 5, 'Amount', section_fmt)
        for i, row in enumerate(data.get('payment_methods') or [], start=22):
            summary.write(i, 4, row.get('name'), cell_fmt)
            summary.write(i, 5, row.get('amount', 0), money_fmt)
        if data.get('revenue_trend'):
            chart = workbook.add_chart({'type': 'column'})
            chart.add_series({
                'name': 'Revenue',
                'categories': f"='Executive Summary'!$B$23:$B${22 + len(data['revenue_trend'])}",
                'values': f"='Executive Summary'!$C$23:$C${22 + len(data['revenue_trend'])}",
                'fill': {'color': blue}, 'border': {'none': True},
            })
            chart.set_title({'name': 'Revenue Trend'})
            chart.set_legend({'none': True})
            chart.set_style(10)
            summary.insert_chart('H15', chart, {'x_scale': 1.2, 'y_scale': 1.0})
        if data.get('payment_methods'):
            pie = workbook.add_chart({'type': 'doughnut'})
            pie.add_series({
                'name': 'Payment Methods',
                'categories': f"='Executive Summary'!$E$23:$E${22 + len(data['payment_methods'])}",
                'values': f"='Executive Summary'!$F$23:$F${22 + len(data['payment_methods'])}",
                'data_labels': {'percentage': True},
            })
            pie.set_title({'name': 'Payment Methods'})
            pie.set_hole_size(55)
            summary.insert_chart('H31', pie, {'x_scale': 1.1, 'y_scale': 1.0})
        summary.freeze_panes(5, 1)
        summary.write('B40', 'Official revenue source: paid Point of Sale orders.', note_fmt)

        # Operations
        def op_conditional(sheet, first, last):
            if last >= first:
                sheet.conditional_format(first, 9, last, 9, {'type': 'text', 'criteria': 'containing', 'value': 'Finished', 'format': success_fmt})
                sheet.conditional_format(first, 9, last, 9, {'type': 'text', 'criteria': 'containing', 'value': 'Cancelled', 'format': danger_fmt})
                sheet.conditional_format(first, 9, last, 9, {'type': 'text', 'criteria': 'containing', 'value': 'Progress', 'format': warning_fmt})
        operations_sheet, _, _ = add_table_sheet(
            'Operations', 'Wash Operations',
            ['Date', 'Time', 'Ticket', 'Plate', 'Vehicle', 'Customer', 'Service', 'Station', 'Duration (min)', 'Status'],
            data.get('operations') or [],
            ['date', 'time', 'ticket', 'plate', 'vehicle', 'customer', 'service', 'station', 'duration', 'status_label'],
            widths=[13, 9, 18, 15, 22, 24, 26, 22, 14, 14], conditional=op_conditional,
        )
        operations_sheet.write(len(data.get('operations') or []) + 7, 7, 'Total Operations', total_fmt)
        operations_sheet.write(len(data.get('operations') or []) + 7, 8, len(data.get('operations') or []), total_fmt)

        # Revenue & Payments
        revenue_sheet = workbook.add_worksheet('Revenue & Payments')
        write_report_header(revenue_sheet, 'Revenue & Payments', 8)
        revenue_sheet.set_column('A:A', 13); revenue_sheet.set_column('B:B', 9); revenue_sheet.set_column('C:C', 22)
        revenue_sheet.set_column('D:D', 24); revenue_sheet.set_column('E:E', 28); revenue_sheet.set_column('F:G', 12); revenue_sheet.set_column('H:H', 16); revenue_sheet.set_column('I:I', 24)
        tx_headers = ['Date', 'Time', 'POS Order', 'Customer', 'Service', 'Qty', 'Unit Price', 'Amount', 'Payment Method']
        for col, header in enumerate(tx_headers):
            revenue_sheet.write(5, col, header, header_fmt)
        for ridx, item in enumerate(data.get('transactions') or [], start=6):
            values = [item.get('date'), item.get('time'), item.get('order_name'), item.get('customer'), item.get('service'), item.get('qty'), item.get('unit_price'), item.get('amount'), item.get('payment_method_label')]
            for col, value in enumerate(values):
                fmt = money_fmt if col in (6, 7) else center_fmt if col == 5 else cell_fmt
                revenue_sheet.write(ridx, col, value if value is not False else '', fmt)
        tx_end = 5 + max(1, len(data.get('transactions') or []))
        revenue_sheet.freeze_panes(6, 0)
        revenue_sheet.autofilter(5, 0, tx_end, 8)
        summary_col = 10
        revenue_sheet.write(5, summary_col, 'Payment Method', header_fmt); revenue_sheet.write(5, summary_col + 1, 'Amount', header_fmt)
        for i, row in enumerate(data.get('payment_methods') or [], start=6):
            revenue_sheet.write(i, summary_col, row.get('name'), cell_fmt); revenue_sheet.write(i, summary_col + 1, row.get('amount', 0), money_fmt)
        revenue_sheet.write(5, summary_col + 3, 'Period', header_fmt); revenue_sheet.write(5, summary_col + 4, 'Revenue', header_fmt)
        for i, row in enumerate(data.get('revenue_trend') or [], start=6):
            revenue_sheet.write(i, summary_col + 3, row.get('label'), cell_fmt); revenue_sheet.write(i, summary_col + 4, row.get('value', 0), money_fmt)
        if data.get('payment_methods'):
            pie = workbook.add_chart({'type': 'doughnut'})
            pie.add_series({'categories': f"='Revenue & Payments'!$K$7:$K${6 + len(data['payment_methods'])}", 'values': f"='Revenue & Payments'!$L$7:$L${6 + len(data['payment_methods'])}", 'data_labels': {'percentage': True}})
            pie.set_title({'name': 'Payment Mix'}); pie.set_hole_size(55)
            revenue_sheet.insert_chart('K15', pie, {'x_scale': 1.0, 'y_scale': 0.9})
        if data.get('revenue_trend'):
            chart = workbook.add_chart({'type': 'line'})
            chart.add_series({'name': 'Revenue', 'categories': f"='Revenue & Payments'!$N$7:$N${6 + len(data['revenue_trend'])}", 'values': f"='Revenue & Payments'!$O$7:$O${6 + len(data['revenue_trend'])}", 'line': {'color': blue, 'width': 2.25}, 'marker': {'type': 'circle', 'size': 5, 'border': {'color': blue}, 'fill': {'color': '#FFFFFF'}}})
            chart.set_title({'name': 'Revenue Trend'}); chart.set_legend({'none': True})
            revenue_sheet.insert_chart('N15', chart, {'x_scale': 1.15, 'y_scale': 0.9})
        revenue_sheet.write(tx_end + 2, 6, 'Total Revenue', total_fmt); revenue_sheet.write(tx_end + 2, 7, data.get('kpis', {}).get('total_revenue', 0), total_money_fmt)

        def service_conditional(sheet, first, last):
            if last >= first:
                sheet.conditional_format(first, 2, last, 2, {'type': 'data_bar', 'bar_color': blue})
                sheet.conditional_format(first, 4, last, 4, {'type': 'data_bar', 'bar_color': green})
        add_table_sheet('Services', 'Services Performance', ['Service', 'Times Sold', 'Revenue', 'Average Duration', 'Sales %'], data.get('services') or [], ['name', 'value', 'revenue', 'average_duration', 'sales_percent'], money_keys=('revenue',), percent_keys=('sales_percent',), widths=[30, 14, 18, 20, 14], conditional=service_conditional)

        def station_conditional(sheet, first, last):
            if last >= first:
                sheet.conditional_format(first, 3, last, 3, {'type': 'data_bar', 'bar_color': blue})
        add_table_sheet('Stations', 'Station Performance', ['Station', 'Type', 'Cars Served', 'Utilization %', 'Busy Minutes', 'Average Duration'], data.get('stations') or [], ['name', 'station_type', 'cars_served', 'utilization', 'busy_minutes', 'average_duration'], percent_keys=('utilization',), widths=[28, 16, 14, 16, 16, 18], conditional=station_conditional)

        def customer_conditional(sheet, first, last):
            if last >= first:
                sheet.conditional_format(first, 2, last, 2, {'type': 'data_bar', 'bar_color': green})
        add_table_sheet('Customers', 'Customer Performance', ['Customer', 'Visits', 'Total Spend', 'Average Spend', 'Last Visit', 'Most Used Service'], data.get('customers') or [], ['name', 'visits', 'total_spend', 'average_spend', 'last_visit', 'top_service'], money_keys=('total_spend', 'average_spend'), widths=[28, 12, 18, 18, 20, 30], conditional=customer_conditional)

        def supply_conditional(sheet, first, last):
            if last >= first:
                sheet.conditional_format(first, 4, last, 4, {'type': '3_color_scale', 'min_color': '#F8696B', 'mid_color': '#FFEB84', 'max_color': '#63BE7B'})
        add_table_sheet('Supplies', 'Cleaning Supplies', ['Material', 'On Hand', 'Minimum', 'UoM', 'Remaining %'], data.get('supplies') or [], ['name', 'available_qty', 'minimum_qty', 'uom', 'remaining_percent'], percent_keys=('remaining_percent',), widths=[38, 14, 14, 12, 16], conditional=supply_conditional)

        def exception_conditional(sheet, first, last):
            if last >= first:
                sheet.conditional_format(first, 0, last, 3, {'type': 'text', 'criteria': 'containing', 'value': 'cancelled', 'format': danger_fmt})
                sheet.conditional_format(first, 0, last, 3, {'type': 'text', 'criteria': 'containing', 'value': 'overdue', 'format': warning_fmt})
        add_table_sheet('Exceptions', 'Exceptions & Delays', ['Type', 'Reference', 'Vehicle', 'Issue'], data.get('exceptions') or [], ['type', 'reference', 'detail', 'message'], widths=[16, 22, 18, 48], conditional=exception_conditional)

        workbook.close()
        output.seek(0)
        filename = f"crystal_clean_management_report_{data['date_from']}_{data['date_to']}.xlsx"
        return request.make_response(output.read(), headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', f'attachment; filename="{filename}"'),
            ('Cache-Control', 'no-store'),
        ])

    def _pdf_font_name(self):
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        candidates = [
            ('CrystalCleanUnicode', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
            ('CrystalCleanUnicode', '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'),
        ]
        for name, path in candidates:
            if os.path.exists(path):
                try:
                    if name not in pdfmetrics.getRegisteredFontNames():
                        pdfmetrics.registerFont(TTFont(name, path))
                    return name
                except Exception:
                    continue
        return 'Helvetica'

    @http.route('/car_wash_dashboard/reports/pdf', type='http', auth='user', methods=['GET'], csrf=False)
    def export_pdf(self, **params):
        from reportlab.graphics.charts.barcharts import VerticalBarChart
        from reportlab.graphics.charts.piecharts import Pie
        from reportlab.graphics.shapes import Drawing, String
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        data = self._report_data(params)
        meta = self._generated_meta(data)
        highlights = self._management_highlights(data)
        currency = data.get('currency_code') or 'LYD'
        font_name = self._pdf_font_name()
        output = io.BytesIO()

        def on_page(canvas, doc):
            width, height = landscape(A4)
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor('#D9E5EF'))
            canvas.line(12 * mm, 9 * mm, width - 12 * mm, 9 * mm)
            canvas.setFont(font_name, 7.5)
            canvas.setFillColor(colors.HexColor('#56718C'))
            canvas.drawString(12 * mm, 5.2 * mm, f"Crystal Clean | {data.get('period_label', '')}")
            canvas.drawRightString(width - 12 * mm, 5.2 * mm, f"Page {canvas.getPageNumber()} | Generated {meta['generated_at']}")
            canvas.restoreState()

        doc = SimpleDocTemplate(
            output, pagesize=landscape(A4), rightMargin=12 * mm, leftMargin=12 * mm,
            topMargin=12 * mm, bottomMargin=14 * mm,
            title='Crystal Clean - Management Report', author=meta['generated_by'],
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('CwTitle', parent=styles['Title'], fontName=font_name, fontSize=23, leading=27, textColor=colors.HexColor('#0D2744'), alignment=TA_LEFT, spaceAfter=4)
        subtitle_style = ParagraphStyle('CwSubtitle', parent=styles['Normal'], fontName=font_name, fontSize=9, leading=12, textColor=colors.HexColor('#607A94'), spaceAfter=6)
        section_style = ParagraphStyle('CwSection', parent=styles['Heading2'], fontName=font_name, fontSize=15, leading=18, textColor=colors.HexColor('#0D2744'), spaceBefore=4, spaceAfter=7)
        small_style = ParagraphStyle('CwSmall', parent=styles['Normal'], fontName=font_name, fontSize=7.5, leading=10, textColor=colors.HexColor('#294B6D'))
        center_style = ParagraphStyle('CwCenter', parent=small_style, alignment=TA_CENTER)
        story = []

        logo = self._logo_path()
        brand = []
        if logo:
            try:
                brand.append(Image(logo, width=18 * mm, height=18 * mm))
            except Exception:
                brand.append(Paragraph('Crystal Clean', title_style))
        else:
            brand.append(Paragraph('Crystal Clean', title_style))
        brand.append(Paragraph('<b>Crystal Clean - Management Report</b><br/><font size="9">Complete car wash management overview</font>', title_style))
        brand_table = Table([brand], colWidths=[22 * mm, 230 * mm] if len(brand) == 2 else [252 * mm])
        brand_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F5FAFF')), ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#D9E7F3')), ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8), ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
        story += [brand_table, Spacer(1, 4 * mm), Paragraph('Executive Summary', section_style), Paragraph(f"<b>Period:</b> {html.escape(data.get('period_label') or '-')}<br/><b>Generated By:</b> {html.escape(meta['generated_by'])} &nbsp;&nbsp; <b>Generated At:</b> {meta['generated_at']}<br/><b>Applied Filters:</b> {html.escape(meta['filters'])}", subtitle_style)]

        kpis = data.get('kpis') or {}
        kpi_rows = [
            ['Total Cars', 'Finished Cars', 'Waiting Cars', 'Total Revenue', 'Average Ticket', 'Unique Customers'],
            [kpis.get('total_cars', 0), kpis.get('finished_cars', 0), kpis.get('waiting_cars', 0), f"{kpis.get('total_revenue', 0):,.2f} {currency}", f"{kpis.get('average_ticket', 0):,.2f} {currency}", kpis.get('unique_customers', 0)],
        ]
        kpi_table = Table(kpi_rows, repeatRows=1, colWidths=[42 * mm] * 6)
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0D2744')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#F3F9FF')), ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#0D2744')),
            ('FONTNAME', (0, 0), (-1, -1), font_name), ('FONTSIZE', (0, 0), (-1, 0), 8), ('FONTSIZE', (0, 1), (-1, 1), 12),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.45, colors.HexColor('#D4E1EC')), ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ]))
        story += [kpi_table, Spacer(1, 4 * mm)]
        highlight_data = [
            ['Top Service', highlights['top_service'], 'Highest Utilization Station', highlights['best_station']],
            ['Top Customer', highlights['top_customer'], 'Critical Supplies', highlights['critical_supplies']],
            ['Exceptions / Delays', highlights['exceptions'], 'Official Revenue Source', 'Paid POS Orders'],
        ]
        highlight_table = Table(highlight_data, colWidths=[42 * mm, 78 * mm, 50 * mm, 82 * mm])
        highlight_table.setStyle(TableStyle([('FONTNAME', (0, 0), (-1, -1), font_name), ('FONTNAME', (0, 0), (0, -1), font_name), ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#EAF5FF')), ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#EAF5FF')), ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#214664')), ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#D9E5EF')), ('FONTSIZE', (0, 0), (-1, -1), 7.5), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
        story += [highlight_table, PageBreak(), Paragraph('Revenue & Payments', section_style)]

        charts = []
        trend = data.get('revenue_trend') or []
        if trend:
            drawing = Drawing(360, 180)
            chart = VerticalBarChart()
            chart.x = 36; chart.y = 32; chart.height = 120; chart.width = 285
            chart.data = [[float(row.get('value') or 0) for row in trend]]
            chart.categoryAxis.categoryNames = [str(row.get('label') or '') for row in trend]
            chart.valueAxis.valueMin = 0
            chart.bars[0].fillColor = colors.HexColor('#178CF4')
            chart.bars[0].strokeColor = colors.HexColor('#178CF4')
            chart.categoryAxis.labels.fontName = font_name; chart.categoryAxis.labels.fontSize = 6
            chart.valueAxis.labels.fontName = font_name; chart.valueAxis.labels.fontSize = 6
            drawing.add(String(36, 162, 'Revenue Trend', fontName=font_name, fontSize=10, fillColor=colors.HexColor('#0D2744')))
            drawing.add(chart)
            charts.append(drawing)
        payments = data.get('payment_methods') or []
        if payments:
            drawing = Drawing(260, 180)
            pie = Pie()
            pie.x = 42; pie.y = 26; pie.width = 120; pie.height = 120
            pie.data = [float(row.get('amount') or 0) for row in payments]
            pie.labels = [str(row.get('name') or '') for row in payments]
            pie.slices.strokeWidth = 0.5
            drawing.add(String(42, 162, 'Payment Methods', fontName=font_name, fontSize=10, fillColor=colors.HexColor('#0D2744')))
            drawing.add(pie)
            charts.append(drawing)
        if charts:
            story.append(Table([charts], colWidths=[125 * mm] * len(charts)))
            story.append(Spacer(1, 4 * mm))
        payment_rows = [['Payment Method', 'Amount']] + [[row.get('name'), f"{float(row.get('amount') or 0):,.2f} {currency}"] for row in payments]
        payment_table = Table(payment_rows, repeatRows=1, colWidths=[80 * mm, 55 * mm])
        payment_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#178CF4')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('FONTNAME', (0, 0), (-1, -1), font_name), ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#D9E5EF')), ('FONTSIZE', (0, 0), (-1, -1), 7.5), ('ALIGN', (1, 1), (1, -1), 'RIGHT'), ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
        story += [payment_table, PageBreak(), Paragraph('Wash Operations', section_style)]

        op_headers = ['Date', 'Time', 'Ticket', 'Plate', 'Vehicle', 'Customer', 'Service', 'Station', 'Duration', 'Status']
        op_rows = [op_headers]
        for row in data.get('operations') or []:
            op_rows.append([row.get('date'), row.get('time'), row.get('ticket'), row.get('plate'), row.get('vehicle'), row.get('customer'), row.get('service'), row.get('station'), f"{float(row.get('duration') or 0):.0f} min", row.get('status_label')])
        op_table = Table(op_rows, repeatRows=1, colWidths=[19*mm, 13*mm, 22*mm, 20*mm, 27*mm, 29*mm, 32*mm, 27*mm, 17*mm, 20*mm])
        op_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0D2744')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('FONTNAME', (0, 0), (-1, -1), font_name), ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#D7E2EC')), ('FONTSIZE', (0, 0), (-1, -1), 6.2), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
        story += [op_table, PageBreak(), Paragraph('Service Performance', section_style)]

        service_rows = [['Service', 'Times Sold', 'Revenue', 'Average Duration', '% of Sales']]
        for row in data.get('services') or []:
            service_rows.append([row.get('name'), row.get('value'), f"{float(row.get('revenue') or 0):,.2f} {currency}", f"{float(row.get('average_duration') or 0):.1f} min", f"{float(row.get('sales_percent') or 0):.1f}%"])
        service_table = Table(service_rows, repeatRows=1, colWidths=[78*mm, 35*mm, 45*mm, 45*mm, 35*mm])
        service_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#178CF4')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('FONTNAME', (0, 0), (-1, -1), font_name), ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#D9E5EF')), ('FONTSIZE', (0, 0), (-1, -1), 7.2), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
        story += [service_table, PageBreak(), Paragraph('Station Performance', section_style)]

        station_rows = [['Station', 'Type', 'Cars Served', 'Utilization', 'Busy Minutes', 'Average Duration']]
        for row in data.get('stations') or []:
            station_rows.append([row.get('name'), row.get('station_type'), row.get('cars_served'), f"{float(row.get('utilization') or 0):.1f}%", f"{float(row.get('busy_minutes') or 0):.1f}", f"{float(row.get('average_duration') or 0):.1f} min"])
        station_table = Table(station_rows, repeatRows=1, colWidths=[65*mm, 38*mm, 32*mm, 35*mm, 38*mm, 42*mm])
        station_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0D2744')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('FONTNAME', (0, 0), (-1, -1), font_name), ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#D9E5EF')), ('FONTSIZE', (0, 0), (-1, -1), 7.2), ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
        story += [station_table, PageBreak(), Paragraph('Top Customers', section_style)]

        customer_rows = [['Customer', 'Visits', 'Total Spend', 'Average Spend', 'Last Visit', 'Most Used Service']]
        for row in (data.get('customers') or [])[:30]:
            customer_rows.append([row.get('name'), row.get('visits'), f"{float(row.get('total_spend') or 0):,.2f} {currency}", f"{float(row.get('average_spend') or 0):,.2f} {currency}", row.get('last_visit'), row.get('top_service')])
        customer_table = Table(customer_rows, repeatRows=1, colWidths=[60*mm, 25*mm, 38*mm, 38*mm, 42*mm, 55*mm])
        customer_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#178CF4')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('FONTNAME', (0, 0), (-1, -1), font_name), ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#D9E5EF')), ('FONTSIZE', (0, 0), (-1, -1), 7.2), ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
        story += [customer_table, PageBreak(), Paragraph('Supplies & Exceptions', section_style)]

        supply_rows = [['Material', 'On Hand', 'Minimum', 'UoM', 'Remaining']]
        for row in data.get('supplies') or []:
            supply_rows.append([row.get('name'), row.get('available_qty'), row.get('minimum_qty'), row.get('uom'), f"{float(row.get('remaining_percent') or 0):.1f}%"])
        supply_table = Table(supply_rows, repeatRows=1, colWidths=[100*mm, 32*mm, 32*mm, 28*mm, 35*mm])
        supply_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0D2744')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('FONTNAME', (0, 0), (-1, -1), font_name), ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#D9E5EF')), ('FONTSIZE', (0, 0), (-1, -1), 7.2), ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
        story += [supply_table, Spacer(1, 5 * mm)]
        exception_rows = [['Type', 'Reference', 'Vehicle', 'Issue']]
        for row in data.get('exceptions') or []:
            exception_rows.append([row.get('type'), row.get('reference'), row.get('detail'), row.get('message')])
        exception_table = Table(exception_rows, repeatRows=1, colWidths=[35*mm, 45*mm, 42*mm, 120*mm])
        exception_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#D64555')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('FONTNAME', (0, 0), (-1, -1), font_name), ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#D9E5EF')), ('FONTSIZE', (0, 0), (-1, -1), 7.2), ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
        story.append(exception_table)

        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        output.seek(0)
        filename = f"crystal_clean_management_report_{data['date_from']}_{data['date_to']}.pdf"
        return request.make_response(output.read(), headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', f'attachment; filename="{filename}"'),
            ('Cache-Control', 'no-store'),
        ])

    def _html_table(self, headers, rows):
        head = ''.join(f'<th>{html.escape(str(value))}</th>' for value in headers)
        body = []
        for row in rows:
            body.append('<tr>' + ''.join(f'<td>{html.escape(str(value if value is not None else ""))}</td>' for value in row) + '</tr>')
        return f'<table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>'

    @http.route('/car_wash_dashboard/reports/print', type='http', auth='user', methods=['GET'], csrf=False)
    def print_report(self, **params):
        data = self._report_data(params)
        meta = self._generated_meta(data)
        kpis = data.get('kpis') or {}
        operations = [[row.get('date'), row.get('time'), row.get('ticket'), row.get('plate'), row.get('vehicle'), row.get('customer'), row.get('service'), row.get('station'), f"{float(row.get('duration') or 0):.0f} min", row.get('status_label')] for row in data.get('operations') or []]
        services = [[row.get('name'), row.get('value'), f"{float(row.get('revenue') or 0):,.2f} {data.get('currency_code')}", f"{float(row.get('average_duration') or 0):.1f} min", f"{float(row.get('sales_percent') or 0):.1f}%"] for row in data.get('services') or []]
        stations = [[row.get('name'), row.get('station_type'), row.get('cars_served'), f"{float(row.get('utilization') or 0):.1f}%", f"{float(row.get('average_duration') or 0):.1f} min"] for row in data.get('stations') or []]
        customers = [[row.get('name'), row.get('visits'), f"{float(row.get('total_spend') or 0):,.2f} {data.get('currency_code')}", row.get('last_visit'), row.get('top_service')] for row in data.get('customers') or []]
        payments = [[row.get('name'), f"{float(row.get('amount') or 0):,.2f} {data.get('currency_code')}"] for row in data.get('payment_methods') or []]
        supplies = [[row.get('name'), row.get('available_qty'), row.get('minimum_qty'), row.get('uom'), f"{float(row.get('remaining_percent') or 0):.1f}%"] for row in data.get('supplies') or []]
        exceptions = [[row.get('type'), row.get('reference'), row.get('detail'), row.get('message')] for row in data.get('exceptions') or []]
        page = f'''<!doctype html>
<html><head><meta charset="utf-8"/><title>Crystal Clean - Management Report</title>
<style>
@page {{ size: A4 landscape; margin: 12mm; }}
body {{ font-family: Arial, sans-serif; color:#173b5d; margin:0; background:#fff; }}
header {{ display:flex; justify-content:space-between; align-items:flex-start; border-bottom:3px solid #178cf4; padding-bottom:10px; margin-bottom:14px; }}
h1 {{ margin:0; color:#0d2744; font-size:26px; }} .meta {{ color:#607a94; font-size:11px; line-height:1.55; text-align:right; }}
.kpis {{ display:grid; grid-template-columns:repeat(6,1fr); gap:8px; margin:12px 0 18px; }} .kpi {{ border:1px solid #d9e5ef; border-radius:9px; padding:10px; text-align:center; background:#f6fbff; }} .kpi b {{ display:block; font-size:20px; color:#0d2744; margin-top:4px; }}
h2 {{ color:#0d2744; font-size:16px; margin:18px 0 8px; }} table {{ width:100%; border-collapse:collapse; font-size:9px; margin-bottom:15px; }} th {{ background:#0d2744; color:white; padding:6px; text-align:left; }} td {{ border:1px solid #dbe6ef; padding:5px; }} tr:nth-child(even) td {{ background:#f8fbfe; }}
.actions {{ display:none; }} @media print {{ .actions {{ display:none!important; }} }}
</style></head><body>
<header><div><h1>Crystal Clean - Management Report</h1><div>{html.escape(data.get('period_label') or '')}</div></div><div class="meta">Generated By: {html.escape(meta['generated_by'])}<br/>Generated At: {meta['generated_at']}<br/>{html.escape(meta['filters'])}</div></header>
<section class="kpis">
<div class="kpi">Total Cars<b>{kpis.get('total_cars',0)}</b></div><div class="kpi">Finished<b>{kpis.get('finished_cars',0)}</b></div><div class="kpi">Waiting<b>{kpis.get('waiting_cars',0)}</b></div><div class="kpi">Revenue<b>{kpis.get('total_revenue',0):,.2f} {data.get('currency_code')}</b></div><div class="kpi">Average Ticket<b>{kpis.get('average_ticket',0):,.2f}</b></div><div class="kpi">Customers<b>{kpis.get('unique_customers',0)}</b></div>
</section>
<h2>Revenue &amp; Payment Methods</h2>{self._html_table(['Payment Method','Amount'], payments)}
<h2>Wash Operations</h2>{self._html_table(['Date','Time','Ticket','Plate','Vehicle','Customer','Service','Station','Duration','Status'], operations)}
<h2>Service Performance</h2>{self._html_table(['Service','Times Sold','Revenue','Avg Duration','Sales %'], services)}
<h2>Station Performance</h2>{self._html_table(['Station','Type','Cars Served','Utilization','Avg Duration'], stations)}
<h2>Top Customers</h2>{self._html_table(['Customer','Visits','Total Spend','Last Visit','Most Used Service'], customers)}
<h2>Cleaning Supplies</h2>{self._html_table(['Material','On Hand','Minimum','UoM','Remaining'], supplies)}
<h2>Exceptions &amp; Delays</h2>{self._html_table(['Type','Reference','Vehicle','Issue'], exceptions)}
<script>window.addEventListener('load', () => setTimeout(() => window.print(), 250));</script>
</body></html>'''
        return request.make_response(page, headers=[('Content-Type', 'text/html; charset=utf-8'), ('Cache-Control', 'no-store')])
