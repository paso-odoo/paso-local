# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from datetime import timedelta, datetime
from odoo.exceptions import UserError
import requests
import base64
from .shiprocket_request import ShipRocket

class DeliverCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('shiprocket', 'Shiprocket')], ondelete={
        'shiprocket': lambda recs: recs.write({'delivery_type': 'fixed', 'fixed_price': 0})})
    shiprocket_email = fields.Char("Shiprocket Email", groups="base.group_system",
                                   help="Enter your Username from Shiprocket account.")
    shiprocket_password = fields.Char("Shiprocket Password", groups="base.group_system",
                                      help="Enter your Password from Shiprocket account.")
    shiprocket_access_token = fields.Text("Shiprocket Access Token", groups="base.group_system",
                                          help="Generate access token by Shiproket credentials")
    shiprocket_token_create_date = fields.Datetime("Access Token Created On")
    shiprocket_token_expiry_date = fields.Datetime("Access Token Expires On")
    shiprocket_channel = fields.Char(string="Shiprocket Channel")
    shiprocket_channel_code = fields.Char(string="Shiprocket Channel Code")
    shiprocket_default_package_type_id = fields.Many2one("stock.package.type", string="Package Type")
    shiprocket_payment_method = fields.Selection([('0', 'Prepaid'), ('1', 'COD')], default="0", string="Payment Method")
    shiprocket_label_generate = fields.Boolean("Generate Label")
    shiprocket_invoice_generate = fields.Boolean("Generate Invoice")
    shiprocket_manifests_generate = fields.Boolean("Generate Manifest")
    shiprocket_courier_filter = fields.Selection(
        [('default_courier', 'Default Shiprocket Service'), ('lowest_rate', 'Lowest Rate'),
         ('lowest_etd', 'Lowest Estimated Time'), ('high_ratings', 'Highest Ratings'),
         ('call_before_delivery', 'Call Before Delivery')], string='Shipment Based on')
    shiprocket_courier_id = fields.Many2one('shiprocket.carrier.service', string="Shiprocket Service")


    def _compute_can_generate_return(self):
        super(DeliverCarrier, self)._compute_can_generate_return()
        self.filtered(lambda c: c.delivery_type == 'shiprocket').write({'can_generate_return': True})

    def action_generate_access_token(self):
        """
        Generate access token from
        shiprocket email and password.
        """
        if self.delivery_type == 'shiprocket' and self.shiprocket_email and self.shiprocket_password:
            sr = ShipRocket(self.shiprocket_access_token, self)
            response = sr.authorize_generate_token()
            if response.status_code == 200:
                response = response.json()
                self.shiprocket_access_token = response.get('token')
                self.shiprocket_token_create_date = datetime.now()
                self.shiprocket_token_expiry_date = datetime.now() + timedelta(days=9)
                type = 'success'
                message = _("Access Token is generated successfully!")
            else:
                type = 'danger'
                message = _("Please check shiprocket credentials!")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': type,
                    'message': message,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

    def cron_shiprocket_access_token(self):
        """
        Scheduled action for renew token automatically.
        """
        shiprocket_carriers = self.search([('delivery_type', '=', 'shiprocket')])
        for carrier in shiprocket_carriers:
            sr = ShipRocket(carrier.shiprocket_access_token, carrier)
            response = sr.authorize_generate_token()
            if response.status_code == 200:
                response = response.json()
                carrier.shiprocket_access_token = response.get('token')
                carrier.shiprocket_token_create_date = datetime.now()
                carrier.shiprocket_token_expiry_date = datetime.now() + timedelta(days=9)


    def action_get_channels(self):
        """
        Return the list of channels configured by the customer
        on its shiprocket account.
        """
        if self.delivery_type == 'shiprocket' and self.sudo().shiprocket_access_token:
            sr = ShipRocket(self.shiprocket_access_token, self)
            channels = sr.fetch_shiprocket_channels()
            if channels:
                action = self.env["ir.actions.actions"]._for_xml_id("delivery_shiprocket.act_delivery_shiprocket_channels")
                action['context'] = {'channel_types': channels, 'default_delivery_carrier_id': self.id}
                return action
        else:
            raise UserError('An Access Token is required in order to load your Shiprocket Channels.')


    def action_get_couriers(self):
        """
        Returns the action for wizard to select shiprocket courier service -
        create a new shiprocket services if not available in db.
        """
        if self.delivery_type == 'shiprocket' and self.sudo().shiprocket_access_token:
            sr = ShipRocket(self.shiprocket_access_token, self)
            sr.fetch_shiprocket_carriers()
            action = self.env["ir.actions.actions"]._for_xml_id("delivery_shiprocket.act_delivery_shiprocket_carriers")
            action['context'] = {'default_delivery_carrier_id': self.id}
            return action
        else:
            raise UserError('An Access Token is required in order to load your Shiprocket Couriers.')


    def _shiprocket_convert_weight(self, weight):
        """ Return the weight for a Shiprocket order weight in KG."""
        weight_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        return weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_kgm'), round=False)


    def shiprocket_rate_shipment(self, order):
        """ Return the rates for a quotation/SO."""
        sr = ShipRocket(self.shiprocket_access_token, self)
        result = sr.rate_request(self, order.partner_shipping_id, order.warehouse_id.partner_id, order)
        if result['error_found']:
            return {'success': False, 'price': 0.0, 'error_message': result['error_found'], 'warning_message': False}
        price = float(result['price'])
        return {'success': True, 'price': price, 'error_message': False, 'warning_message': False,
                'courier_name': result['courier_name']}


    def shiprocket_send_shipping(self, pickings):
        """
        It creates a Shiprocket order.
        Once the order is generated. It will post as message the tracking
        links and the shipping labels, manifests and invoices.
        """
        sr = ShipRocket(self.sudo().shiprocket_access_token, self)
        res = []
        for picking in pickings:
            shipping = sr.send_shipping(picking, self)
            print("shipping---------------------------",shipping)
            if shipping:
                picking.shiprocket_order_id = shipping.get('order_id') if shipping.get('order_id') else False
                picking.shiprocket_shipment_id = shipping.get('shipment_id') if shipping.get('shipment_id') else False
                # need to change awb when available
                picking.carrier_tracking_ref = shipping.get('shipment_id') if shipping.get('shipment_id') else False
                picking.shiprocket_status = shipping.get('status') if shipping.get('status') else ''
                picking.message_post(body='Shiprocket order generated!') if shipping.get('order_id') else False
                attachment_list = []
                if shipping.get('invoice_url'):
                    attachment = self.create_attachment_shiprocket(picking, shipping.get('invoice_url'), 'Invoice')
                    attachment_list.append(attachment.id) if attachment else False
                if shipping.get('label_url'):
                    attachment = self.create_attachment_shiprocket(picking, shipping.get('label_url'), 'Label')
                    attachment_list.append(attachment.id) if attachment else False
                picking.message_post(body=(_("Shiprocket Attachments")), attachment_ids=attachment_list)
                picking.shipment_courier = shipping.get('courier_name')
                res.append(shipping)
        print("res=---------------------",res)
        return res


    def create_attachment_shiprocket(self, picking, url, name):
        """
        Create attachments for Shiprocket Invoice, Label
        and Manifest.
        """
        response = requests.Session().get(url, timeout=30)
        if response.status_code == 200 and response.content:
            attachment = self.env['ir.attachment'].search([('name', '=', '{} Shiprocket {}' .format(name, picking.name))])
            if not attachment:
                attachment = self.env['ir.attachment'].create({
                    'name': '{} Shiprocket {}' .format(name, picking.name),
                    'res_model': 'stock.picking',
                    'res_id': picking.id,
                    'res_name': picking.name,
                    'datas': base64.b64encode(response.content),
                    'mimetype': 'application/pdf'
                })
                return attachment


    def shiprocket_get_tracking_link(self, picking):
        """
        Returns the tracking links from a picking. Shiprocket returns one
        tracking link by package.
        """
        print("shiprocket_get_tracking_link---------------------",picking)
        sr = ShipRocket(self.shiprocket_access_token, self)
        shipment_id = picking.shiprocket_shipment_id
        track_url = sr.track_shipment(shipment_id)
        print("track_url--------------------",track_url)
        return track_url

    def shiprocket_cancel_shipment(self, picking):
        """
        Cancel shipment from shiprocket requests.
        """
        sr = ShipRocket(self.sudo().shiprocket_access_token, self)
        cancel_shipment = sr.send_cancelling(picking)
        print("cancel_shipment----------------------",cancel_shipment)
        if cancel_shipment and cancel_shipment.get('status') == 200:
            picking.write({
                'carrier_tracking_ref': '',
                'carrier_price': 0.0,
                'shiprocket_status': 'REQUEST FOR CANCEL'
            })
            raise UserError(_(cancel_shipment.get('message')))
        else:
            raise UserError(_('Cannot cancel a Shipment!'))

    @api.onchange('shiprocket_courier_filter')
    def onchange_shiprocket_courier_filter(self):
        """
        Delivery carrier name based upon shiprocket_courier_filter.
        """
        if self.shiprocket_courier_filter == 'lowest_rate':
            self.name = 'Shiprocket - Lowest Rate'
        elif self.shiprocket_courier_filter == 'call_before_delivery':
            self.name = 'Shiprocket - Call Before Delivery'
        elif self.shiprocket_courier_filter == 'lowest_etd':
            self.name = 'Shiprocket - Lowest Estimated Delivery time'
        elif self.shiprocket_courier_filter == 'high_ratings':
            self.name = 'Shiprocket - Highest Ratings'
        elif self.shiprocket_courier_filter == 'default_courier' and self.shiprocket_courier_id:
            self.name = 'Shiprocket - {}'.format(self.shiprocket_courier_id.name)
