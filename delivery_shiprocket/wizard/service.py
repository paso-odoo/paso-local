# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class Carriers(models.TransientModel):
    _name = "delivery.carrier.shiprocket"
    _description = "Available Carriers from Shiprocket"

    courier_id = fields.Many2one('shiprocket.carrier.service', string="Shiprocket Service")
    delivery_carrier_id = fields.Many2one('delivery.carrier')

    def action_validate(self):
        """
        Select courier from the particular shiprocket courier.
        """
        if self.courier_id:
            self.delivery_carrier_id.shiprocket_courier_id = self.courier_id.id
            self.delivery_carrier_id.name = 'Shiprocket - ' + self.courier_id.name
