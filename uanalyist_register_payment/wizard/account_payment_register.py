# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    percentage = fields.Integer(string='Percentage')

    @api.onchange('percentage')
    def onchange_percentage_partial(self):
        for record in self:
            if record.percentage > 0:
                record.amount = record.amount * record.percentage / 100
