from odoo import http
from odoo.http import content_disposition, request
import ast

class XLSXReportController(http.Controller):

    @http.route('/download/invoice_line_xlsx/<records>', type='http', auth='user', csrf=False)
    def get_report_xlsx(self, records=None, **kw):
        records = request.env['account.move'].browse(ast.literal_eval(records))
        response = request.make_response(
            None,
            headers=[('Content-Type', 'application/vnd.ms-excel'),
                     ('Content-Disposition', content_disposition('Invoice Items in Excel' + '.xlsx'))]
        )
        request.env['account.move'].get_invoice_lines_report(response, records)
        return response
