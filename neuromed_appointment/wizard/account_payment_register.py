# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    branch_location_id = fields.Many2one(
        comodel_name='medical.locations',
        string='Location'
    )

    def _create_payment_vals_from_wizard(self):
        payment_vals = super()._create_payment_vals_from_wizard()
        payment_vals['branch_location_id'] = self.branch_location_id.id
        return payment_vals
