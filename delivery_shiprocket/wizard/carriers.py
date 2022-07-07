# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class Carriers(models.TransientModel):
    _name = "delivery.carrier.shiprocket"
    _description = "Available Carriers from Shiprocket"

    courier_id = fields.Many2one('shiprocket.carrier.service', string="Shiprocket Service")
    delivery_carrier_id = fields.Many2one('delivery.carrier')

    #to be removed
    # carrier_name = fields.Selection(selection="_get_carrier_names", string="Carrier")
    # carrier_code = fields.Selection(selection="_get_carrier_codes", string="Carrier Code", store=True)

    # to be removed
    # @api.onchange('carrier_name')
    # def onchange_carrier_name(self):
    #     if self.carrier_name:
    #         self.carrier_code = self.env.context.get('carrier_names').get(self.carrier_name).get('id')

    # to be removed
    # def _get_carrier_codes(self):
    #     if self.env.context.get('carrier_names'):
    #         return [(carrier.get('id'), carrier.get('id')) for carrier in list(self.env.context.get('carrier_names').values())]
    #     else:
    #         return []

    # to be removed
    # def _get_carrier_names(self):
    #     if self.env.context.get('carrier_names'):
    #         return [(carrier, carrier) for carrier in self.env.context.get('carrier_names').keys()]
    #     else:
    #         return []

    def action_validate(self):
        print('self.courier_id--------------------------',self.delivery_carrier_id,self.courier_id)
        if self.courier_id:
            # self.delivery_carrier_id.write({'shiprocket_courier_id': self.courier_id.id})
            # print("self.delivery_carrier_id.shiprocket_courier_id-----------1111---",self.delivery_carrier_id.shiprocket_courier_id)
            self.delivery_carrier_id.shiprocket_courier_id = self.courier_id.id
            self.delivery_carrier_id.name = 'Shiprocket - ' + self.courier_id.name
            # print("self.delivery_carrier_id.shiprocket_courier_id-----------222---",self.delivery_carrier_id.shiprocket_courier_id)

        #to be removed
        # if self.carrier_name and self.delivery_carrier_id:
        #     self.delivery_carrier_id.shiprocket_courier_name = self.carrier_name
        #     self.delivery_carrier_id.name = 'Shiprocket - '+self.carrier_name
        #     self.delivery_carrier_id.shiprocket_courier_code = self.carrier_code