# -*- coding: utf-8 -*-

import io
import xlsxwriter
from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    def get_invoice_lines_report(self, response, records):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        title_style = workbook.add_format({'font_name': 'Times', 'font_size': 14, 'bold': True, 'align': 'center'})
        total_style = workbook.add_format(
            {'font_name': 'Times', 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'right'})
        header_style = workbook.add_format(
            {'font_name': 'Times', 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'center'})
        text_style = workbook.add_format(
            {'font_name': 'Times', 'left': 1, 'bottom': 1, 'right': 1, 'top': 1, 'align': 'left'})
        sheet = workbook.add_worksheet(name='Invoice Items  in Excel')
        sheet.set_column('A1:H1', 25)
        sheet.merge_range('A1:H1', 'Automated Report For All Invoice Items ', title_style)
        sheet.write(1, 0, 'Invoice Number', header_style)
        sheet.write(1, 1, 'Date', header_style)
        sheet.write(1, 2, 'Partner', header_style)
        sheet.write(1, 3, 'Partner Medical Card', header_style)
        sheet.write(1, 4, 'Service', header_style)
        sheet.write(1, 5, 'Service Arabic Name', header_style)
        sheet.write(1, 6, 'Total Price For Line', header_style)
        sheet.write(1, 7, 'Total For Invoice', header_style)
        sheet.write(1, 8, 'Paid', header_style)
        sheet.write(1, 9, 'Due Amount', header_style)

        row = 2
        number = 1
        amount_total = 0.0
        paid = 0.0
        amount_residual = 0.0
        for record in records:
            for line in record.invoice_line_ids:
                ##############################################
                sheet.write(row, 0, record.name, text_style)

                ###############################
                sheet.write_url(row, 1, fields.Date.to_string(record.invoice_date) if record.invoice_date else " ",
                                text_style)
                #########################
                sheet.write(row, 2, record.partner_id.name,
                            text_style)
                ######################
                # paso change - studio field
                # sheet.write(row, 3,
                #             record.partner_id.x_studio_medical_card_number if record.partner_id.x_studio_medical_card_number else ' ',
                #             text_style)
                ######################
                sheet.write(row, 4, line.product_id.name,
                            text_style)
                ######################
                # paso change - studio field
                # sheet.write(row, 5,
                #             line.product_id.product_tmpl_id.x_studio_arabic_service_name if line.product_id.product_tmpl_id.x_studio_arabic_service_name else " ",
                #             text_style)
                #
                ######################
                sheet.write(row, 6, line.price_total, total_style)
                ############################
                row += 1
                number += 1
            row += 1
            sheet.merge_range('A' + str(row) + ':G' + str(row), 'Total', text_style)
            ############################
            sheet.write(row - 1, 7, record.amount_total, total_style)
            sheet.write(row - 1, 8, record.amount_total - record.amount_residual, total_style)
            sheet.write(row - 1, 9, record.amount_residual, total_style)
            ##############################
            amount_total += record.amount_total
            paid += record.amount_total - record.amount_residual
            amount_residual += record.amount_residual
            row += 1
        sheet.merge_range('A' + str(row) + ':G' + str(row), 'Total Lines', text_style)
        sheet.write(row - 1, 7, amount_total, total_style)
        sheet.write(row - 1, 8, paid, total_style)
        sheet.write(row - 1, 9, amount_residual, total_style)

        workbook.close()
        output.seek(0)
        generated_file = response.stream.write(output.read())
        output.close()
        return generated_file

    def compute_get_invoice_line(self):
        selected_ids = self.env.context.get('active_ids', [])
        action = {
            'type': "ir.actions.act_url",
            'target': "_blank",
            'url': '/download/invoice_line_xlsx/%s' % (selected_ids),
        }
        return action
