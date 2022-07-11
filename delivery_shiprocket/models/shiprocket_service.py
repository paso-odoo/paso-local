# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

class ShiprocketService(models.Model):
    _name = 'shiprocket.carrier.service'
    _description = 'Shiprocket Service'

    name = fields.Char('Service Name', index=True, readonly=True)
    carrier_code = fields.Integer('Carrier Code', index=True, readonly=True)
