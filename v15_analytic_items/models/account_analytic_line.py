# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    invoice_type = fields.Selection(related='move_id.move_id.invoice_type', string='Invoice Type', store=True)
    location_id = fields.Many2one(related='move_id.move_id.branch_location_id', string='Location', store=True)
    commission_amount = fields.Float('Commission Amount', compute='_compute_commission_amount', store=True)

    @api.depends('product_id', 'unit_amount')
    def _compute_commission_amount(self):
        for rec in self:
            rec.commission_amount = 0.0
            amount = 0.0
            if rec.product_id and rec.account_id:
                apcs = self.env['analytic.product.configuration'].search([('account_id', '=', rec.account_id.id),
                                                                          ('product_id', '=', rec.product_id.id),
                                                                          ('location_id', '=', rec.location_id.id),
                                                                          ('invoice_type', '=', rec.invoice_type),
                                                                          ])
                if apcs:
                    for apc in apcs:
                        if apc.commission_condition == 'amount':
                            amount = apc.comm_amount * rec.unit_amount
                        if apc.commission_condition == 'percentage':
                            amount = (rec.amount * (apc.comm_percentage / 100))
            rec.commission_amount = amount
