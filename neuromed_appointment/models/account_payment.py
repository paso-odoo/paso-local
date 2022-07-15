# -*- coding: utf-8 -*-

from odoo import models, fields

class AccountPayment(models.Model):
    _inherit = "account.payment"

    branch_location_id = fields.Many2one(
        comodel_name='medical.locations',
        string='Location'
    )
