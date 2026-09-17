# -*- coding: utf-8 -*-
import io

from odoo import http
from odoo.http import request


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

    @http.route('/car_wash_dashboard/reports/xlsx', type='http', auth='user', methods=['GET'], csrf=False)
    def export_xlsx(self, **params):
        import xlsxwriter

        data = self._report_data(params)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        title_fmt = workbook.add_format({'bold': True, 'font_size': 16})
        head_fmt = workbook.add_format({'bold': True, 'bg_color': '#EAF5FF', 'border': 1})
        money_fmt = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        cell_fmt = workbook.add_format({'border': 1})

        summary = workbook.add_worksheet('Summary')
        summary.write('A1', 'Crystal Clean - Report Center', title_fmt)
        summary.write('A2', 'Period')
        summary.write('B2', data['period_label'])
        row = 4
        for label, key in (
            ('Total Cars', 'total_cars'), ('Finished Cars', 'finished_cars'), ('Waiting Cars', 'waiting_cars'),
            ('Total Revenue', 'total_revenue'), ('Average Ticket', 'average_ticket'), ('Unique Customers', 'unique_customers'),
        ):
            summary.write(row, 0, label, head_fmt)
            summary.write(row, 1, data['kpis'][key], money_fmt if key in ('total_revenue', 'average_ticket') else cell_fmt)
            row += 1

        def add_sheet(name, headers, rows, keys, money_keys=()):
            sheet = workbook.add_worksheet(name[:31])
            for col, header in enumerate(headers):
                sheet.write(0, col, header, head_fmt)
            for rindex, item in enumerate(rows, start=1):
                for col, key in enumerate(keys):
                    value = item.get(key, '')
                    sheet.write(rindex, col, value if value is not False else '', money_fmt if key in money_keys else cell_fmt)
            sheet.freeze_panes(1, 0)
            sheet.autofilter(0, 0, max(1, len(rows)), len(headers) - 1)
            for col in range(len(headers)):
                sheet.set_column(col, col, 18)

        add_sheet('Operations', ['Date', 'Time', 'Ticket', 'Plate', 'Vehicle', 'Customer', 'Service', 'Station', 'Duration', 'Status'], data['operations'], ['date', 'time', 'ticket', 'plate', 'vehicle', 'customer', 'service', 'station', 'duration', 'status_label'])
        add_sheet('Services', ['Service', 'Cars', 'Revenue', 'Average Duration', 'Sales %'], data['services'], ['name', 'value', 'revenue', 'average_duration', 'sales_percent'], ('revenue',))
        add_sheet('Stations', ['Station', 'Type', 'Cars Served', 'Utilization %', 'Busy Minutes', 'Average Duration'], data['stations'], ['name', 'station_type', 'cars_served', 'utilization', 'busy_minutes', 'average_duration'])
        add_sheet('Customers', ['Customer', 'Visits', 'Total Spend', 'Average Spend', 'Last Visit', 'Top Service'], data['customers'], ['name', 'visits', 'total_spend', 'average_spend', 'last_visit', 'top_service'], ('total_spend', 'average_spend'))
        add_sheet('Supplies', ['Material', 'On Hand', 'Minimum', 'UoM', 'Remaining %'], data['supplies'], ['name', 'available_qty', 'minimum_qty', 'uom', 'remaining_percent'])
        workbook.close()
        output.seek(0)
        filename = f"crystal_clean_report_{data['date_from']}_{data['date_to']}.xlsx"
        return request.make_response(output.read(), headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', f'attachment; filename="{filename}"'),
        ])

    @http.route('/car_wash_dashboard/reports/pdf', type='http', auth='user', methods=['GET'], csrf=False)
    def export_pdf(self, **params):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        data = self._report_data(params)
        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=landscape(A4), rightMargin=10 * mm, leftMargin=10 * mm, topMargin=10 * mm, bottomMargin=10 * mm)
        styles = getSampleStyleSheet()
        story = [Paragraph('Crystal Clean - Report Center', styles['Title']), Paragraph(f"Period: {data['period_label']}", styles['Normal']), Spacer(1, 6 * mm)]
        kpis = data['kpis']
        summary_rows = [
            ['Total Cars', 'Finished', 'Waiting', 'Revenue', 'Average Ticket', 'Unique Customers'],
            [kpis['total_cars'], kpis['finished_cars'], kpis['waiting_cars'], f"{kpis['total_revenue']:.2f} {data['currency_code']}", f"{kpis['average_ticket']:.2f} {data['currency_code']}", kpis['unique_customers']],
        ]
        summary = Table(summary_rows, repeatRows=1)
        summary.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EAF5FF')), ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('PADDING', (0, 0), (-1, -1), 6)]))
        story += [summary, Spacer(1, 6 * mm), Paragraph('Wash Operations', styles['Heading2'])]
        op_rows = [['Date', 'Time', 'Ticket', 'Plate', 'Vehicle', 'Customer', 'Service', 'Station', 'Duration', 'Status']]
        for row in data['operations'][:35]:
            op_rows.append([row['date'], row['time'], row['ticket'], row['plate'], row['vehicle'], row['customer'], row['service'], row['station'], f"{row['duration']:.0f} min", row['status_label']])
        table = Table(op_rows, repeatRows=1, colWidths=[20*mm, 14*mm, 24*mm, 22*mm, 30*mm, 30*mm, 34*mm, 28*mm, 18*mm, 22*mm])
        table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0B86F9')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#D7E0EA')), ('FONTSIZE', (0, 0), (-1, -1), 7), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('PADDING', (0, 0), (-1, -1), 4)]))
        story.append(table)
        doc.build(story)
        output.seek(0)
        filename = f"crystal_clean_report_{data['date_from']}_{data['date_to']}.pdf"
        return request.make_response(output.read(), headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', f'attachment; filename="{filename}"'),
        ])
