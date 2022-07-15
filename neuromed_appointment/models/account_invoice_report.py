# -*- coding: utf-8 -*-

from odoo import models, fields

class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    invoice_type = fields.Selection(
        [('cash', 'Cash'),
         ('insurance', 'Insurance')], 'Invoice Type')
    invoice_sub_type = fields.Selection([
        ('internal', 'Internal'),
        ('portable', 'Portable'),
        ('os', 'OS'),
        ('insurance', 'Insurance')
    ], string="Invoice Sub Type")
    resource_id = fields.Many2one(
        comodel_name='medical.resources', string='Resource')
    branch_location_id = fields.Many2one(
        comodel_name='medical.locations',
        string='Location'
    )

    def _select(self):
        return '''
            SELECT
                line.id,
                line.move_id,
                line.product_id,
                line.account_id,
                line.analytic_account_id,
                line.journal_id,
                line.company_id,
                line.company_currency_id,
                line.partner_id AS commercial_partner_id,
                move.invoice_type,
                move.invoice_sub_type,
                move.resource_id,
                move.branch_location_id,
                move.state,
                move.move_type,
                move.partner_id,
                move.invoice_user_id,
                move.fiscal_position_id,
                move.payment_state,
                move.invoice_date,
                move.invoice_date_due,
                uom_template.id                                             AS product_uom_id,
                template.categ_id                                           AS product_categ_id,
                line.quantity / NULLIF(COALESCE(uom_line.factor, 1) / COALESCE(uom_template.factor, 1), 0.0) * (CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)
                                                                            AS quantity,
                -line.balance * currency_table.rate                         AS price_subtotal,
                -COALESCE(
                   -- Average line price
                   (line.balance / NULLIF(line.quantity, 0.0)) * (CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)
                   -- convert to template uom
                   * (NULLIF(COALESCE(uom_line.factor, 1), 0.0) / NULLIF(COALESCE(uom_template.factor, 1), 0.0)),
                   0.0) * currency_table.rate                               AS price_average,
                COALESCE(partner.country_id, commercial_partner.country_id) AS country_id
        '''

