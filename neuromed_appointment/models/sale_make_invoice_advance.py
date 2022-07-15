# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _prepare_invoice_values(self, order, name, amount, so_line):
        invoice_vals = super()._prepare_invoice_values(order, name, amount, so_line)
        invoice_vals['invoice_type'] = order.invoice_type
        invoice_vals['invoice_sub_type'] = order.invoice_sub_type
        invoice_vals['resource_id'] = order.resource_id.id
        invoice_vals['branch_location_id'] = order.branch_location_id.id
        return invoice_vals
