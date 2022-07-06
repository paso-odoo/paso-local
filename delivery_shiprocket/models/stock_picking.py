# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, _
from .shiprocket_request import ShipRocket
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    shiprocket_picking = fields.Boolean("Shiprocket Picking")
    shiprocket_order_id = fields.Char('Shiprocket Order')
    shiprocket_shipment_id = fields.Char('Shiprocket Shipment')
    shiprocket_status = fields.Char('Shiprocket Status')
    shipment_courier = fields.Char('Shiprocket Courier')

    def action_pickup_requests(self):
        print("--------action_pickup_requests------------")
        for rec in self:
            if rec.carrier_tracking_ref and rec.carrier_id and rec.carrier_id.delivery_type == 'shiprocket':
                sr = ShipRocket(rec.carrier_id.shiprocket_access_token, rec.carrier_id)
                pickup = sr.request_pickup(rec, rec.carrier_id)
                print("pickup------------data-------------",pickup)
                if pickup and pickup.get('status_code') != 200 and pickup.get('message'):
                    raise UserError(_(pickup.get('message')))
                elif pickup and pickup.get('manifest_url'):
                    rec.carrier_id.create_attachment_shiprocket(rec, pickup.get('manifest_url'), 'Manifest')
