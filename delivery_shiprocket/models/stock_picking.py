# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # ep_order_ref = fields.Char("Easypost Order Reference", copy=False)
    shiprocket_picking = fields.Boolean("Shiprocket Picking")
    shiprocket_order_id = fields.Char('Shiprocket Order')
    shiprocket_shipment_id = fields.Char('Shiprocket Shipment')
    shiprocket_status = fields.Char('Shiprocket Status')
    shipment_courier = fields.Char('Shiprocket Courier')
    # shiprocket_label_url = fields.Char('Label URL')
    # shiprocket_invoice_url = fields.Char('Invoice URL')
    # shiprocket_manifest_url = fields.Char('Manifest URL')
