# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class Carriers(models.TransientModel):
    _name = "delivery.carrier.shiprocket"
    _description = "Available Carriers from Shiprocket"

    carrier_name = fields.Selection(selection="_get_carrier_names", string="Carrier")
    carrier_code = fields.Selection(selection="_get_carrier_codes", string="Carrier Code", store=True)
    delivery_carrier_id = fields.Many2one('delivery.carrier')


    @api.onchange('carrier_name')
    def onchange_carrier_name(self):
        if self.carrier_name:
            print("self.env.context.get('carrier_names')-----------------------",self.env.context.get('carrier_names'))
            self.carrier_code = self.env.context.get('carrier_names').get(self.carrier_name)

    def _get_carrier_codes(self):
        if self.env.context.get('carrier_names'):
            return [(carrier, carrier) for carrier in self.env.context.get('carrier_names').values()]
        else:
            return []

    def _get_carrier_names(self):
        if self.env.context.get('carrier_names'):
            return [(carrier, carrier) for carrier in self.env.context.get('carrier_names').keys()]
        else:
            return []

    def action_validate(self):
        if self.carrier_name and self.delivery_carrier_id:
            self.delivery_carrier_id.shiprocket_courier_name = self.carrier_name
            self.delivery_carrier_id.name = 'Shiprocket - '+self.carrier_name
            self.delivery_carrier_id.shiprocket_courier_id = self.carrier_code